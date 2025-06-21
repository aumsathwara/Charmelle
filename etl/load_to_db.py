import sys
from pathlib import Path
import pandas as pd
import json
import re
from slugify import slugify
from datetime import datetime
from bs4 import BeautifulSoup

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from core.models import Product, Offer, PriceHistory, ConditionTag, StagingRawOffer

Session = sessionmaker(bind=engine)

# Simple keyword-based tagger
CONDITION_MAP = {
    "dryness": ["dry", "hydration", "hydrating", "moisture", "moisturizing"],
    "acne": ["acne", "blemish", "pore", "breakout", "clear"],
    "wrinkles": ["wrinkle", "age-defy", "aging", "fine lines", "anti-aging"],
    "redness": ["redness", "sensitive", "calm", "soothing", "gentle"],
    "dullness": ["dullness", "brightening", "radiance", "glow", "luminous"],
}

def get_unsynced_offers(limit):
    """Fetch raw offers that haven't been processed yet."""
    query = "SELECT * FROM staging_raw_offers WHERE etl_sync_ts IS NULL"
    if limit:
        query += f" LIMIT {limit}"
    
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)
    return df

def extract_sephora_data(json_data):
    """Extract data from Sephora's detailed product page JSON."""
    data = {}
    current_sku = json_data.get("currentSku", {})
    
    data['brand'] = json_data.get('brand', {}).get('displayName', '')
    data['name'] = json_data.get('displayName', '')
    data['variant'] = current_sku.get('variantValue', '') or current_sku.get('size', '')
    data['product_type'] = json_data.get('parentCategory', {}).get('displayName', 'uncategorized')
    
    # Ingredients are in a specific component
    ingredients_data = next((c for c in json_data.get("regularChildSkus", [{}])[0].get("customContainer", {}).get("child", {}).get("components", []) if c.get("name") == "Ingredients"), {})
    data['ingredients'] = ingredients_data.get("props", {}).get("ingredients", "")

    data['price'] = current_sku.get('listPrice', '').replace('$', '') if current_sku.get('listPrice') else ''
    data['currency'] = 'USD'
    data['rating'] = json_data.get('rating')
    data['url'] = f"https://www.sephora.com{json_data.get('targetUrl', '')}" if json_data.get('targetUrl') else ''
    data['availability'] = 'in_stock' if current_sku.get('isAppAvailable') else 'out_of_stock'
    
    data['description'] = ' '.join(filter(None, [data['brand'], data['name'], json_data.get('quickLook', {}).get('heading')]))
    return data

def extract_dermstore_data(json_data):
    """Extract data from Dermstore's JSON-LD structure."""
    data = {}
    offer = json_data.get("offers", [{}])[0]
    
    data['name'] = json_data.get('name', '')
    data['brand'] = json_data.get('brand', {}).get('name', '')
    data['variant'] = '' # Not always available
    data['product_type'] = json_data.get('category', 'uncategorized').split('>')[-1].strip()
    data['ingredients'] = json_data.get('description', '') # Ingredients often in description

    data['price'] = offer.get('price')
    data['currency'] = offer.get('priceCurrency', 'USD')
    data['rating'] = json_data.get("aggregateRating", {}).get("ratingValue")
    data['url'] = json_data.get('url')
    data['availability'] = 'in_stock' if offer.get('availability') == 'http://schema.org/InStock' else 'out_of_stock'

    data['description'] = ' '.join(filter(None, [data['name'], data['brand']]))
    return data

def extract_ulta_data(json_data):
    """Extract data from Ulta's __APOLLO_STATE__ structure."""
    data = {}
    data['name'] = json_data.get('name', '')
    data['brand'] = json_data.get('brand', {}).get('name', '')
    
    # Variant can be size or other attributes
    variant = next((attr.get('value') for attr in json_data.get('attributes', []) if attr.get('id') == 'size'), '')
    data['variant'] = variant

    data['product_type'] = next((cat.get('name') for cat in json_data.get('categories', [])), 'uncategorized')
    data['ingredients'] = json_data.get('ingredients', {}).get('value', '')

    data['price'] = json_data.get('pricing', {}).get('listPrice')
    data['currency'] = 'USD'
    data['rating'] = json_data.get('rating')
    data['url'] = f"https://www.ulta.com{json_data.get('url', '')}" if json_data.get('url') else ''
    data['availability'] = 'in_stock' if json_data.get('stock', {}).get('stockLevelStatus') != 'OUT_OF_STOCK' else 'out_of_stock'

    data['description'] = ' '.join(filter(None, [data['brand'], data['name']]))
    return data

def extract_moidaus_data(json_data):
    """Extract data from Moidaus's product JSON and description HTML."""
    data = {}
    data['name'] = json_data.get('title', '')
    data['brand'] = json_data.get('vendor', '')
    data['variant'] = json_data.get('variants', [{}])[0].get('title', '')
    data['product_type'] = json_data.get('type', 'uncategorized')
    
    # Parse ingredients from description HTML
    ingredients = ''
    soup = BeautifulSoup(json_data.get('description_html', ''), 'html.parser')
    # A common pattern is a heading followed by the list
    ingredients_tag = soup.find(['strong', 'b'], string=re.compile(r'Ingredients', re.I))
    if ingredients_tag and ingredients_tag.next_sibling:
        ingredients = ingredients_tag.next_sibling.strip()
    data['ingredients'] = ingredients

    data['price'] = json_data.get('price') / 100.0 if json_data.get('price') else None
    data['currency'] = 'USD'
    data['rating'] = None # Not available
    data['url'] = f"https://moidaus.com{json_data.get('url', '')}" if json_data.get('url') else ''
    data['availability'] = 'in_stock' if json_data.get('available') else 'out_of_stock'

    data['description'] = ' '.join(filter(None, [data['brand'], data['name']]))
    return data

def extract_yesstyle_data(json_data):
    """Extract data from YesStyle's __NEXT_DATA__ structure."""
    data = {}
    data['name'] = json_data.get('name', '')
    data['brand'] = json_data.get('brand', {}).get('name', '')
    
    # Variant can be selected from options
    selected_option = next((opt for opt in json_data.get('options', []) if opt.get('isSelected')), {})
    data['variant'] = selected_option.get('name', '')

    data['product_type'] = json_data.get('category', {}).get('name', 'uncategorized')
    
    # Find ingredients from details sections
    ingredients_section = next((d for d in json_data.get('details', []) if d.get('title', '').lower() == 'ingredients'), {})
    ingredients_html = ingredients_section.get('content', '')
    data['ingredients'] = BeautifulSoup(ingredients_html, 'html.parser').get_text(separator=' ', strip=True)

    price_info = json_data.get('price', {})
    data['price'] = price_info.get('original', {}).get('value') or price_info.get('final', {}).get('value')
    data['currency'] = price_info.get('currency', 'USD')
    data['rating'] = json_data.get('review', {}).get('averageRating')
    data['url'] = f"https://www.yesstyle.com{json_data.get('pdpURL', '')}" if json_data.get('pdpURL') else ''
    data['availability'] = 'in_stock' # Assume in stock

    data['description'] = ' '.join(filter(None, [data['brand'], data['name']]))
    return data

def generate_product_id(row):
    """Generate a canonical product ID from brand, name, and variant."""
    brand = slugify(row.get('brand', ''))
    name = slugify(row.get('name', ''))
    variant = slugify(row.get('variant', ''))
    return f"{brand}__{name}__{variant}"

def clean_rating(rating_str):
    """Convert rating string to float or None."""
    if not rating_str or not str(rating_str).strip():
        return None
    try:
        return float(str(rating_str).strip())
    except (ValueError, TypeError):
        return None

def clean_price(price_str):
    """Extract first price from price string or range."""
    if not price_str or not str(price_str).strip():
        return None
    
    price_str = str(price_str).strip()
    
    # Handle price ranges like "25.00 - 89.00" - take the first price
    if ' - ' in price_str:
        price_str = price_str.split(' - ')[0]
    
    # Remove currency symbols and clean
    price_str = price_str.replace('$', '').strip()
    
    try:
        return float(price_str)
    except (ValueError, TypeError):
        return None

def transform_data(df):
    """Parse JSON, generate IDs, and tag conditions."""
    if df.empty:
        return pd.DataFrame()

    # Parse JSON and extract data based on retailer
    extracted_data = []
    for _, row in df.iterrows():
        try:
            json_data = json.loads(row['json_blob'])
            retailer = row['retailer']
            
            if retailer == 'sephora':
                extracted = extract_sephora_data(json_data)
            elif retailer == 'dermstore':
                extracted = extract_dermstore_data(json_data)
            elif retailer == 'ulta':
                extracted = extract_ulta_data(json_data)
            elif retailer == 'moidaus':
                extracted = extract_moidaus_data(json_data)
            elif retailer == 'yesstyle':
                extracted = extract_yesstyle_data(json_data)
            else:
                continue
            
            # Add original row data
            extracted.update({
                'offer_id': row['offer_id'],
                'retailer': row['retailer'],
                'last_seen_ts': row['last_seen_ts']
            })
            
            extracted_data.append(extracted)
        except Exception as e:
            print(f"Error processing offer {row.get('offer_id', 'unknown')}: {e}")
            continue
    
    if not extracted_data:
        return pd.DataFrame()
    
    # Create DataFrame from extracted data
    df = pd.DataFrame(extracted_data)
    
    # Generate IDs
    df['product_id'] = df.apply(generate_product_id, axis=1)
    
    # Clean rating and price values
    df['rating'] = df['rating'].apply(clean_rating)
    df['price'] = df['price'].apply(clean_price)
    
    # Tag conditions
    df['condition_tags'] = df['description'].apply(tag_conditions)
    
    return df

def tag_conditions(description):
    """Tag a product based on keywords in its description."""
    tags = set()
    if not isinstance(description, str):
        return []
    
    lower_desc = description.lower()
    for condition, keywords in CONDITION_MAP.items():
        if any(re.search(r'\b' + keyword + r'\b', lower_desc) for keyword in keywords):
            tags.add(condition)
    return list(tags)

def load_data(df):
    """Load transformed data into canonical tables."""
    if df.empty:
        print("No new data to load.")
        return

    session = Session()
    try:
        # Upsert Products
        products_df = df[['product_id', 'brand', 'name', 'variant', 'product_type', 'ingredients']].drop_duplicates(subset=['product_id'])
        products_records = products_df.to_dict(orient='records')
        if products_records:
            stmt = insert(Product).values(products_records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['product_id'])
            session.execute(stmt)

        # Upsert Offers
        offers_df = df[['offer_id', 'product_id', 'retailer', 'price', 'currency', 'rating', 'url', 'availability', 'last_seen_ts']]
        offers_records = offers_df.to_dict(orient='records')
        if offers_records:
            stmt = insert(Offer).values(offers_records)
            update_dict = {c.name: c for c in stmt.excluded if c.name not in ['offer_id', 'product_id']}
            stmt = stmt.on_conflict_do_update(index_elements=['offer_id'], set_=update_dict)
            session.execute(stmt)

        # Insert into Price History (if price changed)
        # A more robust implementation would check against the last recorded price
        price_history_df = df[['offer_id', 'last_seen_ts', 'price']].rename(columns={'last_seen_ts': 'ts'})
        price_records = price_history_df.to_dict(orient='records')
        if price_records:
            stmt = insert(PriceHistory).values(price_records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['offer_id', 'ts'])
            session.execute(stmt)
            
        # Insert Condition Tags
        tags_df = df[['product_id', 'condition_tags']].explode('condition_tags').dropna()
        tags_df = tags_df.rename(columns={'condition_tags': 'condition'})
        tags_records = tags_df.to_dict(orient='records')
        if tags_records:
            stmt = insert(ConditionTag).values(tags_records)
            stmt = stmt.on_conflict_do_nothing(index_elements=['product_id', 'condition'])
            session.execute(stmt)

        # Mark raw offers as synced
        session.query(StagingRawOffer).filter(StagingRawOffer.offer_id.in_(df['offer_id'].tolist())).update({"etl_sync_ts": datetime.utcnow()})

        session.commit()
        print(f"Successfully processed and loaded {len(df)} offers.")
    except Exception as e:
        session.rollback()
        print(f"Error during data loading: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ETL process for skincare products.")
    parser.add_argument("--limit", type=int, help="Max staging rows to process.", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't write to DB.")
    args = parser.parse_args()

    print("Starting ETL process...")
    raw_offers_df = get_unsynced_offers(args.limit)
    transformed_df = transform_data(raw_offers_df)
    
    if not args.dry_run:
        load_data(transformed_df)
    else:
        print("Dry run complete. Data transformed:")
        print(transformed_df.head())
    print("ETL process finished.") 