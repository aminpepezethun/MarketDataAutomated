import pandas as pd
from bs4 import BeautifulSoup
import os
from datetime import datetime
import sys
import io

# Fix encoding for Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

URL = "https://www.marketindex.com.au/"

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
    
def scrape_html_ud(html_source) -> list:
    """
    Docstring for scrape_html_ud
        
        scrape_html_ud()
            Process at "https://www.marketindex.com.au/upcoming-dividends/" URL 
                -> returns a list of dict with key as the company's code and value as the information (Ex-Date, Amount, Franking, Pay Date, Yield, Price)
                else returns an empty dict

    :param html_source: HTML object produced by Firecrawl's API
    """
    with open(html_source, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

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
    
    print(big_table)
    return big_table

def scrape_html_code(html_source):
    """
    Docstring for scrape_html_code

        Scrape HTML file for individual 'marketingindex.com.au/{code}/'
    
    :param html_source: Description
    """


def complete_table(table: dict):
    codes = list(table.keys())

    # Iterate over the existing company's code
    for code in codes:
        new_url = URL + code

        scrape_html_code()

        print(new_url)

    return


def process_data_(html_source):
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

    # scrape_html_ud()
    companies = scrape_html_ud(html_source)

    for i in range(len(companies)):
        return
    
    

    # if results:
    #     df = pd.DataFrame(results)
    #     output_file = "asx_dividends_final.csv"
    #     df.to_csv(output_file, index=False, encoding='utf-8-sig')
    #     print(f"Success: Extracted {len(results)} companies to '{output_file}'")
    # else:
    #     print("Final Status: No data extracted. Check if the HTML file is valid.")

scrape_html_ud(os.path.join("./test/upcoming_dividends.html"))