import sys
import random
import pandas as pd
import asyncio
from rebrowser_playwright.async_api import async_playwright
from playwright_stealth import Stealth
import io
from datetime import datetime
import os

# Fix encoding cho Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

UPCOMING_URL = "https://www.marketindex.com.au/upcoming-dividends"
ASX_URL = "https://www.marketindex.com.au/asx/{}"

# Set the correct profile path from brave://version
HOME_DIR = os.path.expanduser("~") 
USER_DATA_DIR = f"{HOME_DIR}/Library/Application Support/BraveSoftware/Brave-Browser/Profile 3"

# Verify the profile exists
if not os.path.exists(USER_DATA_DIR):
    print(f"❌ Profile not found: {USER_DATA_DIR}")
    print("\nAvailable profiles:")
    brave_base = f"{HOME_DIR}/Library/Application Support/BraveSoftware/Brave-Browser"
    if os.path.exists(brave_base):
        for item in os.listdir(brave_base):
            if item.startswith("Profile") or item == "Default":
                profile_path = os.path.join(brave_base, item)
                print(f"  - {profile_path}")
    sys.exit(1)

print(f"✓ Using Brave profile: {USER_DATA_DIR}")

DEBUG_DIR = "./debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

BRAVE_BROWSER = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

def parse_international_date(date_str):
    """Chuyển đổi các định dạng ngày sang YYYY-MM-DD."""
    if not date_str or date_str == "N/A":
        return "N/A"
    
    current_year = datetime.now().year
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(f"{date_str} {current_year}", "%d %b %Y").strftime("%Y-%m-%d")
        except:
            return date_str

def clean_to_number(text):
    """Xóa $, dấu phẩy và chuyển về float."""
    if not text or text in ['\u2010', '-', 'N/A']:
        return None
    try:
        return float(text.replace(',', '').replace('$', '').replace('%', '').strip())
    except:
        return None

def clean_percent_to_decimal(text):
    """Chuyển 100% thành 1.0, 1.66% thành 0.0166."""
    val = clean_to_number(text)
    return val / 100 if val is not None else None

async def get_element_text_with_retry(page, selector, max_attempts=10):
    for attempt in range(2):
        try:
            await page.wait_for_selector(selector, timeout=7000)
            for _ in range(max_attempts):
                raw_val = await page.locator(selector).first.inner_text()
                if raw_val and raw_val not in ['\u2010', '-', '']:
                    return raw_val.strip()
                await asyncio.sleep(0.5)
            if attempt == 0: 
                await page.reload(wait_until="domcontentloaded")
        except:
            if attempt == 0: 
                await page.reload(wait_until="domcontentloaded")
    return "N/A"

async def main():
    counter = 0
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            executable_path=BRAVE_BROWSER,
            headless=False,
            channel='brave',
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        stealth = Stealth()
        await stealth.apply_stealth_async(browser)
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        try:
            print(f"🌐 Loading {UPCOMING_URL}...")
            await page.goto(UPCOMING_URL, wait_until="domcontentloaded", timeout=90000)
            
            # Wait a bit for page to settle
            await asyncio.sleep(2)
            
            # Check page title to detect Cloudflare
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Take screenshot for debugging (do this after checking title)
            try:
                screenshot_path = os.path.join(DEBUG_DIR, "page_load.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved to {screenshot_path}")
            except Exception as e:
                print(f"⚠️  Could not take screenshot: {e}")
            
            if "Just a moment" in title or "Checking your browser" in title:
                print("\n⚠️  Cloudflare challenge detected!")
                print("💡 Please solve the Cloudflare challenge manually in the browser window")
                print("   (Click the checkbox or complete the challenge)")
                print("   Then press Enter here to continue...")
                input()
                
                # Wait for page to reload after Cloudflare
                await asyncio.sleep(3)
                title = await page.title()
                print(f"📄 New page title: {title}")
                
            # Check if table exists now
            print("⏳ Waiting for table to load...")
            try:
                await page.wait_for_selector("table tbody tr", timeout=20000)
                print("✓ Table found! Page loaded successfully!")
            except Exception as e:
                print(f"⚠️  Table still not found: {e}")
                print("\n💡 Debug info:")
                print(f"   Current URL: {page.url}")
                print(f"   Page title: {await page.title()}")
                
                # Take another screenshot
                try:
                    screenshot_path = os.path.join(DEBUG_DIR, "after_challenge.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"   Screenshot: {screenshot_path}")
                except:
                    pass
                
                print("\n   If Cloudflare is still showing, please solve it and press Enter...")
                print("   Otherwise, the website structure may have changed.")
                input()
                
                # Final attempt
                await page.wait_for_selector("table tbody tr", timeout=30000)
                print("✓ Table found! Continuing...")
                
        except Exception as e:
            screenshot_path = os.path.join(DEBUG_DIR, f"page_error_{counter}.png")
            try:
                await page.screenshot(path=screenshot_path, full_page=True)
            except:
                pass
            counter += 1
            print(f"❌ Error: {e}")
            await browser.close()
            return

        rows = page.locator("table tbody tr")
        count = await rows.count()
        print(f"✓ Found {count} dividend entries\n")

        # ===== CRITICAL: Extract ALL table data FIRST before navigating =====
        table_data = []
        for i in range(count):
            try:
                cells = rows.nth(i).locator("td")
                
                # Get all cell values with await
                code = await cells.nth(0).inner_text()
                company = await cells.nth(1).inner_text()
                ex_date_raw = await cells.nth(3).inner_text()
                amount_raw = await cells.nth(4).inner_text()
                franking_raw = await cells.nth(5).inner_text()
                pay_date_raw = await cells.nth(7).inner_text()
                yield_raw = await cells.nth(8).inner_text()
                
                # Clean and validate
                amount_val = clean_to_number(amount_raw.strip())
                
                # Skip if amount is zero or invalid
                if amount_val is None or amount_val == 0:
                    continue
                
                table_data.append({
                    'code': code.strip(),
                    'company': company.strip(),
                    'ex_date': parse_international_date(ex_date_raw.strip()),
                    'amount': amount_val,
                    'franking': clean_percent_to_decimal(franking_raw.strip()),
                    'pay_date': parse_international_date(pay_date_raw.strip()),
                    'yield': clean_percent_to_decimal(yield_raw.strip())
                })
            except Exception as e:
                print(f"⚠️  Skipping row {i}: {e}")
                continue
        
        print(f"✓ Extracted {len(table_data)} valid entries from table\n")

        # ===== WARMUP: Visit first stock page to establish session =====
        if table_data:
            print("🔥 Warming up session with first stock...")
            warmup_code = table_data[0]['code']
            warmup_url = ASX_URL.format(warmup_code.lower())
            
            await page.goto(warmup_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # Check if Cloudflare appears on stock pages
            title = await page.title()
            if "Just a moment" in title or "Checking your browser" in title:
                print("⚠️  Cloudflare detected on stock pages too!")
                print("💡 Please solve it manually, then press Enter...")
                input()
                await asyncio.sleep(3)
            
            print(f"✓ Session warmed up successfully!\n")
            
            # Go back to main page
            await page.goto(UPCOMING_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)

        # ===== Now navigate to detail pages using SAME page object =====
        for idx, data in enumerate(table_data):
            try:
                code = data['code']
                print(f"[{idx+1}/{len(table_data)}] Processing {code}...", end=" ")
                
                # Navigate to detail page (maintains Cloudflare cookies)
                detail_url = ASX_URL.format(code.lower())
                
                # Add longer delay to avoid rate limiting
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                
                # Check for Cloudflare on detail page
                title = await page.title()
                if "Just a moment" in title or "Checking your browser" in title:
                    print(f"\n⚠️  Cloudflare challenge on {code} page")
                    print("💡 Solve it manually and press Enter...")
                    input()
                    await asyncio.sleep(2)
                
                # Wait for the price data to load
                try:
                    await page.wait_for_selector("span[data-quoteapi='price']", timeout=10000)
                except:
                    print("⚠️  Price element not found, retrying...")
                    await asyncio.sleep(3)
                
                # Get volume and price
                vol_str = await get_element_text_with_retry(page, "span[data-quoteapi*='monthAverageVolume']")
                price_str = await get_element_text_with_retry(page, "span[data-quoteapi='price']")

                vol_num = clean_to_number(vol_str)
                price_num = clean_to_number(price_str)
                total_value = vol_num * price_num if vol_num and price_num else None

                print(f"✓ Price=${price_num}, Volume={vol_num}, Value=${total_value}")

                results.append({
                    "Code": code,
                    "Company": data['company'],
                    "Ex Date": data['ex_date'],
                    "Amount": data['amount'],
                    "Franking": data['franking'],
                    "Pay Date": data['pay_date'],
                    "Yield": data['yield'],
                    "Price": price_num,
                    "4W Volume": vol_num,
                    "Total Value": total_value
                })

            except Exception as e:
                screenshot_path = os.path.join(DEBUG_DIR, f"error_{counter}.png")
                counter += 1
                try:
                    await page.screenshot(path=screenshot_path)
                    print(f"❌ Error: {e} (screenshot: {screenshot_path})")
                except:
                    print(f"❌ Error: {e}")
                continue

        await browser.close()

    if results:
        df = pd.DataFrame(results)
        output = "asx_dividends_machine_ready.csv"
        df.to_csv(output, index=False, encoding='utf-8-sig')
        print(f"\n✅ Thành công! File '{output}' đã tạo với {len(results)} entries.")
        print(f"\n📊 Preview:")
        print(df[['Code', 'Company', 'Amount', 'Price', 'Total Value']].head(10))
    else:
        print("\n❌ Không có kết quả nào được thu thập.")

if __name__ == "__main__":
    asyncio.run(main())