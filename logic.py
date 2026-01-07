import os 
import pandas as pd
from dotenv import load_dotenv
from firecrawl import Firecrawl
from helper import clean_number

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
result = firecrawl.scrape(
    url = UD_URL,
    formats=['html'],
)

html = result.html
if not html:
    raise RuntimeError("No HTML found from Firecrawl")

# Save
output_path = os.path.join(TEST_FOLDER, "upcoming_dividends.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Completed saving to {output_path}")






