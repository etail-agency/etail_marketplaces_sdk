# Getting Started

Here is a quick example of how to use the SDK to fetch orders from an aggregator and write them to a database.

## 1. Import and Initialize

```python
from etail_marketplaces_sdk import (
    LengowClient, 
    LengowCredentials, 
    SupabaseSinkConnector,
    StreamType
)
from etail_marketplaces_sdk.models import Brand

# 1. Setup Credentials
creds = LengowCredentials(
    account_id="your_account",
    token="your_token",
    secret="your_secret"
)

# 2. Setup Brand context
brand = Brand(
    id="brand_123",
    name="My Super Brand"
)

# 3. Initialize Client
client = LengowClient(
    credentials=creds,
    brand=brand,
    aggregator_id=3
)

# 4. Initialize Sink
sink = SupabaseSinkConnector(
    url="https://your-project.supabase.co",
    key="your-service-role-key"
)
```

## 2. Fetch and Sink Data

```python
from datetime import datetime, timedelta

# Fetch orders from the last 7 days
since = datetime.utcnow() - timedelta(days=7)

# The client handles pagination and rate limiting automatically
orders_iterator = client.fetch_orders(since=since)

# Write to Supabase (handles batching and upserts automatically)
result = sink.write_orders(orders_iterator)

print(f"Successfully processed {result.processed_count} orders!")
if result.errors:
    print(f"Encountered {len(result.errors)} errors.")
```
