import scrapy
from ..items import RawOfferItem
import json
from datetime import datetime

class DermstoreSpider(scrapy.Spider):
    name = 'dermstore'
    retailer = 'dermstore'
    start_urls = ['https://www.dermstore.com/c/skin-care/']
    
    def parse(self, response):
        """Parse the category page to extract product links."""
        self.logger.info(f"Parsing category page: {response.url}")
        
        # Extract product links using multiple selectors to be safe
        product_links = response.css('a[data-testid="product-card-link"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('.product-card a::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[href*="/product/"]::attr(href)').getall()
        if not product_links:
            # Try more generic selectors
            product_links = response.css('a[href*="/skincare"]::attr(href)').getall()
        if not product_links:
            product_links = response.css('a[class*="product"]::attr(href)').getall()
        if not product_links:
            # Very broad search for any product-like links
            product_links = response.css('a[href*="/p/"]::attr(href)').getall()
            
        self.logger.info(f"Found {len(product_links)} product links on category page.")
        
        # Debug: Print the page content length and some sample links
        self.logger.info(f"Page content length: {len(response.text)} characters")
        if response.css('a::attr(href)').getall():
            sample_links = response.css('a::attr(href)').getall()[:10]
            self.logger.info(f"Sample links found: {sample_links}")

        # Process product links
        for link in set(product_links[:20]):  # Limit to 20 products for testing
            if link.startswith('/'):
                link = response.urljoin(link)
            yield response.follow(link, self.parse_product)

    def parse_product(self, response):
        """Parse individual product pages for detailed data."""
        self.logger.info(f"Parsing product page: {response.url}")
        
        # Try to extract structured data from JSON-LD
        json_ld_scripts = response.css('script[type="application/ld+json"]::text').getall()
        product_data = {}
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    product_data = data
                    break
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            product_data = item
                            break
            except json.JSONDecodeError:
                continue
        
        # If no JSON-LD, extract from page elements
        if not product_data:
            product_data = {
                'name': response.css('h1[data-testid="product-title"]::text').get() or 
                        response.css('h1.product-title::text').get() or
                        response.css('h1::text').get(),
                'brand': response.css('[data-testid="product-brand"]::text').get() or
                         response.css('.product-brand::text').get(),
                'description': response.css('[data-testid="product-description"]::text').get() or
                              response.css('.product-description::text').get(),
                'price': response.css('[data-testid="product-price"]::text').get() or
                         response.css('.price::text').get(),
                'url': response.url
            }
            
            # Extract ingredients if available
            ingredients_text = response.css('[data-testid="ingredients"], .ingredients, [class*="ingredient"]::text').getall()
            if ingredients_text:
                product_data['ingredients'] = ' '.join(ingredients_text).strip()
        
        # Create item
        item = RawOfferItem()
        item['retailer'] = self.retailer
        item['offer_id'] = f"{self.retailer}-{response.url.split('/')[-1]}"
        item['json_blob'] = json.dumps(product_data)
        item['last_seen_ts'] = datetime.now().isoformat()
        
        yield item 