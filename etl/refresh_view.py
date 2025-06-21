import sys
from pathlib import Path
from sqlalchemy import text

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import engine

def refresh_view():
    """Refreshes the materialized view for the API."""
    print("Refreshing materialized view: products_latest...")
    with engine.connect() as connection:
        try:
            # The CONCURRENTLY option requires a unique index on the view.
            # For local use, a standard refresh is acceptable, though it will
            # lock the view during the refresh.
            connection.execute(text("REFRESH MATERIALIZED VIEW products_latest;"))
            connection.commit()
            print("Successfully refreshed the view.")
        except Exception as e:
            print(f"Error refreshing view: {e}")
            connection.rollback()

if __name__ == "__main__":
    refresh_view() 