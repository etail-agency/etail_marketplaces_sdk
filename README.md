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

| Platform | Orders | Invoices | Shipments | Stock | Catalogue |
|---|:---:|:---:|:---:|:---:|:---:|
| [Lengow](https://www.lengow.com) | ✅ | ✅ | | | |
| [ShoppingFeed](https://www.shopping-feed.com) | ✅ | ✅ | | ✅ | ✅ |
| [ChannelEngine](https://www.channelengine.com) | ✅ | ✅ | ✅ | ✅ | ✅ |

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
from etail_marketplaces_sdk import LengowClient, LengowCredentials
from etail_marketplaces_sdk.models import Brand

brand = Brand(id=1, name="My Brand", slug="my-brand", initials="MB")

client = LengowClient(
    credentials=LengowCredentials(
        account_id="<account-id>",
        token="<token>",
        secret="<secret>",
    ),
    brand=brand,
    aggregator_id=3,
)

orders   = client.fetch_orders(days_ago=7)
invoices = client.fetch_invoices(days_ago=7)
```

See [Getting Started](docs/getting-started.md) for ChannelEngine, ShoppingFeed, and sink connector examples.

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

### ChannelEngine — dual endpoint support

ChannelEngine exposes two data sources.  Pass `orders_api=True` to the client to switch:

| `orders_api` | Endpoint | Statuses | Address |
|---|---|---|---|
| `False` *(default)* | `GET /v2/shipments` | `CLOSED` only | — |
| `True` | `GET /v2/orders` | All | Full billing & shipping |

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

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, code standards, the development workflow, and the full release process.
