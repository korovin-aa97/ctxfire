# Pricing assumptions

`ctxfire` ships without built-in vendor prices. Prices change, model aliases can
move, prompt caching depends on runtime behavior, and subscription plans are not
equivalent to API input-token billing.

To show a planning estimate, explicitly configure:

```toml
[project]
model = "the-exact-model-id-you-use"
price_date = "YYYY-MM-DD"
usd_per_million_input_tokens = 0.0 # replace with verified input price
cache_assumption = "no-cache-credit"
```

Use the vendor's official pricing page on the date recorded. `ctxfire` multiplies
the configured input price by estimated input tokens. It does not include output
tokens, tools, storage, regional taxes, subscription quotas, negotiated pricing,
or observed cache reads/writes.

For planning, no-cache credit is conservative. For accounting, use actual vendor
usage records rather than this static model.
