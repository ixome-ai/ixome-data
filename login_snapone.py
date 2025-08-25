from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time
import logging
import json
import random
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(level=logging.INFO, filename='/home/vincent/ixome/scrapy-selenium/control4_scraper/login_snapone.log',
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='w')  # Overwrite log
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
        # Launch browser
        context = p.chromium.launch_persistent_context(
            user_data_dir='/home/vincent/ixome/snapone_profile',
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-web-security'],
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
        page = context.new_page()

        try:
            # Navigate to Snap One homepage
            logger.info("Navigating to https://www.snapav.com")
            page.goto('https://www.snapav.com', wait_until='domcontentloaded', timeout=60000)
            time.sleep(random.uniform(0.5, 1.5))

            # Handle cookie consent
            try:
                page.click('button#onetrust-accept-btn-handler, button[aria-label*="cookie"], button.accept-cookies, button#accept-cookies', timeout=5000)
                logger.info("Accepted cookie consent on homepage")
            except Exception:
                logger.info("No cookie consent popup on homepage")

            # Navigate to login page
            logger.info("Navigating to login page")
            try:
                page.click('a[href*="LogonForm"], a.login-link, a#login-button, a[class*="login"], a[title*="Log In"]', timeout=5000)
                logger.info("Clicked login link")
            except Exception:
                logger.warning("Login link not found, navigating directly to https://www.snapav.com/shop/LogonForm")
                page.goto('https://www.snapav.com/shop/LogonForm', wait_until='domcontentloaded', timeout=60000)
            time.sleep(random.uniform(0.5, 1.5))

            # Wait for page load
            page.wait_for_load_state('networkidle', timeout=90000)
            logger.info("Login page fully loaded")

            # Handle cookie consent (if reappears)
            try:
                page.click('button#onetrust-accept-btn-handler, button[aria-label*="cookie"], button.accept-cookies, button#accept-cookies', timeout=5000)
                logger.info("Accepted cookie consent on login page")
            except Exception:
                logger.info("No cookie consent popup on login page")

            # Fill login form
            logger.info("Filling login form")
            page.wait_for_selector('form[name="Logon"]', timeout=60000)
            page.type('input[name="logonId"].cvform', username, delay=random.randint(50, 100))
            page.type('input[name="logonPassword"].cvform', password, delay=random.randint(50, 100))
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
                    throw new Error("Required form fields not found");
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
            time.sleep(random.uniform(0.3, 0.8))

            # Submit form
            logger.info("Attempting to submit login form")
            try:
                page.click('form[name="Logon"] button.btn-5[type="submit"]', timeout=10000)
                logger.info("Clicked submit button")
            except Exception as e:
                logger.warning(f"Button click failed: {e}, trying JavaScript submission")
                page.evaluate('document.querySelector("form[name=Logon]").submit()')
                logger.info("Submitted form via JavaScript")

            # Wait for redirect
            page.wait_for_url('https://www.snapav.com/shop/**', timeout=90000)
            if 'LogonForm' in page.url or 'login' in page.url.lower():
                raise Exception("Login failed, stayed on login page")
            logger.info("Login successful, redirected to %s", page.url)

            # Handle "go to homepage" box
            try:
                page.wait_for_selector('a[href*="/shop/home"], a[href*="/shop/en/snapav/home"], button:contains("Go to Homepage"), a:contains("Homepage")', timeout=10000)
                page.click('a[href*="/shop/home"], a[href*="/shop/en/snapav/home"], button:contains("Go to Homepage"), a:contains("Homepage")')
                logger.info("Clicked 'go to homepage' link/button")
                time.sleep(random.uniform(0.5, 1.5))
            except Exception:
                logger.info("No 'go to homepage' box found, proceeding")

            # Navigate to product-files-videos-search
            product_files_url = 'https://www.snapav.com/shop/en/snapav/product-files-videos-search'
            logger.info("Navigating to %s", product_files_url)
            page.goto(product_files_url, wait_until='networkidle', timeout=90000)
            time.sleep(random.uniform(0.5, 1.5))

            # Toggle Advanced Search section
            try:
                page.wait_for_selector('div#advAccordion', state='visible', timeout=10000)
                page.click('div#advAccordion')
                logger.info("Clicked Advanced Search toggle")
                time.sleep(random.uniform(0.5, 1))
            except Exception as e:
                logger.error(f"Advanced Search toggle click failed: {e}")

            # Fill and submit Advanced Search
            page.wait_for_selector('input#contentSearchTerm', timeout=90000)
            page.type('input#contentSearchTerm', 'pdf', delay=random.randint(50, 100))
            logger.info("Typed 'pdf' in Advanced Search input")
            time.sleep(random.uniform(0.3, 0.8))
            try:
                page.click('a#qop-submit', timeout=10000)
                logger.info("Clicked 'GO' button")
            except Exception as e:
                logger.warning(f"GO button click failed: {e}, pressing Enter")
                page.press('input#contentSearchTerm', 'Enter')
                logger.info("Pressed Enter in Advanced Search input")

            # Wait for results
            page.wait_for_selector('text=Displaying documents & videos', timeout=300000)
            logger.info("Search results loaded")

            # Scrape all PDFs
            pdf_data = []
            seen_urls = set()
            current_page = 1
            while True:
                # Wait for dynamic content
                page.wait_for_load_state('networkidle', timeout=90000)
                page.wait_for_selector('text=Displaying documents & videos', timeout=30000)
                
                # Debug: Save page HTML and count all links
                with open(f'/home/vincent/ixome/scrapy-selenium/control4_scraper/page_{current_page}.html', 'w') as f:
                    f.write(page.content())
                all_links = page.query_selector_all('a')
                pdf_links = [link for link in all_links if link.get_attribute('href') and '.pdf' in link.get_attribute('href')]
                logger.info(f"Page {current_page}: Found {len(all_links)} total links, {len(pdf_links)} PDF links")

                # Extract PDFs from current page
                items = page.query_selector_all('div.attachment-description')
                logger.info(f"Found {len(items)} result items on page {current_page}")
                for item in items:
                    a = item.query_selector('a[href*=".pdf"]')
                    category = item.query_selector('div.attachment-usage')
                    if a and category:
                        href = a.get_attribute('href')
                        full_url = urljoin(product_files_url, href)
                        if full_url in seen_urls:
                            logger.info(f"Skipping duplicate URL: {full_url}")
                            continue
                        seen_urls.add(full_url)
                        product_name = a.inner_text().strip() or 'Control4 Product'
                        category_text = category.inner_text().strip() if category else 'PDF Document'
                        issue = href.split('/')[-1].replace('.pdf', '')
                        pdf_data.append({
                            'url': full_url,
                            'product': product_name,
                            'category': category_text,
                            'issue': issue,
                            'solution': f"PDF link for parsing: {full_url}",
                            'depth': 0
                        })
                    else:
                        logger.warning(f"No PDF link or category found in item on page {current_page}: {item.inner_html()[:200]}...")
                logger.info(f"Extracted {len(pdf_data)} PDFs so far from page {current_page}")

                # Check for next page
                next_button = page.query_selector('a >> text="Next"')
                if next_button and next_button.is_visible():
                    next_button.click()
                    time.sleep(random.uniform(1, 2))
                    current_page += 1
                else:
                    logger.info("No 'Next' button found, ending pagination")
                    break

            # Save to JSON
            with open('/home/vincent/ixome/scrapy-selenium/control4_scraper/control4_data.json', 'w') as f:
                json.dump(pdf_data, f, indent=4)
            logger.info(f"Scraped {len(pdf_data)} PDFs and saved to control4_data.json")

            # Save session
            context.storage_state(path='cookies.json')
            logger.info("Storage state saved to cookies.json")
            logger.info("Scraping complete")
            context.close()

        except Exception as e:
            logger.error(f"Error during process: {e}")
            page.screenshot(path='/home/vincent/ixome/scrapy-selenium/control4_scraper/error_screenshot.png', timeout=60000)
            with open('/home/vincent/ixome/scrapy-selenium/control4_scraper/error_page.html', 'w') as f:
                f.write(page.content())
            console_errors = page.evaluate('() => window.console._errors || []') or []
            logger.error(f"Console errors: {console_errors}")
            context.close()
            raise

if __name__ == "__main__":
    login_snapone()