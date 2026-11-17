#!/usr/bin/env python3
"""
Jumbo Web Scraper -- Haalt producten en prijzen op van Jumbo.com.

De SupermarktConnector API (jumbo.mobileapi) is down -- geen connectie mogelijk.
We scrappen via Playwright en parsen de HTML body tekst direct.
"""

from playwright.sync_api import sync_playwright
import re


def fetch_jumbo_products(query=""):
    """
    Haal Jumbo producten en prijzen op via web scraping.
    
    Haalt productnaam, prijs, hoeveelheid, link en image uit de HTML.
    """
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            page.goto('https://www.jumbo.com/producten', 
                      wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(5000)
            
            html = page.content()
            body = page.inner_text('body')
            
            # ---- Haal ALLE product links en images op uit HTML ----
            product_links = []
            for m in re.findall(
                r'href="(/product/[a-zA-Z0-9-/]+(?:/[a-zA-Z0-9-/]*)?)"',
                html, re.IGNORECASE
            ):
                # Filter out non-product pages
                if any(skip in m for skip in ['home', 'about', 'privacy', 'contact']):
                    continue
                product_links.append(m)
            
            # Haal ALLE product images op (via src of srcset)
            product_images = []
            for m in re.findall(
                r'<img[^>]*(?:src|data-src)="(https?://[^"]*product[^"]*\.(?:jpg|webp|png))"',
                html, re.IGNORECASE
            ):
                product_images.append(m)
            
            # Unieke images (als duplicates via srcset)
            seen = set()
            unique_images = []
            for img in product_images:
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            
            # ---- Parse producten uit body text ----
            blocks = re.split(r'\nPrijs:\s*€\s*', body)
            
            for block in blocks[1:]:  # Skip navigatie
                lines = block.strip().split('\n')
                name_parts = []
                skip_words = {
                    'Gültig', 'Wähle', 'Markt', 'Geschenk',
                    'Ga naar', 'hoofdinhoud', 'Lekker eten', 'toepen',
                    'Cookies', 'Sluiten', 'Banner', 'Volgende', 'Help',
                    'Vraag', 'Klacht', 'Feedback', 'Tips', 'Nieuwsbrief',
                    'Recepten', 'Folder', 'Aanbiedingen', 'Duurzame',
                    'Pompoen', 'Stamppot', 'Stoofpot', 'Pizzarette',
                    'Gourmet', 'Jaarverslag', 'Leveranciers', 'Terugroep',
                    'Werken', 'België', 'Herroep', 'Download', 'App',
                    'Voorwaarden', 'Privacy', 'Toegankelijkheids',
                    'Kwetsbaarheid', 'Maest', 'Visa', 'Vpay',
                    'American', 'Apple', 'Aanbieders', 'Thuiswinkel',
                    '25 jaar', 'BEMIDDELD', 'NIX', '© 2026',
                    'Wij en', 'Partnerlijst', 'Alle',
                    'Algemene', 'Kwetsbaarheid', 'Cookies', 'Privacy',
                    'We helpen', 'Heb je', 'veelgestelde', 'Neem',
                    'Vragen', 'Tip!', 'Inspire', 'Recept', 'Wat',
                    'Eten', 'Boodschappen', 'Openingstijden',
                    'Bedrijf', 'Verslag', 'Pers', 'Medicijnen',
                    'Waarborg', '18 jaar', '25 jaar'
                }
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if any(sw in line for sw in skip_words):
                        continue
                    if re.match(r'^€?\s*[\d.,]+', line):
                        continue
                    if re.match(r'^per\s', line, re.IGNORECASE):
                        continue
                    name_parts.append(line)
                
                if name_parts:
                    name = re.sub(r'\s+', ' ', ' '.join(name_parts)).strip()
                    if len(name) < 3:
                        continue
                    # Filter lange/ongeldige namen (vaak footer/SEO tekst)
                    if len(name) > 200:
                        continue
                    # Skip productnamen die veel skip woorden bevatten
                    name_lower = name.lower()
                    if any(sw.lower() in name_lower for sw in skip_words):
                        continue
                    
                    price_match = re.search(r'([\d.,]+)', block)
                    if price_match:
                        price = float(price_match.group(1).replace(',', '.'))
                        
                        product = {
                            "name": name,
                            "price": price,
                            "amount": _extract_amount(name),
                        }
                        
                        # Koppel image en link aan product (als beide beschikbaar)
                        if product_images:
                            product["image"] = product_images.pop(0)
                        if product_links:
                            link = product_links.pop(0)
                            if not link.startswith('http'):
                                link = f"https://www.jumbo.com{link}"
                            product["link"] = link
                        
                        products.append(product)
            
            # Filter op query
            if query:
                query_lower = query.lower()
                products = [p for p in products 
                           if query_lower in p["name"].lower()]
            
        finally:
            browser.close()
    
    return products


def _extract_amount(name):
    """Probeer een hoeveelheid te extraheren uit de productnaam."""
    patterns = [
        r'(\d+[,\.]?\d*\s*(?:liter|liters|l|cl|ml))',
        r'(\d+[,\.]?\d*\s*(?:gram|kg))',
        r'(\d+\s*x\s*\d+[,\.]?\d*\s*(?:ml|liter|l))',
    ]
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


if __name__ == "__main__":
    print("=== Jumbo Web Scraper (Verbeterd) ===\n")
    
    products = fetch_jumbo_products()
    print(f"{len(products)} producten gevonden:\n")
    
    for i, p in enumerate(products[:30]):
        print(f"{i+1}. {p['name']}")
        print(f"   Prijs: EUR{p['price']:.2f}")
        if p.get('amount'):
            print(f"   Hoeveelheid: {p['amount']}")
        if p.get('link'):
            print(f"   Link: {p['link']}")
        if p.get('image'):
            print(f"   Image: {p['image'][:70]}...")
        print()
