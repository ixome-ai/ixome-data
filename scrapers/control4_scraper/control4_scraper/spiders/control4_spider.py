# /home/vincent/ixome/scrapy-selenium/control4_scraper/control4_scraper/spiders/control4_spider.py
import scrapy
from scrapy_playwright.page import PageMethod
import logging
from urllib.parse import urljoin
from scrapy.exceptions import NotSupported
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

class Control4Spider(scrapy.Spider):
    name = 'control4'
    custom_settings = {
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 120000,
        'ITEM_PIPELINES': {'control4_scraper.pipelines.Control4ScraperPipeline': 300},
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
            'https': 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler',
        },
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'RETRY_TIMES': 5,
        'DOWNLOAD_FAIL_ON_DATALOSS': False,
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': False,
            'args': ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-web-security', '--ignore-certificate-errors'],
        },
    }

    start_urls = [
        'https://www.snapav.com/shop/en/snapav/product-files-videos-search'  # Dealer search
    ] + [
        'https://docs.control4.com/docs/product/core-5/data-sheet/english/latest/',
        'https://docs.control4.com/docs/product/ea-5-v2/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/core-3/data-sheet/english/latest/',
        'https://docs.control4.com/docs/product/wireless-keypad-dimmer/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/ea-1/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/door-station/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/io-extender/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/adaptive-phase-dimmer/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/ca-1/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/hc-250/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/hc-800/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/5-in-wall-touch-screen/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/7-in-wall-touch-screen/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/halo-remote/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/sr-260/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/z2io/data-sheet/english/latest/',
        'https://docs.control4.com/docs/product/t4-series-touch-screen/installation-guide/english/latest/',
        'https://docs.control4.com/docs/product/myhome/user-guide/english/latest/',
        'https://docs.control4.com/docs/product/tunein/user-guide/english/latest/',
        'https://docs.control4.com/docs/product/myhome/open-source-request-form/english/latest/',
        'https://docs.control4.com/docs/product/alexa/faq/german/latest/',
        'https://docs.control4.com/docs/product/myhome/setup-guide/english/latest/',
        'https://docs.control4.com/docs/product/networking/checklist/english/latest/',
        'https://docs.control4.com/docs/product/mycontrol4/quick-setup/english/latest/',
        'https://docs.control4.com/docs/product/tunein/quick-setup/english/latest/',
        'https://docs.control4.com/docs/product/customer/brochure/english/latest/',
        'https://docs.control4.com/docs/product/pcna/troubleshooting/english/latest/',
        'https://docs.control4.com/docs/product/tunein/data-sheet/english/latest/',
        'https://docs.control4.com/docs/product/pcna/study-guide/english/latest/',
        'https://docs.control4.com/docs/product/wattbox/best-practices/english/latest/',
        'https://docs.control4.com/docs/product/triad/style-guide/english/latest/',
        'https://docs.control4.com/docs/product/alexa/dealer-faq/english/latest/',
        'https://docs.control4.com/docs/product/whenthen/information-sheet/english/latest/',
        'https://docs.control4.com/docs/product/baldwin-doorlock/brochure/english/latest/',
        'https://docs.control4.com/docs/product/networking/best-practices/english/latest/',
        'https://docs.control4.com/docs/product/z2c/data-sheet/english/latest/',
        'https://docs.control4.com/docs/product/beta-test/agreement/english/latest/'
    ]

    def start_requests(self):
        # Dealer page request (authenticated)
        try:
            logger.info("Initiating dealer request for %s", 'https://www.snapav.com/shop/en/snapav/product-files-videos-search')
            yield scrapy.Request(
                url='https://www.snapav.com/shop/en/snapav/product-files-videos-search',
                meta={
                    'playwright': True,
                    'playwright_context': 'persistent',
                    'playwright_context_kwargs': {
                        'storage_state': '/home/vincent/ixome/scrapy-selenium/control4_scraper/cookies.json',
                        'ignoreHTTPSErrors': True,
                    },
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'networkidle', timeout=120000),
                        PageMethod('wait_for_selector', 'text=Displaying documents & videos', state='visible', timeout=300000),
                        PageMethod('wait_for_selector', 'div#advAccordion', state='visible', timeout=15000),
                        PageMethod('click', 'div#advAccordion', force=True),
                        PageMethod('wait_for_timeout', 2000),
                        PageMethod('evaluate', '''() => {
                            const input = document.querySelector('input#contentSearchTerm');
                            if (input) {
                                input.style.display = 'block';
                                input.style.visibility = 'visible';
                                const parent = input.closest('div, section');
                                if (parent) {
                                    parent.style.display = 'block';
                                    parent.style.visibility = 'visible';
                                }
                            }
                        }'''),
                        PageMethod('wait_for_selector', 'input#contentSearchTerm', state='visible', timeout=90000),
                        PageMethod('type', 'input#contentSearchTerm', value='pdf', delay=100),
                        PageMethod('evaluate', '''() => {
                            const input = document.querySelector('input#contentSearchTerm');
                            if (input) {
                                input.dispatchEvent(new Event("input"));
                                if (typeof ContentSearch !== 'undefined' && ContentSearch.checkChange) {
                                    ContentSearch.checkChange({ target: input });
                                }
                            }
                        }'''),
                        PageMethod('click', 'a#qop-submit', force=True),
                        PageMethod('wait_for_selector', 'text=Displaying documents & videos', state='visible', timeout=30000),
                        PageMethod('wait_for_selector', 'div[id*="searchResults"] a[href*=".pdf"], ul[class*="results"] a[href*=".pdf"], li[class*="result"] a[href*=".pdf"], embed[type="application/pdf"]', state='visible', timeout=300000)
                    ]
                },
                callback=self.parse_dealer,
                dont_filter=True,
                errback=self.handle_error
            )
        except Exception as e:
            logger.error("Failed to initiate dealer request: %s, Traceback: %s", e, str(e))

        # Public URLs
        for url in self.start_urls[1:]:  # Skip dealer URL to avoid duplication
            logger.info("Initiating public request for %s", url)
            yield scrapy.Request(
                url=url,
                meta={'playwright': True, 'playwright_page_methods': [
                    PageMethod('wait_for_load_state', 'networkidle', timeout=120000),
                    PageMethod('wait_for_function', 'document.querySelector("a[href$=\'.pdf\']") !== null', timeout=120000)
                ]},
                callback=self.parse_public,
                errback=self.handle_error
            )

    def parse_dealer(self, response):
        logger.info("Parsing dealer page: %s, status: %s, content snippet: %s", response.url, response.status, response.text[:500] if hasattr(response, 'text') else "No text content")
        if 'LogonForm' in response.url or response.status in [401, 403]:
            logger.error("Authentication failed, redirected to login or access denied for %s", response.url)
            return
        if isinstance(response, NotSupported):
            logger.warning("Skipping non-text response for %s, attempting to extract HTML", response.url)
            response = HtmlResponse(url=response.url, body=response.body, encoding='utf-8')
        items_found = False
        for item in response.css('div[id*="searchResults"] a[href*=".pdf"], ul[class*="results"] a[href*=".pdf"], li[class*="result"] a[href*=".pdf"], embed[type="application/pdf"]'):
            href = item.attrib.get('href') or item.attrib.get('src')
            if href and (href.endswith('.pdf') or 'video' in href.lower()):
                items_found = True
                full_url = urljoin(response.url, href)
                sku = item.css('::attr(data-sku), .sku::text').get(default='unknown').strip()
                yield {
                    'url': full_url,
                    'category': item.css('::attr(data-category), .category::text').get(default='dealer').strip(),
                    'issue': item.css('::attr(data-issue), .issue::text').get(default='unknown').strip(),
                    'product': item.css('::attr(data-product), .product::text').get(default='unknown').strip(),
                    'sku': sku,
                    'depth': response.meta.get('depth', 0)
                }
        if not items_found:
            logger.warning("No items found on dealer page: %s, content: %s", response.url, response.text[:500] if hasattr(response, 'text') else "No text content")
        next_page = response.css('a.next-page, .pagination .next, a:where(:text("Next"))').attrib.get('href')
        if next_page:
            logger.info("Found next page: %s", next_page)
            yield scrapy.Request(
                url=urljoin(response.url, next_page),
                meta={'playwright': True, 'playwright_context': 'persistent', 'playwright_context_kwargs': {'storage_state': '/home/vincent/ixome/scrapy-selenium/control4_scraper/cookies.json', 'ignoreHTTPSErrors': True}},
                callback=self.parse_dealer,
                dont_filter=True,
                errback=self.handle_error
            )

    def parse_public(self, response):
        logger.info("Parsing public page: %s", response.url)
        if isinstance(response, NotSupported):
            logger.warning("Skipping non-text response for %s, attempting to extract HTML", response.url)
            response = HtmlResponse(url=response.url, body=response.body, encoding='utf-8')
        items_found = False
        for pdf in response.css('a[href$=".pdf"], embed[type="application/pdf"]'):
            items_found = True
            href = pdf.attrib.get('href') or pdf.attrib.get('src')
            full_url = urljoin(response.url, href)
            sku = pdf.css('::attr(data-sku), .sku::text').get(default='unknown').strip()
            yield {
                'url': full_url,
                'category': pdf.css('::attr(data-category), .category::text').get(default='public').strip(),
                'issue': pdf.css('::attr(data-issue), .issue::text').get(default='unknown').strip(),
                'product': pdf.css('::attr(data-product), .product::text').get(default='unknown').strip(),
                'sku': sku,
                'depth': response.meta.get('depth', 0)
            }
        if not items_found:
            logger.warning("No PDFs found on public page: %s", response.url)

    def handle_error(self, failure):
        logger.error("Request failed: %s, Error: %s, Traceback: %s", failure.request.url, failure.value, failure.getTraceback())