# Market Data Automated
This is a Docker image for ETF's csv conversion for personal analytical purpose

# Packages 
- pandas
- playwright

# How to install
## 1. Create .venv
```
    python3 -m venv venv
```
- or 
```
    python -m venv venv 
```

- Enter the venv:
Mac 
```
    source venv/bin/activate
```
Win:
```
    venv\Scripts\activate
```

## 2. Install dependencies
```
    pip install -r requirements.txt
```

## 3. Create .env file
- Login to Firecrawl: https://www.firecrawl.dev/app
- Create .env file with variables:
    + "FIRECRAWL_API"
- And paste your API key in

## 4. Run the code
```
    python logic.py
```