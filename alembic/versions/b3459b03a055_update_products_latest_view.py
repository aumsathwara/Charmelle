"""update products_latest view

Revision ID: b3459b03a055
Revises: fcd7eb91e9b6
Create Date: 2025-06-16 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3459b03a055'
down_revision = 'fcd7eb91e9b6'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing materialized view
    op.execute("DROP MATERIALIZED VIEW products_latest;")
    
    # Create the updated materialized view with aggregated columns
    op.execute("""
    CREATE MATERIALIZED VIEW products_latest AS
    SELECT 
        p.product_id,
        p.brand,
        p.name,
        p.variant,
        p.ingredients,
        MIN(o.price) as min_price,
        MAX(o.price) as max_price,
        AVG(o.price) as avg_price,
        AVG(o.rating) as avg_rating,
        COUNT(o.offer_id) as offer_count,
        MAX(o.last_seen_ts) as last_seen_ts
    FROM products p
    LEFT JOIN offers o ON p.product_id = o.product_id
    GROUP BY p.product_id, p.brand, p.name, p.variant, p.ingredients;
    """)
    
    # Create index for better performance
    op.execute("CREATE INDEX idx_products_latest_min_price ON products_latest(min_price);")
    op.execute("CREATE INDEX idx_products_latest_avg_rating ON products_latest(avg_rating);")


def downgrade():
    # Drop the updated view and indexes
    op.execute("DROP INDEX idx_products_latest_min_price;")
    op.execute("DROP INDEX idx_products_latest_avg_rating;")
    op.execute("DROP MATERIALIZED VIEW products_latest;")
    
    # Recreate the original view
    op.execute("""
    CREATE MATERIALIZED VIEW products_latest AS
    SELECT DISTINCT ON (o.product_id) o.*, p.brand, p.name, p.variant
    FROM offers o JOIN products p USING(product_id)
    ORDER BY o.product_id, o.last_seen_ts DESC;
    """) 