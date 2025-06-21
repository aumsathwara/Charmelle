import sys
from pathlib import Path
import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
import logging

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.models import StagingRawOffer
from config import DB_URL


class DatabasePipeline:
    def __init__(self):
        self.engine = create_engine(DB_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)

    def process_item(self, item, spider):
        session = self.Session()
        self.logger.info(f"PIPELINE: Processing item {item['offer_id']} for spider {spider.name}.")
        stmt = insert(StagingRawOffer).values(
            offer_id=item['offer_id'],
            retailer=item['retailer'],
            json_blob=item['json_blob'],
            last_seen_ts=item['last_seen_ts']
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['offer_id'],
            set_=dict(
                retailer=stmt.excluded.retailer,
                json_blob=stmt.excluded.json_blob,
                last_seen_ts=stmt.excluded.last_seen_ts
            )
        )
        try:
            session.execute(stmt)
            session.commit()
            self.logger.info(f"PIPELINE: Successfully saved item {item['offer_id']} to the database.")
        except Exception as e:
            self.logger.error(f"PIPELINE: Failed to save item {item['offer_id']}. Error: {e}")
            session.rollback()
        finally:
            session.close()
        return item 