from core.database import engine
from sqlalchemy import text

# Update existing records with retailer info extracted from offer_id
with engine.connect() as conn:
    result = conn.execute(text("""
        UPDATE staging_raw_offers 
        SET retailer = CASE 
            WHEN offer_id LIKE 'sephora-%' THEN 'sephora'
            WHEN offer_id LIKE 'dermstore-%' THEN 'dermstore'
            WHEN offer_id LIKE 'ulta-%' THEN 'ulta'
            ELSE 'unknown'
        END
        WHERE retailer IS NULL
    """))
    conn.commit()
    print(f'Updated retailer information for {result.rowcount} records') 