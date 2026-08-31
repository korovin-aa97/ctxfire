# Contributing

Thank you for helping make agent context costs explainable.

1. Open an issue for a loading-semantics change before implementing it.
2. Keep runtime code dependency-free unless a dependency has a clear accuracy
   or security benefit.
3. Add a regression fixture for every adapter/discovery quirk.
4. Keep reports repository-relative, never emit file content, and declare any
   adapter that requires narrow local content parsing.
5. Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`,
   `bandit -q -r src`, and `python -m build`.

Adapters and report schemas are public APIs. A changed engine behavior needs an
official source link, an uncertainty note, and either a compatible adapter
patch or a new adapter version. Do not silently change existing semantics.

By participating you agree to the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
