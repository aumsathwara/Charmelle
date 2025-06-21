"""add product_type to products

Revision ID: 9a8d5f6c7e1b
Revises: b3459b03a055
Create Date: 2025-06-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a8d5f6c7e1b'
down_revision = 'b3459b03a055'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('product_type', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('products', 'product_type') 