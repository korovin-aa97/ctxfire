# Extension guide

## Add an adapter

1. Find a primary, official source for the engine's loading behavior.
2. Document precedence, roots, conditional behavior, and uncertainty in
   `ADAPTER_SPEC.md` with a checked date.
3. Add the versioned adapter name to config validation.
4. Return explicit `Inclusion` rules from `adapters.inclusions`.
5. Add fixtures for nested instructions, missing files, conditional candidates,
   duplicates, excludes, and unusual paths.
6. Confirm `explain` attributes every edge.

Precedence and byte caps belong in the adapter and must remain visible in edge
reasons, `counted_bytes`, and warnings. Do not model a full skill body as
always-on merely because its name/description catalog is visible at startup.

Do not parse arbitrary executable config or silently reach outside the project
root. A semantics change needs a new adapter version.

## Add a tokenizer

The default v0.1 estimator is deliberately dependency-free; the `tokenizers`
extra provides an opt-in tiktoken backend. Any further tokenizer extension must:

- be opt-in and name/version itself in `assumptions.tokenizer`;
- operate locally without uploading content;
- distinguish unavailable tokenizer errors from byte-estimate fallback;
- document normalization and special-token behavior;
- retain exact byte facts and schema compatibility;
- include multilingual Markdown and source-code fixtures.

Tokenizer support is not permission to print or retain file contents.

## Add a report field

Optional additive fields can remain in schema 1.0 after updating the JSON Schema
and stability tests. Changes to type, aggregation, required fields, or meaning
need a new schema and a migration note.
