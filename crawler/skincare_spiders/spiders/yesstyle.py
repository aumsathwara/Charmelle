import scrapy
from ..items import RawOfferItem
import json
from datetime import datetime
import re

class YesstyleSpider(scrapy.Spider):
    name = 'yesstyle'
    retailer = 'yesstyle'
    base_url = 'https://www.yesstyle.com/en/beauty-skin-care/list.html/bcc.15544_bpt.46'
    
    def start_requests(self):
        yield scrapy.Request(self.base_url, callback=self.parse_list)

    def parse_list(self, response):
        """Parses the list page to get product URLs."""
        self.logger.info(f"Parsing list page: {response.url}")
        
        product_links = response.css('div.item-module a[href*="/en/p/"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[href*="/en/p/"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[href*="/p/"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('.item a::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[class*="item"]::attr(href)').getall()
            
        self.logger.info(f"Found {len(product_links)} product links on list page.")
        
        # Debug logging
        self.logger.info(f"Page content length: {len(response.text)} characters")
        if response.css('a::attr(href)').getall():
            sample_links = response.css('a::attr(href)').getall()[:10]
            self.logger.info(f"Sample links found: {sample_links}")

        for pdp_url in set(product_links[:20]):  # Limit to 20 products for testing
            yield response.follow(pdp_url, self.parse_product)
        
        # Skip pagination for now to keep it simple
        # current_page_match = re.search(r'pn=(\d+)', response.url)
        # current_page = int(current_page_match.group(1)) if current_page_match else 1
        # 
        # if current_page < 3: # Limit pages to avoid excessive scraping
        #     next_page = current_page + 1
        #     next_url = f"{self.base_url}?pn={next_page}"
        #     yield response.follow(next_url, self.parse_list)

    def parse_product(self, response):
        """Parses the product detail page for full product data."""
        self.logger.info(f"Parsing product page: {response.url}")
        
        script_data = response.css('script[id="__NEXT_DATA__"]::text').get()
        if not script_data:
            self.logger.error(f"Could not find __NEXT_DATA__ on product page {response.url}")
            return

        try:
            data = json.loads(script_data)
            product_data = data.get('props', {}).get('pageProps', {}).get('product', {})
            product_id = product_data.get('id')
            
            if not product_id:
                self.logger.error(f"Could not find product ID in __NEXT_DATA__ on {response.url}")
                return

            item = RawOfferItem()
            item['retailer'] = self.retailer
            item['offer_id'] = f"{self.retailer}-{product_id}"
            item['json_blob'] = json.dumps(product_data)
            item['last_seen_ts'] = datetime.now().isoformat()
            yield item

        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse __NEXT_DATA__ JSON on product page {response.url}") 