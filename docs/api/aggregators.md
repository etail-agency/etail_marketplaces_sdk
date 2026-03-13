# Aggregators API

Aggregator clients authenticate against third-party platform APIs, paginate
through responses, handle rate limits, and delegate field mapping to their
companion `mappers.py` module.

All clients extend `BaseAggregator` and share the same public interface:

| Method | Returns | Description |
|---|---|---|
| `fetch_orders(days_ago)` | `list[Order]` | Normalised orders for the last N days |
| `fetch_invoices(days_ago)` | `list[Invoice]` | Normalised invoices for the last N days |
| `fetch_shipments(days_ago)` | `list[Shipment]` | Normalised shipments for the last N days |
| `fetch_order(order_id)` | `Order` | Normalised single order by ID |
| `fetch_raw_orders(days_ago)` | `list[dict]` | **Raw** platform payloads — no normalisation |
| `fetch_raw_shipments(days_ago)` | `list[dict]` | **Raw** shipment payloads *(ChannelEngine only)* |

!!! tip "Accessing raw data"
    Every normalised model also carries a `.raw` field containing the original
    platform dict.  `fetch_raw_orders()` gives you the same data **without**
    constructing the canonical model — useful when you need platform-specific
    fields that the `Order` model does not expose.

---

## Base

::: etail_marketplaces_sdk.aggregators.base

---

## Lengow

::: etail_marketplaces_sdk.aggregators.lengow.client

---

## ShoppingFeed

::: etail_marketplaces_sdk.aggregators.shopping_feed.client

---

## ChannelEngine

ChannelEngine exposes two different data sources for order-related data.  The
client supports both via the `orders_api` constructor flag.

### API modes

| Mode | Endpoint | Statuses returned | Address data | When to use |
|---|---|---|---|---|
| `orders_api=False` *(default)* | `GET /v2/shipments` | `CLOSED` only | ✗ | Tenants with shipment API access |
| `orders_api=True` | `GET /v2/orders` | All statuses | ✓ Full billing & shipping | Tenants whose API key only has order access |

> **Note — invoices in `orders_api=True` mode.**  
> `fetch_invoices()` automatically filters to `SHIPPED` and `CLOSED` orders,
> so you always get invoice-ready records without extra filtering.

### Usage — orders API mode

```python
from decimal import Decimal
from etail_marketplaces_sdk.aggregators.channelengine.client import ChannelEngineClient
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.models.brand import Brand

brand = Brand(
    id=1,
    name="My Brand",
    slug="my_brand",
    initials="MB",
    logo_url="https://storage.example.com/my-brand/logo.png",
    company_info="",
    invoice_footer_text="",
)

client = ChannelEngineClient(
    credentials=ApiKeyCredentials(api_key="<your-api-key>"),
    base_url="https://<tenant>.channelengine.net/api",
    brand=brand,
    marketplace_id=42,        # must match a row in your marketplace table
    tax_rate=Decimal("20"),
    orders_api=True,           # use /v2/orders instead of /v2/shipments
)

# Fetch all orders from the last 30 days (all statuses)
orders = client.fetch_orders(days_ago=30)

# Fetch invoices — only SHIPPED / CLOSED orders, with full billing address
invoices = client.fetch_invoices(days_ago=30)

# Fetch a single order + its invoice in one call
order   = client.fetch_order("ORDER-001")
invoice = client.fetch_invoice_for_order("ORDER-001")  # None if not yet shipped
```

### Usage — shipments API mode (default)

```python
client = ChannelEngineClient(
    credentials=ApiKeyCredentials(api_key="<your-api-key>"),
    base_url="https://<tenant>.channelengine.net/api",
    brand=brand,
    marketplace_id=42,
    # orders_api defaults to False → uses /v2/shipments
)

orders   = client.fetch_orders(days_ago=30)    # CLOSED shipments only
invoices = client.fetch_invoices(days_ago=30)
```

### Client reference

::: etail_marketplaces_sdk.aggregators.channelengine.client

### Mappers reference

The mapper module is the **single file** that encodes all field-mapping logic.
Update it when the ChannelEngine OpenAPI spec changes.

::: etail_marketplaces_sdk.aggregators.channelengine.mappers
    options:
      members:
        - map_order
        - map_invoice
        - map_shipment
        - map_order_from_orders_api
        - map_invoice_from_orders_api
