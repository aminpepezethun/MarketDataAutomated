import sys
import random
import pandas as pd
import asyncio
from rebrowser_playwright.async_api import async_playwright
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
                print(f"  - {os.path.join(brave_base, item)}")
    sys.exit(1)

print(f"✓ Using Brave profile: {USER_DATA_DIR}")

DEBUG_DIR = "./debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

BRAVE_BROWSER = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"


def parse_international_date(date_str):
    if not date_str or date_str == "N/A":
        return "N/A"

    current_year = datetime.now().year
    try:
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(f"{date_str} {current_year}", "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            return date_str


def clean_to_number(text):
    if not text or text in ['\u2010', '-', 'N/A']:
        return None
    try:
        return float(text.replace(',', '').replace('$', '').replace('%', '').strip())
    except Exception:
        return None


def clean_percent_to_decimal(text):
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
        except Exception:
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
            channel="brave",
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            print(f"🌐 Loading {UPCOMING_URL}...")
            await page.goto(UPCOMING_URL, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(2)

            title = await page.title()
            print(f"📄 Page title: {title}")

            try:
                await page.screenshot(
                    path=os.path.join(DEBUG_DIR, "page_load.png"),
                    full_page=True
                )
            except Exception:
                pass

            if "Just a moment" in title or "Checking your browser" in title:
                print("\n⚠️ Cloudflare challenge detected!")
                print("💡 Solve it manually in the browser, then press Enter...")
                input()
                await asyncio.sleep(3)

            print("⏳ Waiting for table to load...")
            await page.wait_for_selector("table tbody tr", timeout=30000)
            print("✓ Table found!")

        except Exception as e:
            print(f"❌ Failed to load main page: {e}")
            await browser.close()
            return

        rows = page.locator("table tbody tr")
        count = await rows.count()
        print(f"✓ Found {count} dividend entries\n")

        table_data = []

        for i in range(count):
            try:
                cells = rows.nth(i).locator("td")

                code = await cells.nth(0).inner_text()
                company = await cells.nth(1).inner_text()
                ex_date_raw = await cells.nth(3).inner_text()
                amount_raw = await cells.nth(4).inner_text()
                franking_raw = await cells.nth(5).inner_text()
                pay_date_raw = await cells.nth(7).inner_text()
                yield_raw = await cells.nth(8).inner_text()

                amount_val = clean_to_number(amount_raw.strip())
                if amount_val is None or amount_val == 0:
                    continue

                table_data.append({
                    "code": code.strip(),
                    "company": company.strip(),
                    "ex_date": parse_international_date(ex_date_raw.strip()),
                    "amount": amount_val,
                    "franking": clean_percent_to_decimal(franking_raw.strip()),
                    "pay_date": parse_international_date(pay_date_raw.strip()),
                    "yield": clean_percent_to_decimal(yield_raw.strip())
                })

            except Exception:
                continue

        print(f"✓ Extracted {len(table_data)} valid entries\n")

        if table_data:
            warmup_code = table_data[0]["code"]
            await page.goto(
                ASX_URL.format(warmup_code.lower()),
                wait_until="domcontentloaded",
                timeout=30000
            )
            await asyncio.sleep(3)

            if "Just a moment" in await page.title():
                print("⚠️ Cloudflare detected again. Solve it and press Enter.")
                input()
                await asyncio.sleep(2)

            await page.goto(UPCOMING_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)

        for idx, data in enumerate(table_data):
            try:
                code = data["code"]
                print(f"[{idx+1}/{len(table_data)}] {code}...", end=" ")

                await asyncio.sleep(random.uniform(2.0, 4.0))
                await page.goto(
                    ASX_URL.format(code.lower()),
                    wait_until="domcontentloaded",
                    timeout=30000
                )

                if "Just a moment" in await page.title():
                    print("\n⚠️ Solve Cloudflare and press Enter")
                    input()
                    await asyncio.sleep(2)

                await page.wait_for_selector("span[data-quoteapi='price']", timeout=10000)

                vol_str = await get_element_text_with_retry(
                    page, "span[data-quoteapi*='monthAverageVolume']"
                )
                price_str = await get_element_text_with_retry(
                    page, "span[data-quoteapi='price']"
                )

                vol = clean_to_number(vol_str)
                price = clean_to_number(price_str)
                total_value = vol * price if vol and price else None

                print(f"✓ ${price} × {vol}")

                results.append({
                    "Code": code,
                    "Company": data["company"],
                    "Ex Date": data["ex_date"],
                    "Amount": data["amount"],
                    "Franking": data["franking"],
                    "Pay Date": data["pay_date"],
                    "Yield": data["yield"],
                    "Price": price,
                    "4W Volume": vol,
                    "Total Value": total_value
                })

            except Exception as e:
                print(f"❌ Error: {e}")
                counter += 1
                continue

        await browser.close()

    if results:
        df = pd.DataFrame(results)
        output = "asx_dividends_machine_ready.csv"
        df.to_csv(output, index=False, encoding="utf-8-sig")

        print(f"\n✅ Success! Saved {len(results)} rows to {output}")
        print(df[["Code", "Company", "Amount", "Price", "Total Value"]].head(10))
    else:
        print("\n❌ No data collected.")


if __name__ == "__main__":
    asyncio.run(main())
