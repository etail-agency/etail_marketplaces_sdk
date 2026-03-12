# Architecture

The SDK follows a strict three-layer pipeline:

```mermaid
flowchart LR
    A[Credentials] --> B(Client)
    B -->|Fetch Raw| C(Mapper)
    C -->|Normalise| D[Canonical Model]
    D --> E(Sink)
    E -->|Write| F[(Database)]
```

1. **Clients**: Handle authentication, pagination, and rate limit detection.
2. **Mappers**: Convert raw API `dict` responses into canonical model instances. The raw payload is always stored in the `raw` field of every model for traceability.
3. **Canonical Models**: Plain Python `@dataclass` objects with a `to_dict()` method for serialisation.
4. **Sinks**: Write data to storage (Supabase, Postgres, BigQuery) using idempotent upsert semantics.
