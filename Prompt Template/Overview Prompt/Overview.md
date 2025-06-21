# AI‑Powered Skincare Recommendation Platform – Technical Design Document

---

## 1  Purpose & Scope

A backend‑only service that transforms structured outputs from a skin‑analysis model into product suggestions obtained and refreshed automatically from multiple online retailers. The platform must:

* Deliver sub‑100 ms recommendations via a REST/CLI interface.
* Maintain a fresh, de‑duplicated catalogue with price history.
* Allow clients to re‑order results by relevance (default), price, brand, rating, etc.
* Operate legally (respecting robots.txt) and be cloud‑deployable.

## 2  Key Functional Components

| Layer                    | Responsibilities                                                                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Crawlers**             | Scrape retailer product listings, write raw JSON to *staging\_raw\_offers*.                                                                                  |
| **ETL / Normaliser**     | Parse, dedupe, tag skin‑conditions, upsert into canonical tables, log price deltas.                                                                          |
| **Catalogue DB**         | Relational schema storing *products*, *offers*, *price\_history*, *condition\_tags*. Materialised view `products_latest` pre‑joins latest offer per product. |
| **Recommendation API**   | FastAPI service; queries `products_latest`, ranks by relevance, applies optional sort adapters, returns JSON.                                                |
| **Scheduler**            | Orchestrates crawls, ETL, view refresh. Cron, Airflow or APScheduler.                                                                                        |
| **Logging & Monitoring** | Tracks crawler health, ETL success, API latencies, price anomalies.                                                                                          |

## 3  High‑Level Architecture

```
┌─ Skin‑Analysis Model ─┐
│   {condition, area}   │
└─────────┬─────────────┘
          ▼ (JSON)
 ┌────────────────────────────┐
 │  Recommendation Service    │  ⇢  /recommend?condition=acne&sort=price_low
 └─────┬──────────┬──────────┘
       │ default  │ alt sort
       ▼          ▼
   Relevance   Sort Adapter
     Ranker      (price, …)
       │ SQL              ▲
       ▼                  │
┌────────────────────────────┐
│  products_latest view      │  (materialised)
└────────┬───────────────────┘
         │ nightly REFRESH
         ▼
┌────────────────────────────┐
│   Canonical Catalogue DB   │
└────────┬─┬─────────────────┘
         │ │  upserts / deltas
         │ ▼
         │ ETL & Normaliser
         │ (tagger, dedupe)
         ▼
 Staging Raw Offers  ◄─ Crawlers (Scrapy + Playwright)
```

## 4  Data Acquisition Layer

### 4.1  Crawling Strategy

* **Tools**: Scrapy + Playwright (Chromium) for JS‑heavy pages.
* **Retailers**: Sephora, Ulta, Dermstore (extensible).
* **Concurrency**: `CONCURRENT_REQUESTS=8`, AutoThrottle, 1.5 s download delay.
* **Full crawl**: once per week/site.
* **Delta crawl**: category pages every 3 hours.
* **Output schema** (`staging_raw_offers`):

  | column         | type      | description                    |
  | -------------- | --------- | ------------------------------ |
  | offer\_id      | TEXT PK   | retailer + SKU \[+ shade/size] |
  | json\_blob     | JSONB     | raw scraped payload            |
  | last\_seen\_ts | TIMESTAMP | updated each crawl             |

### 4.2  Robustness & Compliance

* Custom User‑Agent, retries with backoff, obey `robots.txt`.
* Store HTTP status & checksum to detect layout changes.

## 5  ETL & Normalisation Pipeline

1. **Load** unsynced `staging_raw_offers` rows.
2. **Parse & Clean** → brand, name, variant, price, rating, availability.
3. **Canonical ID**: `slug(brand)__slug(name)__slug(variant)`.
4. **Upsert** into `products` (one row per canonical ID).
5. **Upsert** into `offers` (one per retailer × product).
6. **Price diff** → insert into `price_history` if changed.
7. **Tagger**: regex + optional LLM classification ⇒ write rows in `condition_tags`.
8. Mark rows as synced.

Implemented with Pandas + SQLAlchemy bulk operations; runtime ≤60 s for 10 k changed offers.

## 6  Database Schema (PostgreSQL‑ish)

```sql
products(
  product_id    TEXT  PRIMARY KEY,
  brand         TEXT,
  name          TEXT,
  variant       TEXT,
  ingredients   TEXT,
  created_ts    TIMESTAMP DEFAULT NOW()
);
offers(
  offer_id      TEXT  PRIMARY KEY,
  product_id    TEXT  REFERENCES products,
  retailer      TEXT,
  price         NUMERIC(10,2),
  currency      CHAR(3),
  rating        NUMERIC(2,1),
  url           TEXT,
  availability  TEXT,
  last_seen_ts  TIMESTAMP,
  etl_sync_ts   TIMESTAMP
);
price_history(
  offer_id  TEXT REFERENCES offers,
  ts        TIMESTAMP,
  price     NUMERIC(10,2),
  PRIMARY KEY(offer_id, ts)
);
condition_tags(
  product_id TEXT REFERENCES products,
  condition  TEXT,
  PRIMARY KEY(product_id, condition)
);
detection_logs(
  id         SERIAL PRIMARY KEY,
  condition  TEXT,
  area       TEXT,
  ts         TIMESTAMP DEFAULT NOW()
);
-- fast read view
CREATE MATERIALIZED VIEW products_latest AS
SELECT DISTINCT ON (o.product_id) o.*, p.brand, p.name, p.variant
FROM offers o JOIN products p USING(product_id)
ORDER BY o.product_id, o.last_seen_ts DESC;
CREATE INDEX idx_cond ON condition_tags(condition);
```

## 7  Recommendation Service

### 7.1  Relevance Scoring

```python
def relevance_score(row, cond):
    tag_hit   = cond in row["condition_tags"].split(';')
    price_pen = min(float(row["price"])/100, 1)
    return 5*tag_hit + 0.5*(row["rating"] or 0) - price_pen
```

Default SQL `ORDER BY` replicates this weight to avoid Python sorting for most calls.

### 7.2  Sort Adapter

```python
SORTS = {
  "relevance": lambda rows: rows,
  "price_low": lambda rows: sorted(rows, key=lambda r: r["price"]),
  "price_high": lambda rows: sorted(rows, key=lambda r: -r["price"]),
  "brand":     lambda rows: sorted(rows, key=lambda r: r["brand"].lower()),
  "rating":    lambda rows: sorted(rows, key=lambda r: -(r["rating"] or 0)),
}
```

### 7.3  API Contract (FastAPI)

```
GET /recommend?condition=wrinkles&area=forehead&sort=price_low&top=20
Response 200 JSON:
[
  {
    "product_id": "glowco__anti_wrinkle_50ml",
    "brand": "GlowCo",
    "name": "Anti‑Wrinkle Cream",
    "price": 29.99,
    "rating": 4.6,
    "retailer": "Sephora",
    "url": "https://…"
  }, …
]
```

## 8  Scheduling & Orchestration

| Job                           | Tool                                     | Frequency            | Trigger          |
| ----------------------------- | ---------------------------------------- | -------------------- | ---------------- |
| **delta\_crawl\_{site}**      | Scrapy CLI                               | Every 3 h            | Cron/Airflow DAG |
| **full\_crawl\_{site}**       | Scrapy                                   | Weekly               | Cron/DAG         |
| **etl\_normalise**            | Python script                            | Hourly or post‑crawl | DAG dependency   |
| **refresh\_products\_latest** | `REFRESH MATERIALIZED VIEW CONCURRENTLY` | 15 min               | APScheduler      |

Small teams can replace Airflow with simple cron and a `make all` shell.

## 9  Performance Targets & Tuning

| Metric                  | Target                  | Notes                                                                                  |
| ----------------------- | ----------------------- | -------------------------------------------------------------------------------------- |
| **API p95 latency**     | < 120 ms                | Index on `condition`, small result sets; optional Redis cache keyed by `(cond, sort)`. |
| **Catalogue staleness** | < 4 h for delta pages   | Controlled by crawl interval.                                                          |
| **ETL runtime**         | < 2 min per 10 k offers | Bulk upserts & vectorised Pandas.                                                      |

Scaling path: read replicas, pgBouncer, horizontal FastAPI pods.

## 10  Deployment & Ops

* **Containers**: Single Dockerfile with multi‑stage build.
* **Infra**: Postgres (RDS/Aurora), ECS/Kubernetes for API & workers.
* **Secrets**: AWS Secrets Manager or Hashicorp Vault.
* **Monitoring**: Prometheus + Grafana; Scrapy logs shipped to Loki.

## 11  Security & Compliance

* Respect robots.txt, throttle requests.
* Store only non‑PII product data.
* HTTPS everywhere; TLS 1.2+.

## 12  Roadmap

1. User profile table → personalised ranks.
2. Vector similarity search via pgvector for ingredient “dupes”.
3. Coupon/discount ingestion.
4. Real‑time price check endpoint per product.

---
