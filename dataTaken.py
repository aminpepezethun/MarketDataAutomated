import pandas as pd
from bs4 import BeautifulSoup
import os
from datetime import datetime
import sys
import io

# Fix encoding for Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def parse_date(date_str):
    if not date_str or date_str == "N/A":
        return "N/A"
    try:
        # Standard format for Market Index: 25 Jan 2026
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except:
        return date_str

def clean_to_number(text):
    if not text or text in ['-', 'N/A', '', '\u2010']:
        return None
    try:
        return float(text.replace('$', '').replace('%', '').replace(',', '').strip())
    except:
        return None

def process_data():
    html_file = "./test/upcoming_dividends.html"
    
    if not os.path.exists(html_file):
        print(f"Error: Could not find {html_file}. Run the scraper first.")
        return

    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Find the table containing dividend data
    table = None
    for t in soup.find_all("table"):
        if "Code" in t.get_text():
            table = t
            break
    
    if not table:
        print("Error: Could not find dividend table in the HTML file.")
        return

    results = []
    rows = table.find_all("tr")
    print(f"Analyzing {len(rows)} rows...")

    for row in rows:
        if row.find("th"): continue # Skip header row
            
        cells = row.find_all("td")
        if len(cells) < 5: continue 

        try:
            # Map columns based on Market Index structure
            code = cells[0].get_text(strip=True)
            company = cells[1].get_text(strip=True)
            ex_date = cells[3].get_text(strip=True)
            amount_raw = cells[4].get_text(strip=True)
            franking = cells[5].get_text(strip=True) if len(cells) > 5 else "N/A"
            pay_date = cells[7].get_text(strip=True) if len(cells) > 7 else "N/A"
            div_yield = cells[8].get_text(strip=True) if len(cells) > 8 else "N/A"

            amount = clean_to_number(amount_raw)
            
            # Filter: Only keep rows with a valid dividend amount > 0
            if amount and amount > 0:
                results.append({
                    "Code": code,
                    "Company": company,
                    "Ex Date": parse_date(ex_date),
                    "Amount": amount,
                    "Franking": franking,
                    "Pay Date": parse_date(pay_date),
                    "Yield": div_yield
                })
        except Exception as e:
            continue

    if results:
        df = pd.DataFrame(results)
        output_file = "asx_dividends_final.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Success: Extracted {len(results)} companies to '{output_file}'")
    else:
        print("Final Status: No data extracted. Check if the HTML file is valid.")

if __name__ == "__main__":
    process_data()