import os
import sys
import json
import urllib.parse
import requests
from playwright.sync_api import sync_playwright

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def load_watchlist():
    try:
        with open("watchlist.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_watchlist(data):
    with open("watchlist.json", "w") as f:
        json.dump(data, f, indent=2)

def send_telegram_alert(item_name, status_message):
    if not TELEGRAM_BOT_TOKEN: return
    message = f"🚨 **INSTAMART UPDATE** 🚨\n\n📦 **Item:** {item_name}\n🔔 **Status:** {status_message}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})

def check_stock_with_coordinates(url, lat, lng):
    """Bypasses pincodes by injecting lat/long directly into browser context geolocation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Grant geo-location permissions and pass custom browser coordinates
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            permissions=["geolocation"],
            geolocation={"latitude": float(lat), "longitude": float(lng)}
        )
        page = context.new_page()
        
        try:
            # Open product listing target URL directly
            page.goto(url, timeout=45000)
            page.wait_for_timeout(4000)
            
            # Fetch clean Item title from meta text
            item_title = page.title().split('|')[0].strip()
            if not item_title or "instamart" in item_title.lower():
                item_title = "Target Product"

            page_source = page.content().lower()
            
            if "out of stock" in page_source or "not available" in page_source:
                return item_title, "OUT_OF_STOCK"
            elif "add" in page_source or "add to cart" in page_source:
                return item_title, "IN_STOCK"
            return item_title, "UNKNOWN"
        except Exception as e:
            print(f"Scraper error: {e}")
            return "Product Link", "ERROR"
        finally:
            browser.close()

if __name__ == "__main__":
    # Check if UI arguments were passed down
    args = sys.argv[1:]
    action_type = args[0] if len(args) > 0 else "CHECK"

    if action_type == "ADD" and len(args) >= 4:
        prod_url = args[1]
        latitude = args[2]
        longitude = args[3]
        
        print(f"Adding link to monitor: {prod_url} at [{latitude}, {longitude}]")
        # Run test to retrieve product title and initial status
        title, initial_status = check_stock_with_coordinates(prod_url, latitude, longitude)
        
        current_list = load_watchlist()
        current_list.append({
            "item_name": title,
            "url": prod_url,
            "latitude": latitude,
            "longitude": longitude
        })
        save_watchlist(current_list)
        print(f"Successfully tracked: {title}")
        send_telegram_alert(title, f"Added to monitoring dashboard successfully! Current Status: {initial_status}")

    else:
        # Standard background cron routine loop
        watchlist = load_watchlist()
        print(f"Scanning {len(watchlist)} targets via coordinate sessions...")
        for item in watchlist:
            title, status = check_stock_with_coordinates(item["url"], item["latitude"], item["longitude"])
            print(f"Result for {title}: {status}")
            if status == "IN_STOCK":
                send_telegram_alert(title, f"🟢 Available right now at coordinates [{item['latitude']}, {item['longitude']}]!")