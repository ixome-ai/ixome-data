import scrapy
from scrapy_playwright.page import PageMethod
from lutron_scraper.items import LutronScraperItem
import logging
from urllib.parse import urljoin
from scrapy.exceptions import NotSupported
from scrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

class LutronHomeworksSpider(scrapy.Spider):
    name = 'lutron_homeworks'
    start_urls = ['https://support.lutron.com/us/en/search?q=homeworks&scope=all']

    async def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                meta={
                    'playwright': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_load_state', 'networkidle', timeout=120000),
                        PageMethod('evaluate', '''() => {
                            const acceptBtn = document.querySelector('#onetrust-accept-btn-handler, button[onclick*="accept"]');
                            if (acceptBtn) acceptBtn.click();
                            // Scroll 5 times for full dynamic load
                            for (let i = 0; i < 5; i++) {
                                window.scrollTo(0, document.body.scrollHeight);
                                return new Promise(resolve => setTimeout(resolve, 3000));
                            }
                        }'''),
                        PageMethod('wait_for_timeout', 20000),  # 20s extra for JS
                    ]
                },
                callback=self.parse_search,
                errback=self.handle_error
            )

    def parse_search(self, response):
        logger.info(f"Parsing: {response.url}, status: {response.status}")
        if isinstance(response, NotSupported):
            response = HtmlResponse(url=response.url, body=response.body, encoding='utf-8')
        items_found = 0
        # Robust XPath: Any link with "homeworks" in text or href, in results context
        for link in response.xpath('//div[contains(text(), "results")]//following::a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "homeworks") or contains(@href, "homeworks") or contains(@href, "/article") or contains(@href, "/product")]'):
            items_found += 1
            item = LutronScraperItem()
            title = link.xpath('normalize-space(text()) | normalize-space(@title)').get(default='HomeWorks Result').strip()
            url = link.xpath('@href').get()
            # Desc from following p/div
            desc_nodes = link.xpath('following-sibling::p[1]/text() | following-sibling::div[1]//p/text() | ancestor::div[1]//p[contains(text(), title)]/text()')
            desc = ' '.join([t.strip() for t in desc_nodes.getall() if t.strip()])[:1000]
            if url and 'homeworks' in title.lower():
                item['url'] = urljoin(response.url, url)
                item['issue'] = title
                item['solution'] = desc or 'Troubleshooting guide for HomeWorks system.'
                item['product'] = 'HomeWorks'
                item['category'] = 'HomeWorks'
                yield item
                logger.info(f"Yielded {items_found}: {title[:50]}...")
        logger.info(f"Found {items_found} items")
        if items_found == 0:
            logger.warning("No items; log response.body[:2000] for debug")
            logger.warning(response.body[:2000].decode('utf-8', errors='ignore'))
        # Pagination: Next link
        next_page = response.xpath('//a[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "next") or contains(@aria-label, "next")]/@href').get()
        if next_page:
            yield scrapy.Request(
                url=urljoin(response.url, next_page),
                meta={'playwright': True, 'playwright_page_methods': [
                    PageMethod('wait_for_load_state', 'networkidle', timeout=60000),
                    PageMethod('evaluate', '''() => {
                        for (let i = 0; i < 5; i++) {
                            window.scrollTo(0, document.body.scrollHeight);
                            return new Promise(resolve => setTimeout(resolve, 3000));
                        }
                    }'''),
                    PageMethod('wait_for_timeout', 15000),
                ]},
                callback=self.parse_search
            )

    def handle_error(self, failure):
        logger.error(f"Failed {failure.request.url}: {failure.value}")