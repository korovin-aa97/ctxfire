# Privacy and data handling

`ctxfire` is local-only and telemetry-free. Its default byte estimator is
dependency-free. Metadata-only adapters read file sizes; the content-aware
`claude-code@2` adapter reads a narrow set of matched Markdown files locally.

It reads:

- `ctxfire.toml` configuration;
- Git's candidate path list;
- file type and byte size for eligible matched paths;
- file type and byte size for known exact engine/config paths, even if ignored;
- matched Claude rule, skill, and subagent Markdown when `claude-code@2` needs
  frontmatter or catalog fields;
- JSON snapshots explicitly supplied to `diff`.

With `explicit@1`, `agents-md@1`, `codex@1`, or `claude-code@1` and the default
byte estimator, it does not read context-file contents. With
`claude-code@2`, it reads only matched rule, skill, and subagent Markdown in
memory and reports `discovery.content_access = "matched-file-content-local"`.
In every mode it does not follow symlinks (including a symlinked parent
directory), call a model, upload a report, access a vendor API, add hooks, or
make network requests. The package contains no telemetry identifier.

If the user explicitly configures `tiktoken:<encoding>` and installs the
`tokenizers` extra, matched file bytes are read and tokenized locally in memory.
They are not printed, retained, or uploaded. Machine reports declare this as
`discovery.content_access = "matched-file-content-local"` and record the
tokenizer package version.

Default reports contain user-selected project/agent labels, relative paths,
file sizes, assumptions, and estimates. Relative paths can still reveal project
structure. Review JSON/SARIF before publishing it from a private repository.

The scanner executes local Git with a fixed argument array and `shell=False`.
Repository files are never executed. A malicious repository can still contain
very large indexes or rapidly changing files; run untrusted scans with ordinary
least privilege and normal resource controls.
