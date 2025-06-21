"""add etl_sync_ts to staging

Revision ID: d78cb5129604
Revises: 2f8f04b2215c
Create Date: 2024-06-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd78cb5129604'
down_revision = '2f8f04b2215c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('staging_raw_offers', sa.Column('etl_sync_ts', sa.TIMESTAMP(), nullable=True))


def downgrade():
    op.drop_column('staging_raw_offers', 'etl_sync_ts') 