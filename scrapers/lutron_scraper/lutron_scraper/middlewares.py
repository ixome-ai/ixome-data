from importlib import import_module
import logging
from os.path import exists

from scrapy import signals
from scrapy.http import HtmlResponse
from scrapy.utils.misc import load_object
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException

class SeleniumMiddleware:
    """Scrapy middleware to handle JavaScript pages using Selenium"""

    def __init__(self, driver_name, driver_executable_path, driver_arguments,
                 browser_executable_path, command_executor, wait_time=0):
        """Initialize the selenium webdriver

        Parameters
        ----------
        driver_name: str
            The selenium ``WebDriver`` to use
        driver_executable_path: str
            The path of the executable binary of the driver
        driver_arguments: list
            A list of arguments to initialize the driver
        browser_executable_path: str
            The path of the executable binary of the browser
        command_executor: str
            The Selenium remote server endpoint
        wait_time: int
            The default wait time for Selenium to wait for elements
        """
        self.logger = logging.getLogger(__name__)

        webdriver_base_path = f'selenium.webdriver.{driver_name}'
        driver_klass_module = import_module(f'{webdriver_base_path}.webdriver')
        driver_klass = getattr(driver_klass_module, 'WebDriver')

        driver_options_module = import_module(f'{webdriver_base_path}.options')
        driver_options_klass = getattr(driver_options_module, 'Options')

        driver_options = driver_options_klass()

        if browser_executable_path and exists(browser_executable_path):
            driver_options.binary_location = browser_executable_path
        for argument in driver_arguments:
            driver_options.add_argument(argument)

        driver_kwargs = {}
        if command_executor:
            driver_kwargs = {
                'command_executor': command_executor,
                'desired_capabilities': getattr(DesiredCapabilities, driver_name.upper()),
                'options': driver_options
            }
        else:
            driver_kwargs = {
                'service': Service(driver_executable_path),
                'options': driver_options
            }

        self.wait_time = wait_time
        self.driver = driver_klass(**driver_kwargs)

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""
        driver_name = crawler.settings.get('SELENIUM_DRIVER_NAME')
        driver_executable_path = crawler.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        browser_executable_path = crawler.settings.get('SELENIUM_BROWSER_EXECUTABLE_PATH')
        command_executor = crawler.settings.get('SELENIUM_COMMAND_EXECUTOR')
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS')
        wait_time = crawler.settings.get('SELENIUM_DEFAULT_WAIT_TIME', 0)

        if driver_name is None:
            raise ValueError('You must specify SELENIUM_DRIVER_NAME in settings.py')
        if command_executor is None and driver_executable_path is None:
            raise ValueError('You must specify SELENIUM_DRIVER_EXECUTABLE_PATH or SELENIUM_COMMAND_EXECUTOR in settings.py')

        middleware = cls(
            driver_name=driver_name,
            driver_executable_path=driver_executable_path,
            driver_arguments=driver_arguments,
            browser_executable_path=browser_executable_path,
            command_executor=command_executor,
            wait_time=wait_time
        )

        crawler.signals.connect(middleware.spider_closed, signals.spider_closed)

        return middleware

    def process_request(self, request, spider):
        """Process a request using the selenium driver if the request is a SeleniumRequest"""
        if not isinstance(request, SeleniumRequest):
            return None

        self.driver.get(request.url)

        for cookie_name, cookie_value in request.cookies.items():
            self.driver.add_cookie({
                'name': cookie_name,
                'value': cookie_value
            })

        if request.wait_until:
            try:
                WebDriverWait(self.driver, request.wait_time or self.wait_time).until(
                    request.wait_until
                )
            except TimeoutException:
                pass

        if request.screenshot:
            request.meta['screenshot'] = self.driver.get_screenshot_as_png()

        if request.script:
            self.driver.execute_script(request.script)

        body = str.encode(self.driver.page_source)

        # Expose the driver via the "meta" attribute
        request.meta.update({'driver': self.driver})

        return HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()