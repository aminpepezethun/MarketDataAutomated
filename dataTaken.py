from bs4 import BeautifulSoup
from datetime import datetime
from config import firecrawl
import pandas as pd
import os
import sys
import io

# Fix encoding for Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# URLs
WEB_URL = "https://www.marketindex.com.au/"
UD_URL = "https://www.marketindex.com.au/upcoming-dividends"
CODE_TEST_URL = "https://www.marketindex.com.au/asx/xgov"


TEST_DIR = './test'

def parse_date(date_str):
    """
    Docstring for parse_date
    
    :param date_str: 
    """
    if not date_str or date_str == "N/A":
        return "N/A"
    try:
        # Standard format for Market Index: 25 Jan 2026
        return datetime.strptime(date_str, "%d %b %Y").strftime("%Y-%m-%d")
    except:
        return date_str

def clean_to_number(text):
    """
    Docstring for clean_to_number
    
    :param text: clean raw string number from html object
    """
    if not text or text in ['-', 'N/A', '', '\u2010']:
        return None
    try:
        return float(text.replace('$', '').replace('%', '').replace(',', '').strip())
    except:
        return None
    
def scrape_html_ud(html_source, type="object") -> list:
    """
    Docstring for scrape_html_ud
        
        scrape_html_ud()
            Process at "https://www.marketindex.com.au/upcoming-dividends/" URL 
                -> returns a list of dict with key as the company's code and value as the information (Ex-Date, Amount, Franking, Pay Date, Yield, Price)
                else returns an empty dict

    :param html_source: HTML object produced by Firecrawl's API or 
    """

    """ 
        [!!!] ONLY USE type='file' IN TEST to reduce number of tokens being used
    """
    if type == "file":
        if isinstance(html_source, str) and os.path.exists(html_source):
            with open(html_source, "r", encoding="utf-8") as f:
                html_text = f.read()

    elif type == 'object':
        if isinstance(html_source, str) and "<html" in html_source.lower():
            html_text = html_source

    soup = BeautifulSoup(html_text, "html.parser")

    table = None
    for t in soup.find_all("table"):
        if "Code" in t.get_text():
            table = t
            break
    
    if not table:
        print("Error: Could not find dividend table in the HTML file.")
        return []
    
    big_table = []
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
                big_table.append({
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
    
    return big_table

def extract_price_volume_4w(html_source):
    """
    Docstring for extract_price_volume_4w

        Extracts Price, Volume, 4W Volume from code-specific html source

        Returns a dict:
            {
                "Price": float | None,
                "Volume": float | None,
                "4W Volume": float | None
            }
    :param html_source: Description
    """
    soup = BeautifulSoup(html_source, "html.parser")
    
    # Price
    price_el = soup.select_one("span[data-quoteapi='price']")

    # Volume
    vol_el   = soup.select_one("span[data-quoteapi^='volume']")
    vol4w_el = soup.select_one("span[data-quoteapi^='monthAverageVolume']")

    price = clean_to_number(price_el.get_text(strip=True)) if price_el else None
    vol   = clean_to_number(vol_el.get_text(strip=True)) if vol_el else None
    vol4w = clean_to_number(vol4w_el.get_text(strip=True)) if vol4w_el else None

    return {"Price": price, "Volume": vol, "4W Volume": vol4w}

def scrape_html_code(big_table, type='object'):
    """
    Docstring for scrape_html_code

        Scrape HTML file for individual 'marketingindex.com.au/{code}/' and update big_table with:
            Price, Volume, 4W Volume

    :param code: unique code of a company
    :param table: dictionary of the previous scrape_html_ud()
    """
    error_code = []

    # Iterate over the existing company's code
    for row in big_table:
        code = row.get("Code")
        if not code:
            continue
    
        code_l = code.lower()
        code_url = f"{WEB_URL}asx/{code_l}"

        object = firecrawl.scrape(
            url=code_url,
            formats=['html']
        )

        html_source = object['html']

        if not html_source:
            error_code.append(code_l)
        
        pvv = extract_price_volume_4w(html_source)

        # Add Price, Volumne, 4W Volume to big_table
        row.update(pvv)
        
    # Print Error (if existed)
    if error_code:
        print(f"[ERROR] There has been issued with {len(error_code)} codes: ")
        for error in error_code:
            print(f"Code {error} failed to extract from the URL")
    
    return big_table



def process_data():
    """
    Docstring for process_data

        scrape_html_ud()
            Process at /upcoming-dividends/ URL to /{code} URL
                -> returns a table dict with key as the company's code and value as the information (Ex-Date, Amount, Franking, Pay Date, Yield, Price)
                else returns an Error object if dict is empty
        
        scra()
        It saves a list of company's code inside a list
        Iterate over the list to scrape each code for the necessary columns and update the table with the information corresponding to each code (4W, Last (Price))
    
    :param html_file: HTML file object from Firecrawl
    """ 
    object = firecrawl.scrape(
        url = UD_URL,
        formats=['html']  
    )

    html_source_ud = object['html']
    big_table = scrape_html_ud(html_source_ud)
    if not big_table:
        print("[ERROR] Step 1 of process_data() failed to extract big table data")
        return

    completed_big_table = scrape_html_code(big_table)
    if completed_big_table == big_table:
        print("[ERROR] Step 2 of process_data() faield: there were error since no further data being added to big_table data")
        return

    return completed_big_table
    
def save_table_to_csv(big_table):
    """
    Docstring for save_table_to_csv
    
    :param big_table: big_table dict 
    """

    df = pd.DataFrame(big_table)
    df.to_csv("asx_dividends.csv", index=False, encoding='utf-8-sig')
    print(f"Saved {len(df)} rows to asx_dividends_final.csv")






# ------------------------------------------------------------------------------- #

# [!!!] TEST FUNCTION TO SAVE FORMAT FOR CODE-SPECIFIC HTML FILES
def save_test_html(html_source, code):
    os.makedirs(TEST_DIR, exist_ok=True)

    file_name = f"test_html_{code}.html"
    file_path = os.path.join(TEST_DIR, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_source)
    
    print(f"Successfully saved {file_name} to {TEST_DIR}")
