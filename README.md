# eTAIL Marketplaces SDK

> Unified Python SDK for eCommerce marketplace and aggregator APIs.

Fetch, normalise, and sink data streams (orders, stock, catalogue, shipments, returns, invoices, analytics, ads, settlements, reviews) across multiple platforms — all with a single, consistent interface.

[![CI](https://github.com/etail-agency/etail_marketplaces_sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/etail-agency/etail_marketplaces_sdk/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/etail-marketplaces-sdk)](https://pypi.org/project/etail-marketplaces-sdk/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Supported Platforms

**Aggregators**

| Platform | Orders | Invoices | Shipments |
|---|:---:|:---:|:---:|
| [Lengow](https://www.lengow.com) | ✅ | ✅ | |
| [ShoppingFeed](https://www.shopping-feed.com) | ✅ | ✅ | |
| [ChannelEngine](https://www.channelengine.com) | ✅ | ✅ | ✅ |

**Marketplaces**

| Platform | Orders | Invoices | Stock | Catalogue |
|---|:---:|:---:|:---:|:---:|
| [ManoMano](https://www.manomano.fr) | ✅ | ✅ | | |
| [Mirakl](https://www.mirakl.com) | ✅ | ✅ | ✅ | ✅ |

**Sink Connectors**

| Connector | Orders | Invoices | All Streams |
|---|:---:|:---:|:---:|
| Supabase | ✅ | ✅ | ✅ |
| BigQuery | ✅ | ✅ | ✅ |
| PostgreSQL | ✅ | ✅ | |

---

## Installation

```bash
pip install etail-marketplaces-sdk
```

Install with optional sink connectors:

```bash
pip install "etail-marketplaces-sdk[supabase]"
pip install "etail-marketplaces-sdk[postgres]"
pip install "etail-marketplaces-sdk[bigquery]"
pip install "etail-marketplaces-sdk[all]"
```

---

## Quick Start

```python
from etail_marketplaces_sdk import (
    LengowClient,
    LengowCredentials,
    SupabaseSinkConnector,
)
from datetime import datetime, timedelta

# 1. Credentials
creds = LengowCredentials(
    access_token="your_access_token",
    secret="your_secret",
)

# 2. Client
client = LengowClient(credentials=creds, aggregator_id=3)

# 3. Sink
sink = SupabaseSinkConnector(
    url="https://your-project.supabase.co",
    key="your-service-role-key",
)

# 4. Fetch & write
orders = client.fetch_orders(since=datetime.utcnow() - timedelta(days=7))
result = sink.write_orders(orders)

print(f"Processed {result.processed_count} orders")
```

---

## Architecture

The SDK follows a strict three-layer pipeline:

```
Credentials → Client (fetch) → Mapper (normalise) → Canonical Model → Sink (write)
```

- **Clients** handle authentication, pagination, and rate-limit retries.
- **Mappers** convert raw platform payloads to canonical models. Each mapper is the only file that changes when a platform spec changes.
- **Canonical Models** are plain Python `@dataclass` objects with a `raw` field for full traceability.
- **Sinks** write data with upsert semantics so pipelines can be safely re-run.

---

## Development

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install all dependencies
uv sync --all-extras

# Lint
uv run ruff check .

# Serve docs locally
uv run mkdocs serve

# Bump version (patch | minor | major)
uv run bump-my-version bump patch
```

---

## Contributing

Contributions are welcome! To add a new platform:

1. Create a new folder under `etail_marketplaces_sdk/aggregators/` or `etail_marketplaces_sdk/marketplaces/`.
2. Add a `client.py` (extends `BaseAggregator` or `BaseMarketplace`) and a `mappers.py`.
3. Drop the platform's OpenAPI spec in `specs/`.
4. Expose the new client in the root `__init__.py`.
