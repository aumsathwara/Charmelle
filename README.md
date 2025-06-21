# Skincare Recommendation Platform - Local Setup Guide

This guide provides step-by-step instructions to set up and run the AI-Powered Skincare Recommendation Platform on your local machine.

---

## 0. Prerequisites

Before you begin, ensure you have the following installed:
- **Python (3.10 – 3.12)**
- **PostgreSQL (≥ 14)**
- **Node.js (≥ 18)** (for Playwright)
- **Git**

---

## 1. Repository Bootstrap

First, set up the Python environment and install the necessary dependencies.

```bash
# 1.1 Create a virtual environment
python -m venv .venv

# 1.2 Activate the virtual environment
# On Windows:
# .\\.venv\\Scripts\\activate
# On macOS/Linux:
# source .venv/bin/activate

# 1.3 Install Python dependencies
pip install -r requirements.txt

# 1.4 Install Playwright browsers
playwright install chromium
```

---

## 2. Database Setup

This project uses a local PostgreSQL database.

**2.1. Start PostgreSQL Service**

Ensure your local PostgreSQL service is running. The method varies by OS:
- **macOS (Homebrew):** `brew services start postgresql@14`
- **Ubuntu/Debian:** `sudo systemctl start postgresql`
- **Windows:** Use the Services application to start the PostgreSQL service.

**2.2. Create User and Database**

You need to create a dedicated database and user for the application. You can do this either via the command line or a graphical tool like pgAdmin.

---
#### **Option A: Using the Command Line (`psql`)**

Connect to PostgreSQL as the superuser (the default is `postgres`).

*   **On Windows:**
    ```powershell
    # If psql is in your PATH, run this command:
    psql -U postgres
    ```
    > **Note:** If you don't remember the password for the `postgres` user, please use Option B (pgAdmin) below or reset the password.

*   **On macOS/Linux:**
    ```bash
    sudo -u postgres psql
    ```

Once you are inside the `psql` shell, run these commands to create the user and database:

```sql
-- inside psql
CREATE USER skin WITH PASSWORD 'skin' LOGIN;
CREATE DATABASE skincare OWNER skin ENCODING 'UTF8';
\q
```

---
#### **Option B: Using pgAdmin**

If you prefer a graphical interface, follow these steps in pgAdmin:

1.  **Connect to your Server:** Open pgAdmin and connect to your PostgreSQL server.
2.  **Create a Login Role:**
    *   In the tree view on the left, right-click on **Login/Group Roles**.
    *   Select **Create** > **Login/Group Role...**.
    *   In the **General** tab, enter `skin` for the **Name**.
    *   Go to the **Definition** tab and enter `skin` for the **Password**.
    *   Go to the **Privileges** tab and make sure **Can login?** is set to `Yes`.
    *   Click **Save**.
3.  **Create a Database:**
    *   Right-click on **Databases**.
    *   Select **Create** > **Database...**.
    *   In the **General** tab, enter `skincare` for the **Database** name.
    *   Set the **Owner** to the `skin` user you just created.
    *   Click **Save**.

You have now created the required user and database and can proceed to the next step.
---

**2.3. Environment Configuration**

The application is configured via a `.env` file. We use a `config.py` as a fallback. For this setup, no `.env` is needed if you used the credentials above.

**2.4. Run Database Migrations**

Apply the database schema to your newly created database using Alembic.

```bash
alembic upgrade head
```

This command creates all necessary tables and the `products_latest` materialized view.

---

## 3. Run the Data Pipeline

Now, populate your database with the sample product data.

**3.1. Run Crawlers**

The spiders generate dummy data and save it to the `staging_raw_offers` table.

```bash
# Navigate to the crawler directory
cd crawler

# Run each spider
scrapy crawl sephora
scrapy crawl ulta
scrapy crawl dermstore

# Return to the project root
cd ..
```

**3.2. Run ETL Process**

The ETL script processes the raw data from the staging table, normalizes it, and loads it into the final product and offer tables.

```bash
python etl/load_to_db.py
```

**3.3. Refresh the Materialized View**

Update the `products_latest` view so the API can serve the new data.

```bash
python etl/refresh_view.py
```

---

## 4. Run the API Service

With the database populated, you can now start the recommendation API.

**4.1. Start the Development Server**

Use `uvicorn` to run the FastAPI application. The `--reload` flag enables hot-reloading.

```bash
uvicorn api.server:app --reload --port 8000
```

**4.2. Test the API**

You can now send requests to the API.

**Health Check:**
```bash
curl http://localhost:8000/healthz
# Expected output: {"status":"ok"}
```

**Example Recommendation Query:**
```bash
curl "http://localhost:8000/recommend?condition=dryness&sort=price_low&top=5"
```
This should return a JSON array of products recommended for "dryness", sorted by the lowest price.

---

## 5. Run Tests

To ensure all components are working as expected, run the automated tests.

```bash
pytest -q
```

This will execute the tests in the `tests/` directory.

---

## (Optional) 6. Run the Scheduler

The `scheduler.py` script automates the crawling and ETL jobs. You can run it in a separate terminal to keep your data fresh.

```bash
python scheduler.py
```

This will run all jobs once on startup and then follow the cron schedule defined in the script. 