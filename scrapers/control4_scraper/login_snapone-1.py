# /home/vincent/ixome/scrapy-selenium/control4_scraper/login_snapone.py
# Logs into Snap One Partner Store, toggles Advanced Search, scrapes PDFs.
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time
import logging
import json
import random

# Setup logging
logging.basicConfig(level=logging.INFO, filename='login_snapone.log', format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='/home/vincent/ixome/.env')

def login_snapone():
    username = os.getenv('SNAPONE_USERNAME')
    password = os.getenv('SNAPONE_PASSWORD')
    if not username or not password:
        logger.error("SNAPONE_USERNAME or SNAPONE_PASSWORD not found in .env")
        raise ValueError("Missing credentials in .env")

    with sync_playwright() as p:
        # Launch persistent context with a fresh profile if needed
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir='/home/vincent/ixome/snapone_profile',
                headless=False,  # Keep False for debugging
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-web-security', '--ignore-certificate-errors'],
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 720},
                bypass_csp=True,
                geolocation={'latitude': 37.7749, 'longitude': -122.4194},
                extra_http_headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.snapav.com/'
                }
            )
        except Exception as e:
            logger.error(f"Failed to launch context: {e}")
            raise
        page = context.new_page()

        try:
            # Navigate to Snap One homepage
            logger.info("Navigating to https://www.snapav.com")
            page.goto('https://www.snapav.com', wait_until='domcontentloaded', timeout=60000)
            time.sleep(random.uniform(1, 3))

            # Handle cookie consent
            try:
                page.click('button#onetrust-accept-btn-handler, button[aria-label*="cookie"], button.accept-cookies, button#accept-cookies', timeout=10000)
                logger.info("Accepted cookie consent on homepage")
            except Exception:
                logger.info("No cookie consent popup on homepage")

            # Navigate to login page
            logger.info("Navigating to login page")
            try:
                page.click('a[href*="LogonForm"], a.login-link, a#login-button, a[class*="login"], a[title*="Log In"]', timeout=10000)
                logger.info("Clicked login link")
            except Exception:
                logger.warning("Login link not found, navigating directly to https://www.snapav.com/shop/LogonForm")
                page.goto('https://www.snapav.com/shop/LogonForm', wait_until='domcontentloaded', timeout=60000)
            time.sleep(random.uniform(1, 3))

            # Wait for page load
            page.wait_for_load_state('networkidle', timeout=90000)
            logger.info("Login page fully loaded")

            # Handle cookie consent (if reappears)
            try:
                page.click('button#onetrust-accept-btn-handler, button[aria-label*="cookie"], button.accept-cookies, button#accept-cookies', timeout=10000)
                logger.info("Accepted cookie consent on login page")
            except Exception:
                logger.info("No cookie consent popup on login page")

            # Fill login form (target main form with class="cvform")
            logger.info("Filling login form")
            try:
                page.wait_for_selector('form[name="Logon"]', timeout=60000)
                page.type('input[name="logonId"].cvform', username, delay=random.randint(50, 150))
                page.type('input[name="logonPassword"].cvform', password, delay=random.randint(50, 150))
                page.evaluate('''() => {
                    const form = document.querySelector('form[name="Logon"]');
                    if (!form) throw new Error("Form not found");
                    const logonId = document.querySelector('input[name="logonId"].cvform');
                    const logonPassword = document.querySelector('input[name="logonPassword"].cvform');
                    const reLogonURL = document.querySelector('form[name="Logon"] input[name="reLogonURL"]');
                    const catalogId = document.querySelector('form[name="Logon"] input[name="catalogId"]');
                    const storeId = document.querySelector('form[name="Logon"] input[name="storeId"]');
                    const errorViewName = document.querySelector('form[name="Logon"] input[name="errorViewName"]');
                    if (!logonId || !logonPassword || !reLogonURL || !catalogId || !storeId || !errorViewName) {
                        throw new Error("Required form fields not found: " + 
                            [!logonId ? "logonId" : "", !logonPassword ? "logonPassword" : "", 
                             !reLogonURL ? "reLogonURL" : "", !catalogId ? "catalogId" : "", 
                             !storeId ? "storeId" : "", !errorViewName ? "errorViewName" : ""].filter(Boolean).join(", "));
                    }
                    logonId.dispatchEvent(new Event("input"));
                    logonPassword.dispatchEvent(new Event("input"));
                    reLogonURL.value = "LogonForm";
                    catalogId.value = "10010";
                    storeId.value = "10151";
                    errorViewName.value = "LogonForm";
                    const langId = document.querySelector('form[name="Logon"] input[name="langId"]');
                    if (langId) langId.value = "-1";
                }''')
                time.sleep(random.uniform(0.5, 1.5))

                # Submit form
                logger.info("Attempting to submit login form")
                try:
                    submit_button = page.locator('form[name="Logon"] button.btn-5[type="submit"]')
                    page.wait_for_selector('form[name="Logon"] button.btn-5[type="submit"]', state='visible', timeout=15000)
                    submit_button.click(timeout=10000)
                    logger.info("Clicked submit button")
                except Exception as e:
                    logger.warning(f"Button click failed: {e}, trying JavaScript submission")
                    page.evaluate('''() => {
                        const form = document.querySelector('form[name="Logon"]');
                        if (form) form.submit();
                        else throw new Error("Form not found for submission");
                    }''')
                    logger.info("Submitted form via JavaScript")
            except Exception as e:
                logger.error(f"Form filling failed: {e}")
                page.screenshot(path='form_failure.png', timeout=60000)
                page.content()
                with open('form_failure.html', 'w') as f:
                    f.write(page.content())
                console_errors = page.evaluate('() => window.console._errors || []') or []
                logger.error(f"Console errors: {console_errors}")
                raise Exception(f"Form filling failed, inspect browser (screenshot saved as form_failure.png, page content saved as advanced_search_failure.html)")

            # Save cookies immediately
            context.storage_state(path='cookies.json')
            logger.info("Storage state saved to cookies.json")
            with open('session_storage.json', 'w') as f:
                json.dump(page.evaluate('JSON.stringify(sessionStorage)'), f)
            logger.info("sessionStorage saved to session_storage.json")

            # Wait for redirect
            try:
                page.wait_for_url('https://www.snapav.com/shop/**', timeout=90000)
                if 'LogonForm' in page.url or 'login' in page.url.lower():
                    page.screenshot(path='login_failure.png', timeout=60000)
                    page_content = page.content()
                    with open('login_failure.html', 'w') as f:
                        f.write(page_content)
                    console_errors = page.evaluate('() => window.console._errors || []') or []
                    logger.error(f"Console errors: {console_errors}")
                    raise Exception(f"Still on login page: {page.url}, authentication failed (page content saved as login_failure.html)")
                logger.info(f"Login successful, redirected to {page.url}")
            except Exception as e:
                logger.error(f"Login failed or no redirect detected: {e}")
                page.screenshot(path='login_failure.png', timeout=60000)
                page_content = page.content()
                with open('login_failure.html', 'w') as f:
                    f.write(page.content())
                console_errors = page.evaluate('() => window.console._errors || []') or []
                logger.error(f"Console errors: {console_errors}")
                raise Exception(f"Login failed, check credentials or inspect browser (screenshot saved as login_failure.png, page content saved as login_failure.html), current URL: {page.url}")

            # Handle "go to homepage" box
            logger.info("Checking for 'go to homepage' box on TopCategoriesDisplay")
            try:
                page.wait_for_load_state('networkidle', timeout=90000)
                page.click('a[href*="/shop/home"], a[href*="/shop/en/snapav/home"], button:where(:text("Go to Homepage")), a:where(:text("Homepage"))', timeout=15000)
                logger.info("Clicked 'go to homepage' link/button")
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.warning(f"No 'go to homepage' box found or click failed: {e}")
                logger.info("Proceeding to product files page")

            # Save storage state again
            context.storage_state(path='cookies.json')
            logger.info("Storage state saved to cookies.json")
            with open('session_storage.json', 'w') as f:
                json.dump(page.evaluate('JSON.stringify(sessionStorage)'), f)
            logger.info("sessionStorage saved to session_storage.json")

            # Navigate to product-files-videos-search
            logger.info("Navigating to product-files-videos-search")
            product_files_url = 'https://www.snapav.com/shop/en/snapav/product-files-videos-search'
            page.goto(product_files_url, wait_until='networkidle', timeout=90000)
            time.sleep(random.uniform(1, 3))

            # Wait for page load (potential Angular)
            try:
                page.wait_for_function('window.angular !== undefined', timeout=10000)
                logger.info("Angular loaded on product-files-videos-search")
            except Exception:
                logger.info("No Angular detected, proceeding with standard DOM")

            # Toggle Advanced Search section
            try:
                page.wait_for_selector('div#advAccordion', state='visible', timeout=15000)
                page.click('div#advAccordion', timeout=10000)
                logger.info("Clicked Advanced Search toggle")
                time.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.info(f"Advanced Search toggle click failed: {e}")

            # Use Advanced Search
            try:
                page.wait_for_selector('input#contentSearchTerm', timeout=90000)
                page.evaluate('''() => {
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
                }''')
                page.wait_for_selector('input#contentSearchTerm', state='visible', timeout=90000)
                page.type('input#contentSearchTerm', 'pdf', delay=random.randint(50, 150))
                logger.info("Typed 'pdf' in Advanced Search input")
                page.evaluate('''() => {
                    const input = document.querySelector('input#contentSearchTerm');
                    if (input) {
                        input.dispatchEvent(new Event("input"));
                        if (typeof ContentSearch !== 'undefined' && ContentSearch.checkChange) {
                            ContentSearch.checkChange({ target: input });
                        }
                    }
                }''')
                time.sleep(random.uniform(0.5, 1.5))
                try:
                    page.click('a#qop-submit', timeout=10000)
                    logger.info("Clicked 'GO' button (a#qop-submit)")
                except Exception as e:
                    logger.warning(f"GO button click failed: {e}, trying JavaScript submission")
                    page.evaluate('''() => {
                        if (typeof submitContentSearch !== 'undefined') {
                            submitContentSearch();
                        } else {
                            const form = document.querySelector('form:has(input#contentSearchTerm)');
                            if (form) form.submit();
                            else throw new Error("Advanced Search form or submitContentSearch not found");
                        }
                    }''')
                    logger.info("Triggered submitContentSearch or form submission")
                try:
                    page.wait_for_selector('text=Displaying documents & videos', timeout=300000)  # Wait for results text
                    page.wait_for_load_state('domcontentloaded', timeout=300000)
                    pdf_links = [el.get_attribute('href') for el in page.query_selector_all('a[href*=".pdf"]')] + \
                                [el.get_attribute('src') for el in page.query_selector_all('embed[type="application/pdf"]') if el.get_attribute('src')]
                    if not pdf_links:
                        logger.warning("No PDF links or embeds found, checking page content")
                        page_content = page.content()
                        with open('debug_page_content.html', 'w') as f:
                            f.write(page_content)
                        logger.info("Page content saved to debug_page_content.html for inspection")
                    else:
                        logger.info("Search results loaded with PDFs: %s", pdf_links)
                    time.sleep(5)
                    page.screenshot(path='advanced_search_success.png', timeout=60000)
                except Exception as e:
                    logger.warning(f"Results panel wait failed: {e}, trying Enter keypress")
                    page.press('input#contentSearchTerm', 'Enter')
                    logger.info("Pressed Enter in Advanced Search input")
                    page.wait_for_selector('text=Displaying documents & videos', timeout=300000)
                    page.wait_for_load_state('domcontentloaded', timeout=300000)
                    pdf_links = [el.get_attribute('href') for el in page.query_selector_all('a[href*=".pdf"]')] + \
                                [el.get_attribute('src') for el in page.query_selector_all('embed[type="application/pdf"]') if el.get_attribute('src')]
                    if not pdf_links:
                        logger.warning("No PDF links or embeds found after Enter, checking page content")
                        page_content = page.content()
                        with open('debug_page_content_after_enter.html', 'w') as f:
                            f.write(page_content)
                        logger.info("Page content saved to debug_page_content_after_enter.html for inspection")
                    else:
                        logger.info("Search results loaded with PDFs after Enter: %s", pdf_links)
                    time.sleep(5)
                    page.screenshot(path='advanced_search_success.png', timeout=60000)
            except Exception as e:
                logger.error(f"Failed to handle Advanced Search: {e}")
                page.screenshot(path='advanced_search_failure.png', timeout=60000)
                page.content()
                with open('advanced_search_failure.html', 'w') as f:
                    f.write(page.content())
                console_errors = page.evaluate('() => window.console._errors || []') or []
                logger.error(f"Console errors: {console_errors}")
                input("Press Enter to close browser (error occurred)...")
                raise Exception(f"Failed to load Advanced Search results, inspect browser (screenshot saved as advanced_search_failure.png, page content saved as advanced_search_failure.html), current URL: {page.url}")

            # Save storage state
            context.storage_state(path='cookies.json')
            logger.info("Storage state saved to cookies.json")
            with open('session_storage.json', 'w') as f:
                json.dump(page.evaluate('JSON.stringify(sessionStorage)'), f)
            logger.info("sessionStorage saved to session_storage.json")

            logger.info("Login and Advanced Search complete, browser left open for scraping")
            input("Press Enter to close browser...")

        except Exception as e:
            logger.error(f"Error during login: {e}")
            page.screenshot(path='error_screenshot.png', timeout=60000)
            page.content()
            with open('error_screenshot.html', 'w') as f:
                f.write(page.content())
            console_errors = page.evaluate('() => window.console._errors || []') or []
            logger.error(f"Console errors: {console_errors}")
            input("Press Enter to close browser (error occurred)...")
            raise

if __name__ == "__main__":
    login_snapone()