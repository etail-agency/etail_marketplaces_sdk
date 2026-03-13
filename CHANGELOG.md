# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Released]

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
