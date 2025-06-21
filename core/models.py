from sqlalchemy import (
    Column,
    String,
    Text,
    TIMESTAMP,
    Numeric,
    CHAR,
    ForeignKey,
    PrimaryKeyConstraint,
    Integer,
    func
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    product_id = Column(Text, primary_key=True)
    brand = Column(Text)
    name = Column(Text)
    variant = Column(Text, nullable=False, server_default='')
    product_type = Column(Text, nullable=False, server_default='uncategorized')
    ingredients = Column(Text, nullable=False, server_default='')
    created_ts = Column(TIMESTAMP, server_default=func.now())

class Offer(Base):
    __tablename__ = 'offers'
    offer_id = Column(Text, primary_key=True)
    product_id = Column(Text, ForeignKey('products.product_id'))
    retailer = Column(Text)
    price = Column(Numeric(10, 2))
    currency = Column(CHAR(3))
    rating = Column(Numeric(2, 1))
    url = Column(Text)
    availability = Column(Text)
    last_seen_ts = Column(TIMESTAMP)
    etl_sync_ts = Column(TIMESTAMP)

class PriceHistory(Base):
    __tablename__ = 'price_history'
    offer_id = Column(Text, ForeignKey('offers.offer_id'))
    ts = Column(TIMESTAMP)
    price = Column(Numeric(10, 2))
    __table_args__ = (PrimaryKeyConstraint('offer_id', 'ts'),)

class ConditionTag(Base):
    __tablename__ = 'condition_tags'
    product_id = Column(Text, ForeignKey('products.product_id'))
    condition = Column(Text)
    __table_args__ = (PrimaryKeyConstraint('product_id', 'condition'),)

class DetectionLog(Base):
    __tablename__ = 'detection_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    condition = Column(Text)
    area = Column(Text)
    ts = Column(TIMESTAMP, server_default=func.now())

class StagingRawOffer(Base):
    __tablename__ = 'staging_raw_offers'
    offer_id = Column(Text, primary_key=True)
    retailer = Column(Text)
    json_blob = Column(Text) # Using Text for simplicity, can be JSONB in postgres
    last_seen_ts = Column(TIMESTAMP, server_default=func.now())
    etl_sync_ts = Column(TIMESTAMP, nullable=True) 