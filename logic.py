import os 
import pandas as pd
from dotenv import load_dotenv
from firecrawl import Firecrawl
from dataTaken import process_data

# Load .env 
load_dotenv()

# URLs
WEBSITE_URL = "https://www.marketindex.com.au/"
UD_URL = "https://www.marketindex.com.au/upcoming-dividends"


# FIRECRAWL API
firecrawl_api = os.getenv("FIRECRAWL_API")
firecrawl = Firecrawl(api_key=firecrawl_api)

# Output folder
TEST_FOLDER = "./test"
os.makedirs(TEST_FOLDER, exist_ok=True)

# Main
def main():
    result = firecrawl.scrape(
        url = UD_URL,
        formats=['html'],
    )

    # HTML object
    html = result.html
    if not html:
        raise RuntimeError("No HTML found from Firecrawl")
    
    # Process data 
    table = process_data(html)
    if not table:
        print("Error! No table found.")
        return
    
    # Turn table (dict) into csv
    dp = pd.DataFrame(table)

    # Save
    output_path = os.path.join(TEST_FOLDER, f"upcoming_dividends.html")
    dp.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Completed saving to {output_path}")

    
    """
        Process directly?
            - Use HTML object to locate?
        
        Process by saving files?
        
        upcoming_dividend_url():
            - Code
            - Company
            - Ex-Date
            - Amount
            - Franking
            - Pay Date
            - Yield
            - Price
        
        company_specific_url():
            - 4W Volume
            - Volume
            - Last (Price)

            - Total Volume = 4W Volume * Last (Price)
        
            
        Error class for logging error:
            - Error at upcoming_dividend_url() not returning any table
    """


