import json
import os
import requests
import random

from json.decoder import JSONDecodeError
from dotenv import load_dotenv
from time import sleep
from bs4 import BeautifulSoup

load_dotenv()
TG_API = os.getenv('TG_API')
CHAT_ID = os.getenv('CHAT_ID')

LISTINGS_FILE = 'listings.json'
CONFIG_FILE = 'config.json'

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

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

DEFAULT_HEADERS = {
    "User-Agent": f"{random.choice(UA_POOL)}",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Referer": "https://www.yad2.co.il/realestate/rent",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "no-cache",
}

for url in urls:
    sleep(random.uniform(3, 7))

    headers = DEFAULT_HEADERS.copy()
    headers["User-Agent"] = random.choice(UA_POOL)

    response = requests.get(url, headers=DEFAULT_HEADERS)
    response.encoding = 'utf-8'

    soup = BeautifulSoup(response.text, 'html.parser')
    if soup.title and 'shieldsquare' in soup.title.text.lower():
        print('Bot detected')
        break

    items = []
    items.extend(soup.select('li[data-testid="platinum-item"]'))
    items.extend(soup.select('li[data-testid="item-basic"]'))
    items.extend(soup.select('li[data-testid="agency-item"]'))

    for item in items:
        try:
            a = item.select_one('a.item-layout_itemLink__CZZ7w')
            if not a: continue
            href = a.get("href")
            url = f"https://www.yad2.co.il{href}" if href.startswith("/realestate") else href
            url = url[:url.rindex("?")]
            if url in scraped_urls: continue

            img = a.select_one('img[data-testid="image"]')
            img_url = (img.get("src") or img.get("data-src") or img.get("data-original") or "") if img else ""

            price_el = a.select_one(".feed-item-price_price__ygoeF")
            address_el = a.select_one("h2 span.item-data-content_heading__tphH4")
            info_lines = a.select("h2 span.item-data-content_itemInfoLine__AeoPP")

            price = price_el.get_text(strip=True) if price_el else ""
            address = address_el.get_text(strip=True) if address_el else ""
            details = info_lines[1].get_text(strip=True) if len(info_lines) > 1 else ""
            details.replace('•', '\n')

            listing = {
                "url": url,
                "img": img_url,
                "address": address,
                "price": price,
                "details": details
            }

            new_listings.append(listing)
            scraped_data.append(listing)

        except Exception as e:
            print(f"Error extracting listing: {e}")

with open(LISTINGS_FILE, 'w', encoding='utf-8') as f:
    json.dump(scraped_data, f, indent=2, ensure_ascii=False)

print(f"Scraping complete. {len(new_listings)} new listings found.")

for listing in new_listings:
    msg = f"""
📢 <b>New Listing</b> 📢
<b>Address:</b> {listing['address']}
<b>Price:</b> {listing['price']}
<b>Details:</b> {listing['details']}
<a href="{listing['url']}">View Listing</a>
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
