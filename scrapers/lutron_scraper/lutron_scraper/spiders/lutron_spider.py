# /home/vincent/ixome/ixome-data/scrapers/lutron_scraper/lutron_scraper/spiders/lutron_homeworks_spider.py
import scrapy
from scrapy_playwright.page import PageMethod
import logging
from urllib.parse import urljoin
from scrapy.exceptions import NotSupported
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

class LutronHomeworksSpider(scrapy.Spider):
    name = 'lutron_homeworks'
    custom_settings = {
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 120000,
        'ITEM_PIPELINES': {'lutron_scraper.pipelines.LutronScraperPipeline': 300},  # Assume pipelines.py exists; process to JSON
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'RETRY_TIMES': 5,
        'DOWNLOAD_FAIL_ON_DATALOSS': False,
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': False,  # Set True for prod
            'args': ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-web-security', '--ignore-certificate-errors'],
        },
    }

    start_urls = ['https://support.lutron.com/us/en/search?q=homeworks&scope=all']

    def start_requests(self):
        for url in self.start_urls:
            logger.info(f"Initiating request for Lutron search: {url}")
            yield scrapy.Request(
                url=url,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'networkidle', timeout=120000),
                        PageMethod('wait_for_selector', '.coh-search-result, div.search-result, article.result', state='visible', timeout=60000),  # Wait for results (Salesforce-like)
                        PageMethod('wait_for_function', 'document.querySelector(".coh-search-result") !== null', timeout=60000),
                        PageMethod('evaluate', '''() => {
                            // Accept cookies if present
                            const acceptBtn = document.querySelector('#onetrust-accept-btn-handler');
                            if (acceptBtn) acceptBtn.click();
                            // Scroll to load more if infinite
                            window.scrollTo(0, document.body.scrollHeight);
                        }'''),
                        PageMethod('wait_for_timeout', 3000),
                    ]
                },
                callback=self.parse_search,
                dont_filter=True,
                errback=self.handle_error
            )

    def parse_search(self, response):
        logger.info(f"Parsing search page: {response.url}, status: {response.status}")
        if isinstance(response, NotSupported):
            logger.warning("Non-text response; converting to HTML")
            response = HtmlResponse(url=response.url, body=response.body, encoding='utf-8')
        items_found = False
        # Extract results (adapt from Lutron old: .coh-search-result or standard)
        for result in response.css('.coh-search-result, div.search-result, article.result, li.result-item'):
            items_found = True
            title = result.css('h3.title::text, a.title::text, h2::text, .search-title::text').get(default='').strip()
            description = ' '.join(result.css('p.description::text, .snippet::text, div.summary p::text').getall()).strip()
            url = result.css('a::attr(href)').get()
            pdf_link = result.css('a[href$=".pdf"]::attr(href)').get()
            if url:
                full_url = urljoin(response.url, url)
                category = 'HomeWorks'  # Fixed for search
                yield {
                    'url': full_url,
                    'title': title or 'HomeWorks Result',
                    'description': description[:500],  # Truncate for JSON
                    'product': title.split()[0] if title else 'unknown',  # e.g., "HomeWorks QS"
                    'category': category,
                    'issue': title,  # Title as issue
                    'solution': description,  # Description as solution
                    'pdf_url': urljoin(response.url, pdf_link) if pdf_link else None,
                    'depth': response.meta.get('depth', 0)
                }
                logger.info(f"Yielded item: {title[:50]}... from {full_url}")
        if not items_found:
            logger.warning(f"No results on {response.url}; check selectors")
        # Pagination (next button or page links)
        next_page = response.css('a.pagination-next::attr(href), .next-page::attr(href), a:contains("Next")::attr(href)').get()
        if next_page:
            logger.info(f"Found next page: {next_page}")
            yield scrapy.Request(
                url=urljoin(response.url, next_page),
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'networkidle', timeout=60000),
                        PageMethod('wait_for_selector', '.coh-search-result', state='visible', timeout=60000),
                    ]
                },
                callback=self.parse_search,
                dont_filter=True,
                errback=self.handle_error
            )

    def handle_error(self, failure):
        logger.error(f"Request failed: {failure.request.url}, Error: {failure.value}")