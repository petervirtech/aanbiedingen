#!/usr/bin/env python3
"""
Jumbo Web Scraper -- Haalt producten en prijzen op van Jumbo.com.

De SupermarktConnector API (jumbo.mobileapi) is down -- geen connectie mogelijk.
Maar: Jumbo.com injecteert alle product data in de HTML body tekst.
We scrappen via Playwright (browser simulator) om de data te halen.
"""

from playwright.sync_api import sync_playwright
import re


def fetch_jumbo_products(query=""):
    """
    Haal Jumbo producten en prijzen op via web scraping.
    
    Args:
        query: Optionele zoekterm (wordt gefilterd na ophalen)
    
    Returns:
        List van dicts met producten (standaard formaat)
    """
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            page.goto('https://www.jumbo.com/producten', 
                      wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(5000)
            
            body = page.inner_text('body')
            
            # Parse "Prijs: € X,XX" patronen
            # Productnaam = tekst vóór "Prijs: €"
            price_pattern = r'([A-Z][A-Za-z\säöüÄÖÜ\[\]-]{3,80})[\s\S]*?Prijs:\s*€\s*(\d+[,\.]?\d*)'
            
            matches = re.findall(price_pattern, body)
            for name, price_str in matches:
                price = float(price_str.replace(',', '.'))
                products.append({
                    "name": name.strip(),
                    "price": price,
                })
            
            # Filter op query
            if query:
                query_lower = query.lower()
                products = [p for p in products 
                           if query_lower in p["name"].lower()]
            
        finally:
            browser.close()
    
    return products


if __name__ == "__main__":
    print("=== Jumbo Web Scraper ===\n")
    
    products = fetch_jumbo_products()
    print(f"{len(products)} producten gevonden:\n")
    
    for i, p in enumerate(products):
        print(f"{i+1}. {p['name']}")
        print(f"   Prijs: EUR{p['price']:.2f}")
        print()
