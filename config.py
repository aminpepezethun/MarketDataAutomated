import os
from firecrawl import Firecrawl
from dotenv import load_dotenv

# Load .env 
load_dotenv()

# FIRECRAWL API
firecrawl_api = os.getenv("FIRECRAWL_API")
firecrawl = Firecrawl(api_key=firecrawl_api)