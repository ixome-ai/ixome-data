# /home/vincent/ixome/scrapy-selenium/control4_scraper/control4_scraper/middlewares.py
# Selenium middleware for Scrapy, with added import for webdriver.
from selenium import webdriver  # Added to fix 'name 'webdriver' is not defined'
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from scrapy.http import HtmlResponse
from scrapy.utils.python import to_bytes
import time
import logging

logger = logging.getLogger(__name__)

class SeleniumMiddleware(object):
    def __init__(self, driver_name, driver_executable_path, browser_executable_path, driver_arguments, driver_headless):
        """Initialize the selenium webdriver

        Parameters
        ----------
        driver_name: str
            The selenium ``webdriver`` to use
        driver_executable_path: str
            The path of the executable binary of the driver
        browser_executable_path: str
            The path of the executable binary of the browser
        driver_arguments: list[str]
            A list of arguments to pass to the driver
        driver_headless: bool
            Whether to use headless mode
        """

        self.driver_name = driver_name
        self.driver_executable_path = driver_executable_path
        self.browser_executable_path = browser_executable_path
        self.driver_arguments = driver_arguments
        self.driver_headless = driver_headless

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize middleware from crawler settings"""

        driver_name = crawler.settings['SELENIUM_DRIVER_NAME']
        driver_executable_path = crawler.settings['SELENIUM_DRIVER_EXECUTABLE_PATH']
        browser_executable_path = crawler.settings['SELENIUM_BROWSER_EXECUTABLE_PATH']
        driver_arguments = crawler.settings['SELENIUM_DRIVER_ARGUMENTS']
        driver_headless = crawler.settings['SELENIUM_DRIVER_HEADLESS']

        middleware = cls(driver_name, driver_executable_path, browser_executable_path, driver_arguments, driver_headless)

        middleware.driver = webdriver.Chrome(service=Service(executable_path=driver_executable_path), options=Options())

        return middleware

    def process_request(self, request, spider):
        """Process a request using the selenium driver if applicable"""

        if not request.meta.get('selenium'):
            return None

        self.driver.get(request.url)

        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie(
                {
                    'name': cookie_name,
                    'value': cookie_value
                }
            )

        if request.meta.get('wait_time'):
            time.sleep(request.meta['wait_time'])

        if request.meta.get('wait_for'):
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, request.meta['wait_for']))
            )

        body = to_bytes(self.driver.page_source)  # body must be of type bytes
        return HtmlResponse(self.driver.current_url, body=body, encoding='utf-8', request=request)

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""

        self.driver.quit()