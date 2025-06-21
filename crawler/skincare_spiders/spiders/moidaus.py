import scrapy
from ..items import RawOfferItem
import json
from datetime import datetime

class MoidausSpider(scrapy.Spider):
    name = 'moidaus'
    retailer = 'moidaus'
    
    def start_requests(self):
        url = 'https://moidaus.com/collections/skin-care'
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        product_links = response.css('div.product-item a::attr(href)').getall()
        if not product_links:
            product_links = response.css('.product-item a::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[href*="/products/"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('.product a::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[class*="product"]::attr(href)').getall()
            
        self.logger.info(f"Found {len(product_links)} product links on {response.url}")
        
        # Debug logging
        self.logger.info(f"Page content length: {len(response.text)} characters")
        if response.css('a::attr(href)').getall():
            sample_links = response.css('a::attr(href)').getall()[:10]
            self.logger.info(f"Sample links found: {sample_links}")
            
        for link in set(product_links[:20]):  # Limit to 20 products for testing
            yield response.follow(link, self.parse_product)
        
        # Skip pagination for now to keep it simple
        # next_page = response.css('a[rel="next"]::attr(href)').get()
        # if next_page:
        #     yield response.follow(next_page, self.parse)

    def parse_product(self, response):
        self.logger.info(f"Parsing product page: {response.url}")
        
        script_json = response.css('script[type="application/json"][id*="ProductJson"]::text').get()
        if not script_json:
            self.logger.error(f"Could not find product JSON on {response.url}")
            return
            
        try:
            product_data = json.loads(script_json)
            
            product_id = product_data.get('id')
            if not product_id:
                self.logger.error(f"Could not find product ID in JSON on {response.url}")
                return

            product_data['retailer'] = self.retailer
            product_data['product_type'] = product_data.get('type')
            
            # Add the full description HTML for ingredient parsing later
            product_data['description_html'] = response.css('div.product-description').get()

            item = RawOfferItem()
            item['retailer'] = self.retailer
            item['offer_id'] = f"{self.retailer}-{product_id}"
            item['json_blob'] = json.dumps(product_data)
            item['last_seen_ts'] = datetime.now().isoformat()
            
            yield item
            
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse product JSON on {response.url}") 