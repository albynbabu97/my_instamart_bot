import os
import sys
import urllib.parse
import requests
from playwright.sync_api import sync_playwright

# Enhanced Loading Block
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

print("--- DEBUG INFO ---")
print(f"Is BOT_TOKEN detected?: {'YES (Length: ' + str(len(TELEGRAM_BOT_TOKEN)) + ')' if TELEGRAM_BOT_TOKEN else 'NO'}")
print(f"Is CHAT_ID detected?: {'YES' if TELEGRAM_CHAT_ID else 'NO'}")
print("------------------")

# Hardcoded Backup (ONLY use this if your repository is strictly PRIVATE!)
# If GitHub secrets keep failing, you can paste your strings directly below:
if not TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = "YOUR_ACTUAL_BOT_TOKEN_HERE"  # e.g., "8747316097:AAFi..."
if not TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = "624616966"

# 2. Define the items you want to monitor here (Item Name, Pincode)
WATCHLIST = [
    {"item_name": "Amul Gold Milk 500ml", "pincode": "560001"},
    {"item_name": "Coca-Cola Diet Coke 300ml", "pincode": "560001"}
]

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
        # Launching with a mobile user-agent to load simpler mobile layouts and minimize bot detection
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Step A: Hit landing page to initialize session
            page.goto("https://www.swiggy.com/instamart", timeout=45000)
            page.wait_for_timeout(2000)
            
            # Step B: Set Location
            # Simulating manual user flow to safely bypass basic geo-blocking fences
            if page.locator("text=Select Location").is_visible():
                page.click("text=Select Location")
                page.wait_for_selector("input[placeholder*='area']", timeout=5000)
                page.fill("input[placeholder*='area']", pincode)
                page.press("input[placeholder*='area']", "Enter")
                page.wait_for_timeout(3000)
            
            # Step C: Direct Search Query
            encoded_query = urllib.parse.quote(item_name)
            search_url = f"https://www.swiggy.com/instamart/search?item={encoded_query}"
            page.goto(search_url, timeout=45000)
            page.wait_for_timeout(4000) # Let dynamic elements render
            
            # Step D: Read the page data to parse state
            page_source = page.content().lower()
            
            # Simple defensive keywords checks based on active CSS layout text strings
            if "out of stock" in page_source or "no results found" in page_source:
                print(f"❌ '{item_name}' is currently out of stock.")
                return "OUT_OF_STOCK"
            elif "add" in page_source or "add to cart" in page_source:
                print(f"✅ '{item_name}' is available!")
                return "IN_STOCK"
            else:
                print("❓ Page text configuration changed. Manual selector update might be needed.")
                return "UNKNOWN"
                
        except Exception as e:
            print(f"⚠️ Error scanning page: {e}")
            return "ERROR"
        finally:
            browser.close()

if __name__ == "__main__":
    # Loop over all items tracked in your configuration list
    for target in WATCHLIST:
        status = check_stock(target["pincode"], target["item_name"])
        if status == "IN_STOCK":
            send_telegram_alert(target["item_name"], target["pincode"])
