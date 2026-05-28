import os
import json
import urllib.parse
import requests
from playwright.sync_api import sync_playwright

# 1. Load Secrets securely from GitHub Environment Variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def load_watchlist():
    """Loads target configurations dynamically from the JSON schema file."""
    try:
        with open("watchlist.json", "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"❌ Error reading watchlist.json: {e}")
        return []

def send_telegram_alert(item_name, pincode):
    """Sends a push notification directly to your phone."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Telegram secrets are missing.")
        return
        
    message = f"🚨 **INSTAMART STOCK ALERT** 🚨\n\n🟢 **'{item_name}'** is now back in stock at pincode **{pincode}**!\n\nOpen Instamart and place your order quickly!"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": message, 
            "parse_mode": "Markdown"
        })
        if response.status_code == 200:
            print(f"Notification sent successfully for {item_name}!")
        else:
            print(f"Telegram API Error: {response.text}")
    except Exception as e:
        print(f"Failed to connect to Telegram: {e}")

def check_stock(pincode, item_name):
    """Launches an isolated headless browser to track item availability."""
    print(f"🔍 Checking: '{item_name}' for Pincode: {pincode}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto("https://www.swiggy.com/instamart", timeout=45000)
            page.wait_for_timeout(2000)
            
            if page.locator("text=Select Location").is_visible():
                page.click("text=Select Location")
                page.wait_for_selector("input[placeholder*='area']", timeout=5000)
                page.fill("input[placeholder*='area']", pincode)
                page.press("input[placeholder*='area']", "Enter")
                page.wait_for_timeout(3000)
            
            encoded_query = urllib.parse.quote(item_name)
            search_url = f"https://www.swiggy.com/instamart/search?item={encoded_query}"
            page.goto(search_url, timeout=45000)
            page.wait_for_timeout(4000)
            
            page_source = page.content().lower()
            
            if "out of stock" in page_source or "no results found" in page_source:
                print(f"❌ '{item_name}' is currently out of stock.")
                return "OUT_OF_STOCK"
            elif "add" in page_source or "add to cart" in page_source:
                print(f"✅ '{item_name}' is available!")
                return "IN_STOCK"
            else:
                print("❓ Page text configuration changed or item ambiguous.")
                return "UNKNOWN"
                
        except Exception as e:
            print(f"⚠️ Error scanning page: {e}")
            return "ERROR"
        finally:
            browser.close()

if __name__ == "__main__":
    watchlist = load_watchlist()
    if not watchlist:
        print("Watchlist empty or file failed to open. Terminating run.")
    else:
        print(f"Loaded {len(watchlist)} active item trackers from configuration database.")
        for target in watchlist:
            status = check_stock(target["pincode"], target["item_name"])
            if status == "IN_STOCK":
                send_telegram_alert(target["item_name"], target["pincode"])
