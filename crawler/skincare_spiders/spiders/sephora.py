import scrapy
import json
from datetime import datetime
from ..items import RawOfferItem

class SephoraSpider(scrapy.Spider):
    name = 'sephora'
    retailer = 'sephora'
    
    def start_requests(self):
        url = 'https://www.sephora.com/shop/moisturizing-cream-oils-mists'
        yield scrapy.Request(url, callback=self.parse_list)

    def parse_list(self, response):
        """Extract product links from the category page."""
        self.logger.info(f"Parsing category page: {response.url}")
        
        # Try multiple selectors to find product links
        product_links = response.css('a[data-comp-name="ProductItem"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[href*="/product/"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('.product-tile a::attr(href)').getall()
            
        self.logger.info(f"Found {len(product_links)} product links on {response.url}")

        for link in set(product_links[:20]):  # Limit to 20 products for testing
            if link.startswith('/'):
                link = response.urljoin(link)
            yield scrapy.Request(link, callback=self.parse_product)

    def parse_product(self, response):
        """Extracts detailed product data from an embedded script tag on the product page."""
        self.logger.info(f"Parsing product page: {response.url}")
        
        script_data = response.css('script[type="application/ld+json"][data-comp="PageJSON"]::text').get()
        if not script_data:
            self.logger.error(f"Could not find PageJSON data on {response.url}")
            return
            
        try:
            product_json = json.loads(script_data)
            
            # The actual product data is nested inside this JSON
            props = product_json.get("props", {})
            page_props = props.get("pageProps", {})
            product_data = page_props.get("product", {})
            sku = product_data.get("currentSku", {}).get("skuId")

            if not sku:
                self.logger.error(f"Could not find SKU in PageJSON on {response.url}")
                return

            item = RawOfferItem()
            item['retailer'] = self.retailer
            item['offer_id'] = f"{self.retailer}-{sku}"
            item['json_blob'] = json.dumps(product_data) # Store the detailed product data
            item['last_seen_ts'] = datetime.now().isoformat()
            
            yield item
            
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse PageJSON on {response.url}")

 