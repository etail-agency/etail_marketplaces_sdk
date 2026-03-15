# Marketplaces API

Marketplace clients connect directly to a platform's seller API (no middleware aggregator).
They share the same public interface as aggregator clients and extend it with raw access methods.

| Method | Returns | Description |
|---|---|---|
| `fetch_orders(days_ago)` | `list[Order]` | Normalised orders for the last N days |
| `fetch_invoices(days_ago)` | `list[Invoice]` | Normalised invoices for the last N days |
| `fetch_order(order_id)` | `Order` | Normalised single order by ID |
| `fetch_raw_orders(days_ago)` | `list[dict]` | **Raw** platform payloads — no normalisation |
| `fetch_stock(skus)` | `list[StockLevel]` | Normalised stock levels *(Mirakl)* |
| `fetch_raw_stock(skus)` | `list[dict]` | **Raw** stock payloads *(Mirakl)* |
| `fetch_catalogue(skus, updated_since)` | `list[Product]` | Normalised product listings *(Mirakl)* |
| `fetch_raw_catalogue(skus, updated_since)` | `list[dict]` | **Raw** product payloads *(Mirakl)* |

!!! tip "Accessing raw data"
    Every normalised model also carries a `.raw` field containing the original
    platform dict.  `fetch_raw_orders()` gives you the same data **without**
    constructing the canonical model — useful when you need platform-specific
    fields that the `Order` model does not expose.

---

## ManoMano

::: etail_marketplaces_sdk.marketplaces.manomano.client

---

## Mirakl

The `MiraklClient` targets the **Mirakl Seller API** (`seller_openapi.json`).

### Endpoints used

| Stream | Endpoint | Operation |
|---|---|---|
| Orders | `GET /api/orders` | OR11 |
| Stock | `GET /api/offers` | OF21 |
| Catalogue | `GET /api/offers` | OF21 |

!!! note "Why OF21 for both stock and catalogue?"
    Mirakl's P31 Products endpoint requires explicit product references and does not support
    full-catalogue pagination.  OF21 Offers returns the same data with richer fields
    (`product_title`, `product_brand`, `product_description`, `price`, `active`,
    `category_code`) and full offset pagination — making it the right source for both
    stock levels and product listings.

### Usage

```python
from etail_marketplaces_sdk.marketplaces.mirakl.client import MiraklClient
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials

client = MiraklClient(
    credentials=ApiKeyCredentials(api_key="<your-api-key>"),
    base_url="https://<tenant>.mirakl.net",
    marketplace_id=10,
)

# Orders
orders = client.fetch_orders(days_ago=7)

# Stock levels
stock = client.fetch_stock()                         # all offers
stock = client.fetch_stock(skus=["SKU-A", "SKU-B"]) # filtered

# Product catalogue (same OF21 source, different mapper)
products = client.fetch_catalogue()
products = client.fetch_catalogue(skus=["SKU-A"])

# Raw payloads
raw_orders  = client.fetch_raw_orders(days_ago=7)
raw_stock   = client.fetch_raw_stock()
raw_catalogue = client.fetch_raw_catalogue()
```

### Client reference

::: etail_marketplaces_sdk.marketplaces.mirakl.client

### Base

::: etail_marketplaces_sdk.marketplaces.base
