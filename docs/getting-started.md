# Getting Started

This guide walks through the most common usage patterns.

---

## Lengow — orders to Supabase

```python
from etail_marketplaces_sdk import (
    LengowClient,
    LengowCredentials,
    SupabaseSinkConnector,
    StreamType,
)
from etail_marketplaces_sdk.models import Brand

creds = LengowCredentials(
    account_id="your_account",
    token="your_token",
    secret="your_secret",
)

brand = Brand(id=1, name="My Super Brand", slug="my-brand", initials="MSB")

client = LengowClient(credentials=creds, brand=brand, aggregator_id=3)

sink = SupabaseSinkConnector(
    url="https://your-project.supabase.co",
    key="your-service-role-key",
)

orders = client.fetch_orders(days_ago=7)
result = sink.write_orders(orders)

print(f"Processed {result.processed_count} orders")
if result.errors:
    print(f"Errors: {len(result.errors)}")
```

---

## ChannelEngine — shipments API (default)

Suitable for tenants whose API key has access to `GET /v2/shipments`.
Only `CLOSED` (fully shipped) records are returned.

```python
from decimal import Decimal
from etail_marketplaces_sdk.aggregators.channelengine.client import ChannelEngineClient
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.models.brand import Brand

brand = Brand(
    id=5,
    name="My Brand",
    slug="my-brand",
    initials="MB",
    logo_url="",
    company_info="",
    invoice_footer_text="",
)

client = ChannelEngineClient(
    credentials=ApiKeyCredentials(api_key="<api-key>"),
    base_url="https://<tenant>.channelengine.net/api",
    brand=brand,
    marketplace_id=10,
    tax_rate=Decimal("20"),
    # orders_api=False is the default
)

orders   = client.fetch_orders(days_ago=30)
invoices = client.fetch_invoices(days_ago=30)
```

---

## ChannelEngine — orders API (`orders_api=True`)

Use this mode when the tenant's API key only has access to `GET /v2/orders`
(e.g. Villeroy & Boch).  This endpoint returns all order statuses and includes
full billing and shipping address data — making it the richer data source when
available.

`fetch_invoices()` automatically restricts results to `SHIPPED` and `CLOSED`
orders, so no extra filtering is needed.

```python
from decimal import Decimal
from etail_marketplaces_sdk.aggregators.channelengine.client import ChannelEngineClient
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.models.brand import Brand

brand = Brand(
    id=9,
    name="Villeroy & Boch",
    slug="villeroy_boch",
    initials="VNB",
    logo_url="https://storage.googleapis.com/invoices-services/vnb/vnb_logo.png",
    company_info="",
    invoice_footer_text="",
)

client = ChannelEngineClient(
    credentials=ApiKeyCredentials(api_key="<api-key>"),
    base_url="https://villeroy-boch-prod-etail.channelengine.net/api",
    brand=brand,
    marketplace_id=42,
    tax_rate=Decimal("20"),
    orders_api=True,           # switch to /v2/orders
)

# All statuses (NEW, IN_PROGRESS, SHIPPED, CLOSED, …)
orders = client.fetch_orders(days_ago=30)

# Only SHIPPED / CLOSED — invoice-ready, with full billing address
invoices = client.fetch_invoices(days_ago=30)

# Single-order lookup
order   = client.fetch_order("ORDER-001")
invoice = client.fetch_invoice_for_order("ORDER-001")  # None if not yet shipped
```
