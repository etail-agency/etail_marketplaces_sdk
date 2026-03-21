# eTAIL Marketplaces SDK

Welcome to the documentation for the `etail-marketplaces-sdk`.

This is a unified Python SDK for eCommerce marketplace and aggregator APIs. Its core purpose is to provide a single, consistent interface to **fetch, normalise, and sink** data streams across multiple platforms.

## Key Features

- **Unified Interface**: One way to fetch orders, stock, catalogue, etc., regardless of the underlying platform.
- **Aggregators & Marketplaces**: Support for Lengow, ShoppingFeed, ChannelEngine, ManoMano, Mirakl.
- **Built-in Sinks**: Write data directly to Supabase, PostgreSQL, or BigQuery.
- **Idempotent**: All sink connectors use upsert semantics so pipelines can be safely re-run.
- **Traceability**: Every canonical model stores the unmodified platform payload in a `raw` field.
- **Tested**: CI runs **pytest** over mapper and small client tests (mocked HTTP). Run `uv run pytest` locally after installing dev dependencies; see **Architecture** and the repo **CONTRIBUTING.md**.

## Quick Install

```bash
pip install etail-marketplaces-sdk
```

With optional sinks:
```bash
pip install "etail-marketplaces-sdk[supabase]"
pip install "etail-marketplaces-sdk[postgres]"
pip install "etail-marketplaces-sdk[bigquery]"
pip install "etail-marketplaces-sdk[all]"
```
