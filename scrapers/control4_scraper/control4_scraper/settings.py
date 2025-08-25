# /home/vincent/ixome/scrapy-selenium/control4_scraper/control4_scraper/settings.py
BOT_NAME = 'control4_scraper'

SPIDER_MODULES = ['control4_scraper.spiders']
NEWSPIDER_MODULE = 'control4_scraper.spiders'

ROBOTSTXT_OBEY = True

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'

DOWNLOAD_DELAY = 5.0
DEPTH_LIMIT = 5
CONCURRENT_REQUESTS = 16

ITEM_PIPELINES = {
    'control4_scraper.pipelines.Control4ScraperPipeline': 300,
}

DOWNLOADER_MIDDLEWARES = {
    'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler': 1000,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
}

# Playwright settings
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000
PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': True,
    'args': ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-gpu']
}
PLAYWRIGHT_CONTEXT_ARGS = {
    'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'bypass_csp': True
}

DOWNLOAD_HANDLERS = {
    'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
    'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
}

TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'

LOG_LEVEL = 'DEBUG'  # Increased to DEBUG for more detail
LOG_FILE = '/home/vincent/ixome/scrapy-selenium/control4_scraper/control4_scraper/scrapy.log'  # Absolute path