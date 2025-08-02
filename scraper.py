import json
import os
import random
import requests

from json.decoder import JSONDecodeError
from dotenv import load_dotenv
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

load_dotenv()
TG_API = os.getenv('TG_API')
CHAT_ID = os.getenv('CHAT_ID')

LISTINGS_FILE = 'listings.json'
CONFIG_FILE = 'config.json'

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

ua = random.choice(UA_POOL)

options = Options()
options.add_argument('--headless=new')
options.add_argument('--disable-gpu')
options.add_argument("--window-size=780,1080")
options.add_argument('--disable-dev-shm-usage')
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument(f"user-agent={ua}")
options.add_argument('--no-sandbox')
options.add_argument("--disable-logging")
options.add_argument("--log-level=3")

driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(10)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Asia/Jerusalem"})
driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": "he-IL"})

if os.path.exists(LISTINGS_FILE):
    try:
        with open(LISTINGS_FILE, 'r', encoding='utf-8') as f:
            scraped_data = json.load(f)
            scraped_urls = {item['url'] for item in scraped_data}
    except JSONDecodeError:
        scraped_data = []
        scraped_urls = set()
else:
    scraped_data = []
    scraped_urls = set()

new_listings = []

with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)
urls = [area["url"] for area in config["areas"]]

first_it = True
for url in urls:
    print(f"scraping {url}")
    driver.get(url)
    if driver.current_url.startswith("validate"):
        print(f"Bot detection {driver.current_url}")
        continue
    sleep(5)

    if first_it:
        # luring the popup in
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(5)
        driver.execute_script("""
          const iframe = document.querySelector('iframe[title="Modal Message"]');
          if (iframe) iframe.style.display = 'none';
        """)
        sleep(4)
        driver.execute_script("window.scrollTo(0, 0);")
        first_it = False

    items = (
        driver.find_elements(By.CSS_SELECTOR, 'li[data-testid="platinum-item"]') +
        driver.find_elements(By.CSS_SELECTOR, 'li[data-testid="item-basic"]') +
        driver.find_elements(By.CSS_SELECTOR, 'li[data-testid="agency-item"]')
    )

    items.sort(key=lambda el: el.location['y'])

    for item in items:
        try:
            relative_url = item.find_element(By.CSS_SELECTOR, 'a.item-layout_itemLink__CZZ7w').get_attribute('href')
            url = f"https://www.yad2.co.il{relative_url}" if relative_url.startswith("/realestate") else relative_url
            if url in scraped_urls:
                continue
            driver.execute_script("arguments[0].scrollIntoView(true);", item)
            sleep(0.7)
            img_tag = item.find_element(By.CSS_SELECTOR, 'img[data-testid="image"]')
            img = img_tag.get_attribute('src')
            price = item.find_element(By.CLASS_NAME, 'feed-item-price_price__ygoeF').text
            address = item.find_element(By.CSS_SELECTOR, 'h2 span.item-data-content_heading__tphH4').text
            info_lines = item.find_elements(By.CSS_SELECTOR, 'h2 span.item-data-content_itemInfoLine__AeoPP')
            details = info_lines[1].text if len(info_lines) > 1 else ''

            listing = {
                "url": url,
                "img": img,
                "address": address,
                "price": price,
                "details": details
            }

            new_listings.append(listing)
            scraped_data.append(listing)
            scraped_urls.add(url)

        except Exception as e:
            print(f"Error extracting listing: {e}")

    sleep(4)
    driver.refresh()

driver.quit()

with open(LISTINGS_FILE, 'w', encoding='utf-8') as f:
    json.dump(scraped_data, f, indent=2, ensure_ascii=False)

print(f"Scraping complete. {len(new_listings)} new listings found.")

for listing in new_listings:
    msg = f"""
📢 <b>New Listing</b>
🏠 <b>Address:</b> {listing['address']}
💰 <b>Price:</b> {listing['price']}
📋 <b>Details:</b> {listing['details']}
🔗 <a href="{listing['url']}">View Listing</a>
"""
    img = listing['img']

    # Send photo with caption
    requests.post(
        f"https://api.telegram.org/bot{TG_API}/sendPhoto",
        data={
            "chat_id": CHAT_ID,
            "caption": msg,
            "parse_mode": "HTML"
        },
        files={
            "photo": requests.get(img).content
        }
    )
    sleep(1.5)