import scrapy
import json
import re
from datetime import datetime
from ..items import RawOfferItem

class UltaSpider(scrapy.Spider):
    name = 'ulta'
    retailer = 'ulta'

    def start_requests(self):
        url = 'https://www.ulta.com/shop/skin-care'
        yield scrapy.Request(url, callback=self.parse_list)

    def parse_list(self, response):
        """Extracts product links from the listing page."""
        product_links = response.css("div[class*='ProductCard'] a::attr(href)").getall()
        if not product_links:
            product_links = response.css("a[href*='/product/']::attr(href)").getall()
        if not product_links:
            product_links = response.css("a[class*='product']::attr(href)").getall()
        if not product_links:
            product_links = response.css("a[href*='/p/']::attr(href)").getall()
        if not product_links:
            product_links = response.css("a[data-testid*='product']::attr(href)").getall()
            
        self.logger.info(f"Found {len(product_links)} product links on {response.url}")
        
        # Debug logging
        self.logger.info(f"Page content length: {len(response.text)} characters")
        if response.css('a::attr(href)').getall():
            sample_links = response.css('a::attr(href)').getall()[:10]
            self.logger.info(f"Sample links found: {sample_links}")

        for link in set(product_links[:20]):  # Limit to 20 products for testing
            yield response.follow(link, self.parse_product)

    def parse_product(self, response):
        """Extracts __APOLLO_STATE__ from the product detail page."""
        self.logger.info(f"Parsing product page: {response.url}")
        
        script_content = response.xpath("//script[contains(., 'window.__APOLLO_STATE__')]/text()").get()
        if not script_content:
            self.logger.error(f"Could not find __APOLLO_STATE__ script on {response.url}")
            return
        
        match = re.search(r'window\.__APOLLO_STATE__\s*=\s*(\{.*\})', script_content)
        if not match:
            self.logger.error(f"Could not extract __APOOLLO_STATE__ JSON from script on {response.url}")
            return
            
        try:
            apollo_state = json.loads(match.group(1))
            
            # Find the main product entry in the Apollo state
            product_key = next((key for key in apollo_state if key.startswith('Product:')), None)
            if not product_key:
                self.logger.error(f"Could not find Product key in Apollo State on {response.url}")
                return

            product_data = apollo_state[product_key]
            product_id = product_data.get('id')
            
            if not product_id:
                 self.logger.error(f"Could not find product ID in Apollo State on {response.url}")
                 return

            item = RawOfferItem()
            item['retailer'] = self.retailer
            item['offer_id'] = f"{self.retailer}-{product_id}"
            item['json_blob'] = json.dumps(product_data)
            item['last_seen_ts'] = datetime.now().isoformat()
            
            yield item
            
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse __APOLLO_STATE__ JSON on {response.url}") 