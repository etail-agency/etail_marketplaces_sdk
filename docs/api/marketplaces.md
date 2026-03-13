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
| `fetch_catalogue(updated_since)` | `list[Product]` | Normalised product listings *(Mirakl)* |
| `fetch_raw_catalogue(updated_since)` | `list[dict]` | **Raw** product payloads *(Mirakl)* |

!!! tip "Accessing raw data"
    Every normalised model also carries a `.raw` field containing the original
    platform dict.  `fetch_raw_orders()` gives you the same data **without**
    constructing the canonical model — useful when you need platform-specific
    fields that the `Order` model does not expose.

---

::: etail_marketplaces_sdk.marketplaces.base
::: etail_marketplaces_sdk.marketplaces.manomano.client
::: etail_marketplaces_sdk.marketplaces.mirakl.client
