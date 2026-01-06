import sys
import random
import time
import pandas as pd
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import io
from datetime import datetime
import os

# Fix encoding cho Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

UPCOMING_URL = "https://www.marketindex.com.au/upcoming-dividends"
ASX_URL = "https://www.marketindex.com.au/asx/{}"
USER_DATA_DIR = "/Users/ducminhyologmail.com/Library/Application Support/BraveSoftware/Brave-Browser/Default"
DEBUG_DIR = "./debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

BRAVE_BROWSER = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

def parse_international_date(date_str):
    """Chuyển đổi các định dạng ngày sang YYYY-MM-DD."""
    if not date_str or date_str == "N/A":
        return "N/A"
    
    current_year = datetime.now().year
    try:
        # Thử định dạng: 29 Dec 2025 hoặc 9 Jan 2026
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            # Thử định dạng không có năm: 29 Dec (tự hiểu là năm hiện tại)
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
                raw_val = await page.locator(selector).first.inner_text().strip()
                if raw_val and raw_val not in ['\u2010', '-', '']:
                    return raw_val
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
        # context = p.chromium.launch_persistent_context(
        #     user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", 
        #     args=["--disable-blink-features=AutomationControlled"]
        # )
        stealth = Stealth()
        await stealth.apply_stealth_async(browser)
        page = await browser.new_page()
        
        try:
            await page.goto(UPCOMING_URL, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_selector("table tbody tr", timeout=90000)
        except Exception as e:
            screenshot_path = os.path.join(DEBUG_DIR, f"page_error_{counter}.png")
            await page.screenshot(path=screenshot_path)
            counter += 1

            print(f"Lỗi: {e}")
            await browser.close()
            return

        rows = page.locator("table tbody tr")
        count = await rows.count()
        detail_page = await browser.new_page()

        counter = 0

        for i in range(count):
            try:
                cells = await rows.nth(i).locator("td")
                code = await cells.nth(0).inner_text().strip()
                
                # Kiểm tra Amount trước để lọc
                amount_raw = await cells.nth(4).inner_text().strip()
                amount_val = clean_to_number(amount_raw)
                
                if amount_val is None or amount_val == 0:
                    continue

                # Lấy các thông tin khác từ bảng
                company = await cells.nth(1).inner_text().strip()
                ex_date = parse_international_date(cells.nth(3).inner_text().strip())
                franking = clean_percent_to_decimal(cells.nth(5).inner_text().strip())
                pay_date = parse_international_date(cells.nth(7).inner_text().strip())
                yield_val = clean_percent_to_decimal(cells.nth(8).inner_text().strip())

                # Vào trang chi tiết lấy Volume và Price
                await detail_page.goto(ASX_URL.format(code.lower()), wait_until="domcontentloaded")
                vol_str = await get_element_text_with_retry(detail_page, "span[data-quoteapi*='monthAverageVolume']")
                price_str = await get_element_text_with_retry(detail_page, "span[data-quoteapi='price']")

                vol_num = clean_to_number(vol_str)
                price_num = clean_to_number(price_str)
                total_value = vol_num * price_num if vol_num and price_num else None

                print(f"[{i+1}] {code}: Amount={amount_val}, Value={total_value}")

                results.append({
                    "Code": code,
                    "Company": company,
                    "Ex Date": ex_date,
                    "Amount": amount_val,
                    "Franking": franking,
                    "Pay Date": pay_date,
                    "Yield": yield_val,
                    "Price": price_num,
                    "4W Volume": vol_num,
                    "Total Value": total_value
                })
                await asyncio.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                screenshot_path = os.path.join(DEBUG_DIR, f"error_{counter}.png")
                counter += 1
                await detail_page.screenshot(path=screenshot_path)
                print(f"Bỏ qua dòng {i}: {e}")
                continue

        await browser.close()

    if results:
        df = pd.DataFrame(results)
        # Lưu file
        output = "asx_dividends_machine_ready.csv"
        df.to_csv(output, index=False, encoding='utf-8-sig')
        print(f"\nThành công! File '{output}' đã sẵn sàng cho máy đọc.")

asyncio.run(main())