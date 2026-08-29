from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ctxfire.adapters import matches
from ctxfire.cli import EXIT_BUDGET_EXCEEDED, EXIT_ERROR, EXIT_OK, main
from ctxfire.config import load_config
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
        self.assertEqual("1.0", json.loads(after.read_text())["schema_version"])
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

    def test_bad_schema_is_a_controlled_error(self) -> None:
        config = self.config()
        config.write_text('schema_version = "99"\n', encoding="utf-8")
        self.assertEqual(EXIT_ERROR, main(["scan", "--config", str(config)]))


class PatternTests(unittest.TestCase):
    def test_double_star_matches_zero_or_more_directories(self) -> None:
        self.assertTrue(matches(".agents/skills/x/SKILL.md", ".agents/skills/*/SKILL.md"))
        self.assertTrue(matches("rules/python.md", "**/*.md"))
        self.assertTrue(matches("rules/python.md", "rules/**/*.md"))

    def test_single_star_does_not_cross_directories(self) -> None:
        self.assertTrue(matches("README.md", "README*"))
        self.assertFalse(matches("docs/README.md", "README*"))
        self.assertFalse(matches("rules/nested/python.md", "rules/*.md"))


if __name__ == "__main__":
    unittest.main()
