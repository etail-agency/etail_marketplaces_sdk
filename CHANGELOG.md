# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Released]

## [Unreleased]

### Added

- **`Order.marketplace_name`** and **`Order.commission`**: Optional canonical fields populated from platform payloads where available (`Lengow`, `ShoppingFeed`, `ChannelEngine` orders + shipments, `Mirakl`, `ManoMano`).
- **`core.decimal_utils.optional_decimal`**: Shared safe parsing helper for mapper numeric fields.

## [0.3.1] - 2026-03-12

### Added

- **`docs/order_field_mapping.csv`**, **`docs/order_item_field_mapping.csv`**, **`docs/stock_field_mapping.csv`**: Cross-platform field maps (canonical model ↔ Lengow / ShoppingFeed / ChannelEngine / Mirakl raw payloads).

### Changed

- **Mirakl client**: HTTP 429 handling with `Retry-After` + exponential backoff; inter-page delay for OR11/OF21 pagination; adaptive delay increase after rate-limit events so large offer catalogues can complete.

### Fixed

- **Mirakl mappers**: Removed unused `ProductImage` import (Ruff F401).

### Repository

- **`.gitignore`**: Ignore `.DS_Store` (macOS Finder metadata).

## [0.3.0] - 2026-03-12

### Added — Catalogue & Stock streams for all aggregators + Mirakl spec alignment

#### Lengow — `CATALOGUE` stream

- **`fetch_catalogue(feed_id, nb_days_to_skip)` / `fetch_raw_catalogue(feed_id, nb_days_to_skip)`**: New public methods on `LengowClient` that call `GET /v1.0/report/export` — the only Lengow endpoint that exposes product data.  The response is a pipe-separated CSV whose column names are feed-specific; `feed_id` can be set once on the constructor or passed per-call.
- **`map_product()` in `aggregators/lengow/mappers.py`**: Best-effort mapper that resolves SKU, name, EAN, brand, description, category, price, and images from a set of common Lengow export column name patterns (e.g. `sku`/`merchant_sku`/`id_product`, `title`/`name`/`product_title`, etc.).  All unrecognised non-empty columns are preserved as `ProductAttribute` objects.
- `StreamType.CATALOGUE` added to `LengowClient.supported_streams`.
- New `feed_id: Optional[int]` constructor parameter on `LengowClient`.

#### ChannelEngine — `CATALOGUE` stream

- **`fetch_catalogue(skus)` / `fetch_raw_catalogue(skus)`**: New public methods on `ChannelEngineClient` that hit `GET /v2/products` with full offset pagination.  Optional `skus` list is forwarded as `merchantProductNoList` for targeted product lookup.
- **`map_product()` in `aggregators/channelengine/mappers.py`**: New mapper that converts a `MerchantProductResponse` record to a canonical `Product`, mapping `MerchantProductNo` → `sku`, `Name`, `Ean`, `Brand`, `Description`, `Price`, `IsActive`, `ImageUrl` (plus additional images from `ExtraImageUrl1`–`ExtraImageUrl3`), and `ExtraData` key/value pairs to `ProductAttribute` objects.
- `StreamType.CATALOGUE` added to `ChannelEngineClient.supported_streams`.

#### ShoppingFeed — `CATALOGUE` stream

- **`fetch_catalogue(updated_since, skus)` / `fetch_raw_catalogue(updated_since, skus)`**: New public methods on `ShoppingFeedClient` that hit `GET /v1/catalog/{catalogId}/reference` with page-based pagination.  `updated_since` maps to the `publishedAfter` query parameter; `skus` is forwarded as a comma-separated `reference` filter.
- **`map_product()` in `aggregators/shopping_feed/mappers.py`**: New mapper that converts a ShoppingFeed `reference` record to a canonical `Product`, mapping `reference` → `sku`, `id` → `platform_id`, `name`, `ean`/`gtin`, `price`, `description`, `brand`, `category`, images from `_embedded`, attributes from `_embedded`, and `status`/`state` to `is_active`.
- `StreamType.CATALOGUE` added to `ShoppingFeedClient.supported_streams`.

#### Mirakl — spec alignment (`specs/marketplaces/mirakl/seller_openapi.json`)

- **Consolidated catalogue + stock under OF21**: `fetch_catalogue()`, `fetch_raw_catalogue()`, `fetch_stock()`, and `fetch_raw_stock()` all delegate to the new `_fetch_raw_offers()` helper (`GET /api/offers`, OF21).  The removed `_fetch_raw_products()` (P31) is no longer needed — OF21 provides richer data (`product_title`, `product_brand`, `product_description`, `price`, `active`, `category_code`, `product_references`).
- **`map_product()` rewritten to use OF21 fields**: `shop_sku` → `sku`, `product_title` → `name`, `product_sku` → `platform_id`, `product_brand` → `brand`, `product_description` → `description`, `price` → `price_incl_vat`, `active` → `is_active`, EAN extracted from `product_references`.
- **`map_stock_level()` carries `raw`**: `raw=raw` is now passed to the `StockLevel` constructor for full traceability.

### Fixed — Mirakl mapper & client (`specs/marketplaces/mirakl/seller_openapi.json`)

- **Order totals**: `map_order()` now reads `price` for `eur_amount_incl_vat` and `shipping_price` for `eur_shipping_fee_incl_vat` (previously used non-existent `total_price` / `total_shipping_price` fields from the spec).
- **Order line items**: `_map_order_items()` now reads `price_unit` for `unit_price_incl_vat`, `product_title` for `name`, and `price` for `total_price_incl_vat` (previously used `unit_price`, `offer_title`, `total_price`).
- **Address mapping**: `_map_address()` / `_map_invoice_address()` now read `country_iso_code` directly (spec field), no longer treating `country` as a nested object.  New `_build_name()` helper combines `firstname`, `lastname`, and `company` consistently.
- **OF21 pagination was incomplete**: `_fetch_raw_offers()` previously fetched only one page.  Re-implemented with correct offset-based loop (`max=100`, `offset` increments), matching the OR11 pattern.
- **OF21 SKU filter parameter**: was sent as `shop_sku`; the correct OF21 parameter is `sku`.
- **OR11 pagination used wrong token**: `_fetch_raw_orders()` was using `next_page_token` (seek-based) instead of `offset` (offset-based) as defined in the OR11 spec.
- **`fetch_order()` lookup parameter**: now sends `order_ids` with `max=1` for single-order retrieval.

## [0.2.5] - 2026-03-12

### Fixed — spec alignment (`specs/aggregators/lengow/openapi.json` v3.0)

- **Critical: `currency` parsed as dict instead of string**: `map_order()` and `map_invoice()` stored `raw.get("currency", {})` and then called `.get("iso_a3", "EUR")` on the result. Per the spec, `Order.currency` is a plain ISO 4217 string (e.g. `"EUR"`), not an object — this would raise `AttributeError` whenever `currency` was present in the response. Fixed to read it directly as a string.
- **Critical: `original_currency` read from wrong field**: The mapper derived `original_currency` by calling `.get("iso_a3")` on the (now-fixed) `currency` dict. The spec exposes `original_currency` as a separate top-level string field. Fixed to read `raw.get("original_currency")` with a fallback to `currency`.
- **`second_line` and `complement` address fields ignored**: The spec's `Address` schema includes `second_line` (second address line) and `complement` (additional address detail). Both address mappers now populate `address_line2` (delivery) and append to the full street string (invoice).
- **`full_name` and `company` address fields ignored**: The spec provides a `full_name` field (the authoritative combined name from the platform) and a `company` field. The mappers now prefer `full_name` over manually combining `first_name`+`last_name`, and include `company` in the display name when present — matching the approach used by other platform mappers.
- **`invoice_number` field on `Order` not used**: The spec defines `Order.invoice_number` as a string field set by the marketplace. `map_invoice()` was always generating an invoice number from the payment ID (or a random fallback), ignoring this field. Now uses `raw.get("invoice_number")` when present, falling back to the payment-based logic only when it is absent.
- **Date filter sends `date` instead of `date-time`**: `_fetch_raw_orders()` computed `datetime.now().date()` and sent it as a plain `YYYY-MM-DD` string for `marketplace_order_date_from`. The spec defines this parameter as `format: date-time` (ISO 8601). Fixed to use a full `datetime` and format it as `YYYY-MM-DDTHH:MM:SS`.

## [0.2.4] - 2026-03-13

### Fixed — spec alignment (`specs/aggregators/shopping_feed/order.yml` v1.0)

- **Client-side date filter replaced with `since` query param**: `_fetch_raw_orders()` was computing a cutoff date and filtering the response client-side, iterating all pages and assuming orders were sorted by date (not guaranteed by the spec). Replaced with the `since` query parameter defined in the spec (`GET /v1/store/{storeId}/order`), so the API performs server-side filtering before pagination.
- **Wrong `channelId` field**: `map_order()` and `map_invoice()` read `raw.get("channelId")` which does not exist as a top-level field in the response. Per the spec example, channel info lives at `_embedded.channel.id`. Fixed to read `_embedded.channel.id` with a `channelId` top-level fallback for backwards compatibility.
- **`street2` ignored in address mapping**: The spec shows addresses include a `street2` field (second address line). `_map_address()` now populates `address_line2` and `_map_invoice_address()` appends it to the full street string. The `Address` model already had `address_line2: Optional[str]` — it was simply not being set.
- **`company` ignored in address name**: The spec example shows addresses include a `company` field. Both address mappers now include the company in the display name, consistent with other platform mappers.

### Documentation
- Updated spec cross-reference in `client.py` and `mappers.py` from non-existent `openapi.json` to the correct `order.yml` and `auth.yml` YAML files.

## [0.2.3] - 2026-03-13

### Fixed — spec alignment (`specs/aggregators/channelengine/openapi.json` v2.22.11)

- **Wrong shipments endpoint**: `_fetch_raw_shipments()` and `_fetch_shipment_by_order_no()` were calling `GET /v2/shipments`, which only accepts `POST` in the spec. Corrected to `GET /v2/shipments/merchant` (`ShipmentIndex` operation).
- **Wrong date filter parameter**: `_fetch_raw_shipments()` was sending `fromDate`; the correct parameter on `/v2/shipments/merchant` is `fromShipmentDate`.
- **Broken pagination in shipments mode**: the pagination loop compared the per-page `Count` against `TotalCount`, which would prematurely stop on any multi-page response. Replaced with the same `len(accumulated) >= TotalCount or not batch` pattern already used in `_fetch_raw_orders()`.
- **Wrong lookup parameter in `_fetch_order_by_channel_order_no()`**: sent `channelOrderNo` (singular string); the spec defines it as `channelOrderNos` (plural array).
- **Wrong tracking field in `map_shipment()`**: read `shipment.get("TrackAndTrace")` which does not exist in `MerchantShipmentResponse`. Corrected to `TrackTraceNo`.

## [0.2.2] - 2026-03-13

### Added
- **`fetch_raw_orders(days_ago)` on all clients**: Every client (`LengowClient`, `ShoppingFeedClient`, `ChannelEngineClient`, `ManomanoClient`, `MiraklClient`) now exposes a public `fetch_raw_orders()` method that returns the unmodified platform payloads as `list[dict]` — identical to the `.raw` field on each canonical `Order`, but without constructing the model.  On `ChannelEngineClient` the method respects the `orders_api` flag (hits `/v2/orders` or `/v2/shipments` accordingly).
- **`ChannelEngineClient.fetch_raw_shipments(days_ago)`**: Always hits `GET /v2/shipments`, regardless of `orders_api`.  Useful when you need the raw shipment record even on a tenant configured with `orders_api=True`.
- **`MiraklClient.fetch_raw_stock(skus)` / `fetch_raw_catalogue(updated_since)`**: Expose the raw Mirakl Offers (OF21) and Products (P11) payloads without normalisation.
- **`BaseClient.fetch_raw_orders`, `fetch_raw_shipments`, `fetch_raw_stock`, `fetch_raw_catalogue`**: Added as default-raising stubs to `BaseClient` (same pattern as `fetch_orders` etc.), making the raw-access contract part of the core interface.

### Documentation
- Updated `docs/api/aggregators.md` shared interface table to include all `fetch_raw_*` methods with return types.
- Updated `docs/api/marketplaces.md` shared interface table to include `fetch_raw_orders`, `fetch_raw_stock`, and `fetch_raw_catalogue`.

## [0.2.1] - 2026-03-13

### Added
- **ChannelEngine — `orders_api` mode**: `ChannelEngineClient` now accepts an `orders_api: bool = False` constructor parameter. When `True`, all data is fetched from `GET /v2/orders` instead of `GET /v2/shipments`. This is required for tenants whose API key lacks access to the shipments endpoint.
- **`map_order_from_orders_api()`**: New mapper in `aggregators/channelengine/mappers.py` that converts a `/v2/orders` record to a canonical `Order`. All price fields (excl- and incl-VAT, per-line VAT rate, GTIN) are read directly from the richer orders payload — no back-calculation needed.
- **`map_invoice_from_orders_api()`**: New mapper that produces a canonical `Invoice` from a `/v2/orders` record. Automatically restricts to `SHIPPED` and `CLOSED` statuses and populates full `BillingAddress` and `ShippingAddress` from the order's address blocks.
- **`ChannelEngineClient.fetch_invoice_for_order(order_id)`**: New public method for fetching the invoice of a single order by `ChannelOrderNo`. Returns `None` when the order has not yet been shipped.
- **`_fetch_raw_orders()` / `_fetch_order_by_channel_order_no()`**: New private HTTP helpers on `ChannelEngineClient` for paginated access to `GET /v2/orders`.

### Fixed
- Missing `Decimal` type annotation on `tax_rate` parameter of `LengowClient.__init__` (caused `mkdocs build --strict` to abort).

### Documentation
- Updated `docs/api/aggregators.md` with a dedicated ChannelEngine section: dual-mode comparison table, full usage examples for both `orders_api=True` and `orders_api=False`, and explicit mkdocstrings references for all five public mapper functions.
- Updated `docs/getting-started.md` with ChannelEngine examples for both shipments mode and orders mode.
- Updated `README.md` Quick Start and Architecture sections to document the dual-endpoint support.

## [0.1.0] - 2026-03-12

### Added
- Initial base implementation of the `etail-marketplaces-sdk`.
- Support for Aggregators: Lengow, ShoppingFeed, ChannelEngine.
- Support for Marketplaces: ManoMano, Mirakl.
- Base Sink Connectors: Postgres, Supabase, BigQuery.
