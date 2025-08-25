import scrapy

class LutronScraperItem(scrapy.Item):
    issue = scrapy.Field()
    solution = scrapy.Field()
    product = scrapy.Field()
    category = scrapy.Field()
    url = scrapy.Field()