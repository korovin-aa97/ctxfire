from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path

from ctxfire import __version__
from ctxfire.adapters import matches
from ctxfire.cli import EXIT_BUDGET_EXCEEDED, EXIT_ERROR, EXIT_OK, main
from ctxfire.config import load_config
from ctxfire.discovery import inventory
from ctxfire.frontmatter import parse_frontmatter_bytes
from ctxfire.scanner import scan


class RepositoryFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write("AGENTS.md", "root rules\n")
        self.write("apps/api/AGENTS.md", "api rules\n")
        self.write(".agents/skills/review/SKILL.md", "review skill\n")
        self.write(".claude/rules/python.md", "python rule\n")
        self.write("ignored.md", "must not appear\n")
        self.write(".gitignore", "ignored.md\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def config(self, *, adapter: str = "codex@1") -> Path:
        config = self.root / "ctxfire.toml"
        config.write_text(
            "\n".join(
                [
                    'schema_version = "1"',
                    "[project]",
                    'name = "fixture"',
                    'root = "."',
                    "bytes_per_token = 4",
                    'tokenizer = "byte-estimate"',
                    'model = "example"',
                    'price_date = "2026-08-29"',
                    "usd_per_million_input_tokens = 3",
                    'cache_assumption = "no-cache-credit"',
                    "conditional_activation_rate = 0.5",
                    "[[agents]]",
                    'name = "api"',
                    f'adapter = "{adapter}"',
                    'working_directory = "apps/api"',
                    "fires_per_day = 2",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return config


class ScanTests(RepositoryFixture):
    def test_codex_chain_and_conditional_skill(self) -> None:
        report = scan(load_config(self.config()))
        agent = report.agents[0]
        files = {item.path: item for item in agent.files}
        self.assertEqual(
            {"AGENTS.md", "apps/api/AGENTS.md", ".agents/skills/review/SKILL.md"}, set(files)
        )
        self.assertEqual("always", files["AGENTS.md"].activation)
        self.assertEqual(0.5, files[".agents/skills/review/SKILL.md"].activation_rate)
        self.assertEqual("git-index+untracked-nonignored", report.discovery["method"])
        self.assertNotIn("ignored.md", files)
        self.assertEqual(".", report.project["root"])

    def test_claude_rules_are_conservative_by_default(self) -> None:
        report = scan(load_config(self.config(adapter="claude-code@1")))
        rule = next(item for item in report.agents[0].files if item.path.endswith("python.md"))
        self.assertEqual("always", rule.activation)

    def test_claude_v2_parses_mixed_rule_activation(self) -> None:
        self.write(
            ".claude/rules/python.md",
            '---\npaths:\n  - "src/**/*.py"\n---\n\nPython rule\n',
        )
        self.write(".claude/rules/general.md", "General rule\n")
        report = scan(load_config(self.config(adapter="claude-code@2")))
        files = {item.path: item for item in report.agents[0].files}
        self.assertEqual("conditional", files[".claude/rules/python.md"].activation)
        self.assertEqual(0.5, files[".claude/rules/python.md"].activation_rate)
        self.assertEqual("always", files[".claude/rules/general.md"].activation)
        self.assertEqual("matched-file-content-local", report.discovery["content_access"])

    def test_claude_v2_accounts_for_skill_and_subagent_catalogs(self) -> None:
        self.write(
            ".claude/skills/review/SKILL.md",
            "---\nname: review\ndescription: Review changed code\n---\n\nDetailed body.\n",
        )
        self.write(
            ".claude/agents/reviewer.md",
            "---\nname: reviewer\ndescription: Review pull requests\n---\n\nAgent prompt.\n",
        )
        report = scan(load_config(self.config(adapter="claude-code@2")))
        files = {item.path: item for item in report.agents[0].files}
        skill = files[".claude/skills/review/SKILL.md"]
        self.assertEqual("mixed", skill.activation)
        self.assertEqual(
            ["skill-catalog", "skill-body"], [component.kind for component in skill.components]
        )
        subagent = files[".claude/agents/reviewer.md"]
        self.assertEqual(["subagent-catalog"], [item.kind for item in subagent.components])

    def test_claude_v2_descendant_skill_catalog_is_not_available_at_launch(self) -> None:
        self.write(
            "apps/api/.claude/skills/review/SKILL.md",
            "---\nname: review\ndescription: Review API changes\n---\n\nDetailed body.\n",
        )
        report = scan(load_config(self.config(adapter="claude-code@2")))
        skill = next(
            item
            for item in report.agents[0].files
            if item.path == "apps/api/.claude/skills/review/SKILL.md"
        )
        self.assertEqual("mixed", skill.activation)
        self.assertEqual("always", skill.components[0].activation)

        config_path = self.config(adapter="claude-code@2")
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                'working_directory = "apps/api"', 'working_directory = "."'
            ),
            encoding="utf-8",
        )
        root_report = scan(load_config(config_path))
        root_skill = next(
            item
            for item in root_report.agents[0].files
            if item.path == "apps/api/.claude/skills/review/SKILL.md"
        )
        self.assertEqual("conditional", root_skill.activation)
        self.assertTrue(
            all(component.activation == "conditional" for component in root_skill.components)
        )

    def test_claude_v2_selected_subagent_preloads_declared_skills(self) -> None:
        self.write(
            ".claude/skills/review/SKILL.md",
            "---\nname: review\ndescription: Review changed code\n---\n\nDetailed body.\n",
        )
        self.write(
            ".claude/agents/reviewer.md",
            "---\nname: reviewer\ndescription: Review pull requests\nskills:\n  - review\n"
            "---\n\nAgent prompt.\n",
        )
        config_path = self.config(adapter="claude-code@2")
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('claude_subagent = "reviewer"\n')
        report = scan(load_config(config_path))
        files = {item.path: item for item in report.agents[0].files}
        self.assertEqual(
            ["subagent-definition"],
            [item.kind for item in files[".claude/agents/reviewer.md"].components],
        )
        self.assertEqual(
            ["preloaded-skill"],
            [item.kind for item in files[".claude/skills/review/SKILL.md"].components],
        )
        self.assertEqual("always", files[".claude/skills/review/SKILL.md"].activation)

    def test_claude_v2_preload_does_not_resolve_to_an_undiscovered_descendant(self) -> None:
        self.write(
            ".claude/skills/review/SKILL.md",
            "---\nname: review\ndescription: Root review\n---\n\nRoot body.\n",
        )
        self.write(
            "packages/api/.claude/skills/review/SKILL.md",
            "---\nname: review\ndescription: Nested review\n---\n\nNested body.\n",
        )
        self.write(
            ".claude/agents/reviewer.md",
            "---\nname: reviewer\ndescription: Review pull requests\nskills: [review]\n"
            "---\n\nAgent prompt.\n",
        )
        config_path = self.config(adapter="claude-code@2")
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                'working_directory = "apps/api"', 'working_directory = "."'
            ),
            encoding="utf-8",
        )
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('claude_subagent = "reviewer"\n')
        files = {item.path: item for item in scan(load_config(config_path)).agents[0].files}
        self.assertEqual(
            ["preloaded-skill"],
            [item.kind for item in files[".claude/skills/review/SKILL.md"].components],
        )
        self.assertEqual(
            ["skill-catalog", "skill-body"],
            [item.kind for item in files["packages/api/.claude/skills/review/SKILL.md"].components],
        )

    def test_claude_v2_warns_when_a_preloaded_skill_drifts(self) -> None:
        self.write(
            ".claude/agents/reviewer.md",
            "---\nname: reviewer\ndescription: Review pull requests\nskills: [missing]\n"
            "---\n\nAgent prompt.\n",
        )
        config_path = self.config(adapter="claude-code@2")
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('claude_subagent = "reviewer"\n')
        report = scan(load_config(config_path))
        self.assertTrue(any("preloaded Claude skill 'missing'" in item for item in report.warnings))

    def test_claude_v2_hides_disabled_skill_catalog_and_rejects_its_preload(self) -> None:
        self.write(
            ".claude/skills/manual/SKILL.md",
            "---\nname: manual\ndescription: Manual side effect\n"
            "disable-model-invocation: true # user only\n---\n\nRun manually.\n",
        )
        self.write(
            ".claude/agents/reviewer.md",
            "---\nname: reviewer\ndescription: Review pull requests\nskills: [manual]\n"
            "---\n\nAgent prompt.\n",
        )
        config_path = self.config(adapter="claude-code@2")
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('claude_subagent = "reviewer"\n')
        report = scan(load_config(config_path))
        skill = next(
            item for item in report.agents[0].files if item.path == ".claude/skills/manual/SKILL.md"
        )
        self.assertEqual(["skill-body"], [item.kind for item in skill.components])
        self.assertTrue(any("cannot be preloaded" in item for item in report.warnings))

    def test_codex_override_precedence_and_instruction_cap(self) -> None:
        self.write("apps/api/AGENTS.override.md", "override rules\n")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "apps/api/AGENTS.override.md"], check=True
        )
        config_path = self.config()
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write("instruction_max_bytes = 15\n")
        report = scan(load_config(config_path))
        files = {item.path: item for item in report.agents[0].files}
        self.assertNotIn("apps/api/AGENTS.md", files)
        self.assertIn("apps/api/AGENTS.override.md", files)
        instruction_files = [item for item in files.values() if "instruction chain" in item.reason]
        self.assertEqual(15, sum(item.counted_bytes for item in instruction_files))
        self.assertTrue(any("instruction_max_bytes=15" in item for item in report.warnings))

    def test_empty_codex_override_falls_back_to_agents(self) -> None:
        self.write("apps/api/AGENTS.override.md", "")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "apps/api/AGENTS.override.md"], check=True
        )
        paths = {item.path for item in scan(load_config(self.config())).agents[0].files}
        self.assertIn("apps/api/AGENTS.md", paths)
        self.assertNotIn("apps/api/AGENTS.override.md", paths)

    def test_ignored_exact_engine_memory_is_still_counted(self) -> None:
        self.write("CLAUDE.local.md", "local instructions\n")
        self.write(".gitignore", "ignored.md\nCLAUDE.local.md\n")
        report = scan(load_config(self.config(adapter="claude-code@1")))
        self.assertIn("CLAUDE.local.md", {item.path for item in report.agents[0].files})
        self.assertEqual(1, report.discovery["exact_probe_files_outside_git_discovery"])
        self.assertTrue(any("outside Git discovery" in item for item in report.warnings))

    def test_symlinks_are_skipped_without_following(self) -> None:
        target = self.root / "outside-secret"
        target.write_text("secret", encoding="utf-8")
        link = self.root / "AGENTS-link.md"
        os.symlink(target, link)
        subprocess.run(["git", "-C", str(self.root), "add", "AGENTS-link.md"], check=True)
        config = self.config()
        with config.open("a", encoding="utf-8") as handle:
            handle.write('include = ["AGENTS-link.md"]\n')
        report = scan(load_config(config))
        self.assertFalse(any(item.path == "AGENTS-link.md" for item in report.agents[0].files))
        self.assertTrue(any("skipped symlink" in warning for warning in report.warnings))

    def test_exact_probe_does_not_follow_a_symlinked_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as external_directory:
            external = Path(external_directory)
            (external / "AGENTS.md").write_text("outside project", encoding="utf-8")
            os.symlink(external, self.root / "linked")
            config_path = self.config()
            config_path.write_text(
                config_path.read_text(encoding="utf-8").replace(
                    'working_directory = "apps/api"', 'working_directory = "linked"'
                ),
                encoding="utf-8",
            )
            report = scan(load_config(config_path))
        self.assertNotIn("linked/AGENTS.md", {item.path for item in report.agents[0].files})
        self.assertIn("skipped symlink: linked/AGENTS.md", report.warnings)

    def test_explicit_include_wins_a_same_activation_instruction_cap_tie(self) -> None:
        config_path = self.config()
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('instruction_max_bytes = 1\ninclude = ["AGENTS.md"]\n')
        root_instruction = next(
            item
            for item in scan(load_config(config_path)).agents[0].files
            if item.path == "AGENTS.md"
        )
        self.assertEqual(root_instruction.exact_bytes, root_instruction.counted_bytes)
        self.assertEqual("explicit include", root_instruction.reason)

    def test_reports_are_deterministic(self) -> None:
        config = load_config(self.config())
        self.assertEqual(scan(config).as_dict(), scan(config).as_dict())

    def test_opt_in_tiktoken_is_local_and_versioned(self) -> None:
        config_path = self.config()
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                'tokenizer = "byte-estimate"', 'tokenizer = "tiktoken:cl100k_base"'
            ),
            encoding="utf-8",
        )
        report = scan(load_config(config_path))
        self.assertEqual("matched-file-content-local", report.discovery["content_access"])
        self.assertEqual("tiktoken:cl100k_base", report.assumptions.tokenizer)
        self.assertNotEqual("approximation-v1", report.assumptions.tokenizer_version)
        self.assertGreater(report.agents[0].estimated_tokens_per_fire, 0)

    def test_excludes_and_missing_explicit_files_are_explained(self) -> None:
        config_path = self.config()
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('include = ["missing.md"]\nexclude = ["AGENTS.md"]\n')
        report = scan(load_config(config_path))
        paths = {item.path for item in report.agents[0].files}
        self.assertNotIn("AGENTS.md", paths)
        self.assertIn("apps/api/AGENTS.md", paths)
        self.assertIn("api: configured context file not found: missing.md", report.warnings)

    def test_tracked_generated_file_remains_explicitly_budgetable(self) -> None:
        self.write("generated/context.md", "generated but intentionally tracked\n")
        self.write(".gitignore", "ignored.md\ngenerated/\n")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "-f", "generated/context.md"], check=True
        )
        config_path = self.config()
        with config_path.open("a", encoding="utf-8") as handle:
            handle.write('include = ["generated/**/*.md"]\n')
        report = scan(load_config(config_path))
        self.assertIn("generated/context.md", {item.path for item in report.agents[0].files})

    def test_nested_repository_is_not_traversed(self) -> None:
        nested = self.root / "vendor" / "nested"
        nested.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(nested)], check=True)
        (nested / "AGENTS.md").write_text("nested private rules", encoding="utf-8")
        report = scan(load_config(self.config()))
        self.assertNotIn("vendor/nested/AGENTS.md", {item.path for item in report.agents[0].files})

    def test_filesystem_fallback_warns_about_symlinked_directories(self) -> None:
        with tempfile.TemporaryDirectory() as fallback_directory:
            fallback = Path(fallback_directory)
            target = fallback / "target"
            target.mkdir()
            os.symlink(target, fallback / "linked")
            found = inventory(fallback)
        self.assertEqual("filesystem-fallback", found.method)
        self.assertIn("linked", found.skipped_symlinks)


class CliTests(RepositoryFixture):
    def test_scan_json_and_diff(self) -> None:
        config = self.config()
        before = self.root / "before.json"
        after = self.root / "after.json"
        self.assertEqual(
            EXIT_OK,
            main(["scan", "--config", str(config), "--format", "json", "--output", str(before)]),
        )
        self.write("apps/api/AGENTS.md", "api rules changed and larger\n")
        self.assertEqual(
            EXIT_OK,
            main(["scan", "--config", str(config), "--format", "json", "--output", str(after)]),
        )
        self.assertEqual("1.1", json.loads(after.read_text())["schema_version"])
        self.assertEqual(EXIT_OK, main(["diff", str(before), str(after), "--format", "json"]))

    def test_check_exit_codes_and_sarif(self) -> None:
        config = self.config()
        output = self.root / "result.sarif"
        self.assertEqual(
            EXIT_BUDGET_EXCEEDED,
            main(
                [
                    "check",
                    "--config",
                    str(config),
                    "--max-tokens-per-day",
                    "0",
                    "--format",
                    "sarif",
                    "--output",
                    str(output),
                ]
            ),
        )
        payload = json.loads(output.read_text())
        self.assertEqual("2.1.0", payload["version"])
        self.assertTrue(payload["runs"][0]["results"])
        location = payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        self.assertEqual("ctxfire.toml", location["artifactLocation"]["uri"])

    def test_sarif_names_a_custom_config_without_leaking_its_absolute_path(self) -> None:
        config = self.config()
        custom_config = self.root / "custom-budget.toml"
        config.rename(custom_config)
        output = self.root / "result.sarif"
        self.assertEqual(
            EXIT_BUDGET_EXCEEDED,
            main(
                [
                    "check",
                    "--config",
                    str(custom_config),
                    "--max-tokens-per-day",
                    "0",
                    "--format",
                    "sarif",
                    "--output",
                    str(output),
                ]
            ),
        )
        payload = json.loads(output.read_text())
        serialized = output.read_text()
        location = payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        self.assertEqual("custom-budget.toml", location["artifactLocation"]["uri"])
        self.assertNotIn(str(self.root), serialized)

    def test_bad_schema_is_a_controlled_error(self) -> None:
        config = self.config()
        config.write_text('schema_version = "99"\n', encoding="utf-8")
        self.assertEqual(EXIT_ERROR, main(["scan", "--config", str(config)]))

    def test_bad_glob_is_a_controlled_error(self) -> None:
        config = self.config()
        with config.open("a", encoding="utf-8") as handle:
            handle.write('include = ["[z-a]"]\n')
        self.assertEqual(EXIT_ERROR, main(["scan", "--config", str(config)]))

    def test_non_finite_budget_is_a_controlled_error(self) -> None:
        self.assertEqual(
            EXIT_ERROR,
            main(["check", "--config", str(self.config()), "--max-usd-per-day", "nan"]),
        )

    def test_finite_assumptions_that_overflow_a_result_are_a_controlled_error(self) -> None:
        config = self.config()
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "fires_per_day = 2", "fires_per_day = 1e308"
            ),
            encoding="utf-8",
        )
        self.assertEqual(EXIT_ERROR, main(["scan", "--config", str(config)]))

    def test_argparse_input_error_uses_the_documented_error_exit(self) -> None:
        self.assertEqual(
            EXIT_ERROR,
            main(
                [
                    "check",
                    "--config",
                    str(self.config()),
                    "--max-tokens-per-day",
                    "not-an-integer",
                ]
            ),
        )

    def test_malformed_snapshot_is_a_controlled_error(self) -> None:
        malformed = self.root / "malformed.json"
        valid = self.root / "valid.json"
        malformed.write_text(
            '{"schema_version":"1.0","agents":[{"name":"broken","files":{}}]}',
            encoding="utf-8",
        )
        self.assertEqual(
            EXIT_OK,
            main(
                [
                    "scan",
                    "--config",
                    str(self.config()),
                    "--format",
                    "json",
                    "--output",
                    str(valid),
                ]
            ),
        )
        self.assertEqual(EXIT_ERROR, main(["diff", str(malformed), str(valid)]))

    def test_diff_accepts_a_schema_1_0_snapshot(self) -> None:
        config = self.config()
        current = self.root / "current.json"
        legacy = self.root / "legacy.json"
        self.assertEqual(
            EXIT_OK,
            main(["scan", "--config", str(config), "--format", "json", "--output", str(current)]),
        )
        payload = json.loads(current.read_text(encoding="utf-8"))
        payload["schema_version"] = "1.0"
        for agent in payload["agents"]:
            for item in agent["files"]:
                item.pop("components")
        legacy.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(EXIT_OK, main(["diff", str(legacy), str(current), "--format", "json"]))


class ConfigValidationTests(RepositoryFixture):
    def test_claude_v2_rejects_the_legacy_project_wide_rule_override(self) -> None:
        config = self.config(adapter="claude-code@2")
        with config.open("a", encoding="utf-8") as handle:
            handle.write('claude_rules_activation = "conditional"\n')
        with self.assertRaisesRegex(ValueError, "derived from each rule"):
            load_config(config)

    def test_non_finite_numeric_assumptions_are_rejected(self) -> None:
        replacements = (
            ("bytes_per_token = 4", "bytes_per_token = nan"),
            ("conditional_activation_rate = 0.5", "conditional_activation_rate = inf"),
            ("usd_per_million_input_tokens = 3", "usd_per_million_input_tokens = nan"),
            ("fires_per_day = 2", "fires_per_day = inf"),
        )
        for original, replacement in replacements:
            with self.subTest(replacement=replacement):
                config = self.config()
                config.write_text(
                    config.read_text(encoding="utf-8").replace(original, replacement),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "finite"):
                    load_config(config)

    def test_backslash_paths_are_rejected_on_every_platform(self) -> None:
        config = self.config()
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'working_directory = "apps/api"', "working_directory = '..\\outside'"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "POSIX separators"):
            load_config(config)

        config = self.config()
        with config.open("a", encoding="utf-8") as handle:
            handle.write("include = ['..\\outside.md']\n")
        with self.assertRaisesRegex(ValueError, "POSIX paths"):
            load_config(config)


class PatternTests(unittest.TestCase):
    def test_frontmatter_parser_supports_lists_and_folded_scalars(self) -> None:
        document = parse_frontmatter_bytes(
            b"---\npaths:\n  - 'src/**/*.py'\nskills: [review, test]\n"
            b"description: >\n  Review changes\n  carefully\n---\nBody\n"
        )
        self.assertEqual(("src/**/*.py",), document.items("paths"))
        self.assertEqual(("review", "test"), document.items("skills"))
        self.assertEqual("Review changes carefully", document.scalar("description"))

    def test_frontmatter_parser_strips_plain_comments_but_preserves_quoted_hashes(self) -> None:
        document = parse_frontmatter_bytes(
            b"---\n"
            b"disable-model-invocation: true # user-only\n"
            b'paths: ["src/#generated/**"] # scoped\n'
            b"---\n"
        )
        self.assertEqual("true", document.scalar("disable-model-invocation"))
        self.assertEqual(("src/#generated/**",), document.items("paths"))

    def test_double_star_matches_zero_or_more_directories(self) -> None:
        self.assertTrue(matches(".agents/skills/x/SKILL.md", ".agents/skills/*/SKILL.md"))
        self.assertTrue(matches("rules/python.md", "**/*.md"))
        self.assertTrue(matches("rules/python.md", "rules/**/*.md"))

    def test_single_star_does_not_cross_directories(self) -> None:
        self.assertTrue(matches("README.md", "README*"))
        self.assertFalse(matches("docs/README.md", "README*"))
        self.assertFalse(matches("rules/nested/python.md", "rules/*.md"))

    def test_package_metadata_and_cli_version_source_stay_aligned(self) -> None:
        self.assertEqual(version("ctxfire"), __version__)


if __name__ == "__main__":
    unittest.main()
