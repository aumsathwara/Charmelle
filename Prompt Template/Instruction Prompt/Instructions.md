# Skincare Recommendation Platform – *Local‑First* Implementation Instructions

> **Audience:** Backend engineers who want to stand everything up **directly on a laptop/VM**, no Docker/Kubernetes yet.
>
> **Goal:** Crawl retailers, refresh the catalogue, and serve `/recommend` queries—all with local PostgreSQL and Python processes.

---

## 0  Prerequisites

| Item                     | Version     | Notes                                                                                        |
| ------------------------ | ----------- | -------------------------------------------------------------------------------------------- |
| **Python**               | 3.10 – 3.12 | Use `pyenv`, `conda`, or system package manager.                                             |
| **PostgreSQL**           | ≥ 14        | Install locally (brew/apt/winget). Ensure `psql` is on PATH.                                 |
| **Node.js / Playwright** | Node ≥ 18   | Needed for Playwright‑driven crawlers. `playwright install chromium` will fetch the browser. |
| **Git**                  | latest      | Clone the repo.                                                                              |
| **(Optional) Make**      | 4.x         | For shorthand scripts.                                                                       |

---

## 1  Repository Bootstrap

```bash
# 1.1  Clone and enter repo
git clone https://github.com/your-org/skincare-recommender.git
cd skincare-recommender

# 1.2  Create virtual env
python -m venv .venv
source .venv/bin/activate

# 1.3  Install dependencies
pip install -r requirements.txt

# 1.4  Install Playwright browsers
playwright install chromium
```

**requirements.txt (excerpt)**

```
fastapi==0.111.*
uvicorn[standard]==0.29.*
scrapy==2.11.*
scrapy-playwright==0.0.31
playwright==1.44.*
SQLAlchemy==2.0.*
psycopg2-binary
alembic
pandas
orjson
apscheduler
pytest
```

---

## 2  Database Setup (Local PostgreSQL)

1. **Start/enable PostgreSQL service**

   * **macOS (Homebrew):** `brew services start postgresql@14`
   * **Ubuntu/Debian:** `sudo apt install postgresql-14`  → `sudo systemctl start postgresql`
   * **Windows (winget):** `winget install PostgreSQL` and launch from Services.

2. **Create user & database**

   ```bash
   # enter psql as superuser (often 'postgres')
   sudo -u postgres psql

   -- inside psql
   CREATE USER skin WITH PASSWORD 'skin' LOGIN;
   CREATE DATABASE skincare OWNER skin ENCODING 'UTF8';
   \q
   ```

3. **Environment file**
   Create `.env` in repo root:

   ```ini
   DB_URL=postgresql+psycopg2://skin:skin@localhost:5432/skincare
   SECRET_KEY=change_me
   ```

4. **Run Alembic migrations**

   ```bash
   alembic upgrade head
   ```

   This creates all tables and the `products_latest` materialised view.

---

## 3  Crawling Layer

### 3.1  Folder Layout

```
crawler/
 └─ skincare_spiders/
    ├─ sephora.py
    ├─ ulta.py
    ├─ dermstore.py
    ├─ items.py
    ├─ pipelines.py
    └─ settings.py
```

### 3.2  Run a delta crawl (single retailer)

```bash
cd crawler
scrapy crawl sephora -a delta=true -s LOG_LEVEL=INFO
```

* Items land in `staging_raw_offers` with `last_seen_ts`.
* Repeat for `ulta` and `dermstore`.

---

## 4  ETL & Normaliser

### 4.1  Run ETL locally

```bash
python etl/load_to_db.py --limit 5000
```

| Flag        | Description                             | Default   |
| ----------- | --------------------------------------- | --------- |
| `--limit`   | Max staging rows to process in this run | unlimited |
| `--dry-run` | Parse only, don’t write                 | `False`   |

### 4.2  Verify Inserts

```sql
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM offers;
SELECT * FROM products LIMIT 5;  -- sanity
```

---

## 5  Materialised View Refresh

```bash
python etl/refresh_view.py   # wrapper around REFRESH MATERIALIZED VIEW CONCURRENTLY products_latest;
```

Run this after ETL or periodically to keep the API snappy.

---

## 6  API Service

### 6.1  Dev server with hot‑reload

```bash
uvicorn api.server:app --reload --port 8000
```

### 6.2  Health check

```bash
curl http://localhost:8000/healthz
# → {"status": "ok"}
```

### 6.3  Example query

```bash
curl "http://localhost:8000/recommend?condition=dryness&sort=relevance&top=5"
```

Returns an array of product JSON objects.

---

## 7  Job Scheduling (APScheduler example)

Create **`scheduler.py`** in repo root:

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
sched = BlockingScheduler(timezone="UTC")

@sched.scheduled_job("cron", hour="*/3")
def delta_crawl():
    for spider in ("sephora", "ulta", "dermstore"):
        subprocess.run(["scrapy", "crawl", spider, "-a", "delta=true"], cwd=BASE/"crawler")

@sched.scheduled_job("cron", hour="*", minute=10)
def run_etl():
    subprocess.run(["python", "etl/load_to_db.py"], cwd=BASE)
    subprocess.run(["python", "etl/refresh_view.py"], cwd=BASE)

if __name__ == "__main__":
    sched.start()
```

Start it (preferably inside `tmux` or `nohup`):

```bash
python scheduler.py
```

---

## 8  Tests

```bash
pytest -q
```

* `tests/test_recommender.py` ensures relevance order.
* `tests/test_spider_outputs.py` validates spider item completeness.

---

## 9  Monitoring & Alerts (Local‑Friendly)

1. **Prometheus** – run `prom/prometheus` Docker *only* for Prometheus, or use `brew install prometheus`; scrape `http://localhost:8000/metrics`.
2. **Grafana** – optional; point at Prometheus to view dashboards.
3. **Simple alert** – Bash script + cron that checks `SELECT max(last_seen_ts)` and sends an email if stale > 4h.

---

## 10  Common Troubleshooting

| Symptom                     | Likely Cause                              | Fix                                            |
| --------------------------- | ----------------------------------------- | ---------------------------------------------- |
| `psycopg2.OperationalError` | Wrong credentials or Postgres not started | Check `DB_URL`, run `pg_isready`.              |
| API empty list              | `condition_tags` not populated            | Update regex map or ensure Tagger runs.        |
| 429 / 403 errors in crawl   | Site rate‑limits                          | Increase delay, change IP, respect robots.txt. |
| `REFRESH` long lock         | Forgot `CONCURRENTLY` keyword             | Use supplied script or add `CONCURRENTLY`.     |

---

## 11  Next Steps

* Add user profile & personalisation tables.
* Introduce Redis caching for hot queries.
* Instrument Playwright spiders with screenshot logs.
* When ready for cloud, containerise or use `poetry export` & deploy to EC2.

*Happy coding—locally!*
