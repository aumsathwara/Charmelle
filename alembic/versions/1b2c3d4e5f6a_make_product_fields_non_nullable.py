"""make product fields non-nullable

Revision ID: 1b2c3d4e5f6a
Revises: 9a8d5f6c7e1b
Create Date: 2025-06-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b2c3d4e5f6a'
down_revision = '9a8d5f6c7e1b'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Update existing NULLs to default values to avoid constraint violations
    op.execute("UPDATE products SET variant = '' WHERE variant IS NULL")
    op.execute("UPDATE products SET product_type = 'uncategorized' WHERE product_type IS NULL")
    op.execute("UPDATE products SET ingredients = '' WHERE ingredients IS NULL")

    # Step 2: Alter columns to be NOT NULL
    op.alter_column('products', 'variant', existing_type=sa.TEXT(), nullable=False, server_default='')
    op.alter_column('products', 'product_type', existing_type=sa.TEXT(), nullable=False, server_default='uncategorized')
    op.alter_column('products', 'ingredients', existing_type=sa.TEXT(), nullable=False, server_default='')


def downgrade():
    op.alter_column('products', 'ingredients', existing_type=sa.TEXT(), nullable=True, server_default=None)
    op.alter_column('products', 'product_type', existing_type=sa.TEXT(), nullable=True, server_default=None)
    op.alter_column('products', 'variant', existing_type=sa.TEXT(), nullable=True, server_default=None) 