from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
from urllib.parse import urljoin
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_lutron_homeworks():
    options = Options()
    options.add_argument('--headless=False')  # Debug; True for prod
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)

    base_url = 'https://support.lutron.com/us/en/search?q=homeworks&scope=all'
    driver.get(base_url)
    time.sleep(5)
    try:
        accept_btn = wait.until(EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler')))
        accept_btn.click()
    except:
        pass

    data = []
    page = 1
    while True:
        logger.info(f"Scraping page {page}")
        # Scroll for load
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
        # Broader XPath: All /article, /product, or "HomeWorks" links after "results"
        links = driver.find_elements(By.XPATH, '//div[contains(text(), "results")]//following::a[contains(@href, "/article") or contains(@href, "/product") or contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "homeworks")]')
        for link in links[:20]:
            title = link.text.strip()
            url = link.get_attribute('href')
            if url:
                driver.get(url)
                time.sleep(2)
                desc_elements = driver.find_elements(By.TAG_NAME, 'p')
                desc = ' '.join([el.text.strip() for el in desc_elements if el.text.strip()])[:1000]
                item = {
                    'issue': title or 'HomeWorks Result',
                    'solution': desc or 'Troubleshooting guide.',
                    'product': 'HomeWorks',
                    'category': 'HomeWorks',
                    'url': url
                }
                data.append(item)
                logger.info(f"Scraped: {title[:50]}...")
                driver.back()
                time.sleep(1)
        # Next page: Explicit wait/click
        try:
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Next") or contains(@aria-label, "Next")]')))
            if next_btn:
                next_btn.click()
                time.sleep(5)
                page += 1
            else:
                break
        except:
            logger.info("No more pages")
            break
    driver.quit()
    # Save JSONL
    with open('lutron_homeworks_data.json', 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')
    logger.info(f"Scraped {len(data)} items")

if __name__ == "__main__":
    scrape_lutron_homeworks()