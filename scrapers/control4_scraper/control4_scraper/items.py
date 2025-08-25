# /home/vincent/ixome/scrapy-selenium/control4_scraper/control4_scraper/items.py
# Control4 scraper item, added 'depth' field to fix KeyError.
from scrapy.item import Item, Field

class Control4ScraperItem(Item):
    issue = Field()
    solution = Field()
    product = Field()
    category = Field()
    url = Field()
    depth = Field()  # Added to support 'depth' field in parse_item