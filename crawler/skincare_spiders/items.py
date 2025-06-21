import scrapy

class RawOfferItem(scrapy.Item):
    # The unique identifier for the offer, e.g., 'sephora-12345-light'
    offer_id = scrapy.Field()
    # The raw JSON blob of scraped product data
    json_blob = scrapy.Field()
    # Timestamp of when the item was last seen
    last_seen_ts = scrapy.Field()
    # The retailer name (sephora, ulta, dermstore)
    retailer = scrapy.Field() 