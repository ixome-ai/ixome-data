BOT_NAME = "lutron_scraper"

SPIDER_MODULES = ["lutron_scraper.spiders"]
NEWSPIDER_MODULE = "lutron_scraper.spiders"

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'

ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 3

ITEM_PIPELINES = {
    'lutron_scraper.pipelines.LutronScraperPipeline': 300,
}

FEED_FORMAT = 'jsonlines'
FEED_EXPORT_ENCODING = "utf-8"

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'