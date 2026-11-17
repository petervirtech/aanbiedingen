#!/usr/bin/env python3
"""
EDEKA Web Scraper -- Haalt aanbiedingen op van de EDEKA website.
Gebruikt Playwright om de HTML pagina te renderen en aanbiedingen te parsen.

Deze aanpak werkt omdat:
1. De EDEKA website de folder data direct in de HTML injecteert
2. Geen API calls nodig -- alles staat al in de pagina broncode
3. Werkt buiten Duitsland -- alleen Cloudflare blokkeert headless browsers
"""

from playwright.sync_api import sync_playwright
import re


def fetch_edeka_offers(query="", market_url="https://www.edeka.de/"):
    """
    Haal huidige EDEKA aanbiedingen op door de website te scrappen.
    
    Args:
        query: Optionele zoekterm (wordt gefilterd na ophalen)
        market_url: URL van EDEKA markt pagina (standaard: hoofdpagina)
    
    Returns:
        List van dicts met producten (standaard formaat)
    """
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Eerst hoofdpagina bezoeken (zoals een echte gebruiker)
            page.goto(market_url, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(3000)
            
            # Klik op "Angebote" link (zoals een gebruiker zou doen)
            angebote_link = page.query_selector('a[href="/angebote/"]')
            if angebote_link:
                page.goto(f"https://www.edeka.de{angebote_link.get_attribute('href')}", 
                          wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(5000)
            
            body = page.inner_text('body')
            
            # ---- Methode 1: "Angebot:" blokken parsen ----
            blocks = re.split(r'Angebot:\s*\n', body)
            
            for block in blocks[1:]:
                lines = block.strip().split('\n')
                name = lines[0].strip() if len(lines) > 0 else ""
                
                # Filter niet-product items
                skip_words = ['Gültig', 'Wähle', 'Markt', 'Geschenk', 
                              'Klicken', 'Schließen', 'Banner']
                if not name or any(sw in name for sw in skip_words):
                    continue
                
                price = None
                normal_price = None
                discount = ""
                amount = ""
                
                for line in lines:
                    line = line.strip()
                    
                    # Zuivere prijs (getal met komma/punt)
                    price_match = re.match(r'^([\d.,]+)$', line)
                    if price_match and price is None:
                        price = float(line.replace(',', '.'))
                        continue
                    
                    # Festpreis von X€
                    festpreis = re.search(r'Festpreis von ([\d.,]+)€', line)
                    if festpreis:
                        price = float(festpreis.group(1).replace(',', '.'))
                        continue
                    
                    # Rabattierter Preis
                    rabattiert = re.search(r'Rabattierter Preis von ([\d.,]+)€', line)
                    if rabattiert:
                        price = float(rabattiert.group(1).replace(',', '.'))
                        normal_match = re.search(r'durchschnittl\. Normalpreis: € ([\d.,]+)', line)
                        if normal_match:
                            normal_price = float(normal_match.group(1).replace(',', '.'))
                        discount_match = re.search(r'-(\d+)%', line)
                        if discount_match:
                            discount = f"-{discount_match.group(1)}%"
                        continue
                    
                    # App Preis
                    apppreis = re.search(r'App Preis von ([\d.,]+)€', line)
                    if apppreis:
                        price = float(apppreis.group(1).replace(',', '.'))
                        continue
                
                # Beschrijving extracten (voor amount/category)
                desc_parts = []
                for line in lines:
                    line = line.strip()
                    if line and not re.match(r'^[\d.,]+$', line) and 'Preis' not in line:
                        if line and line not in ['Gültig vom', 'Wähle']:
                            desc_parts.append(line)
                
                desc = ' '.join(desc_parts)[:80] if desc_parts else ""
                
                if price:  # Alleen producten met prijs
                    products.append({
                        "name": name,
                        "price": price,
                        "normal_price": normal_price,
                        "discount": discount,
                        "amount": desc.split(",")[0] if desc else "",
                        "description": desc,
                    })
            
            # ---- Methode 2: Fallback — prijs patronen ----
            if not products:
                products = _parse_price_patterns(body)
            
            # Filter op query
            if query:
                query_lower = query.lower()
                products = [p for p in products 
                           if query_lower in p["name"].lower() 
                           or query_lower in p.get("description", "").lower()]
            
        finally:
            browser.close()
    
    return products


def _parse_price_patterns(body):
    """Fallback: parse 'Prijs: € X,XX' patronen uit body tekst."""
    products = []
    blocks = re.split(r'€\s*([\d.,]+)', body)
    
    for i in range(1, len(blocks), 2):
        price = float(blocks[i].replace(',', '.'))
        name = blocks[i-1].strip()
        
        # Skip korte/ongeldige namen
        skip_words = {'Gültig', 'Wähle', 'Markt'}
        if len(name) < 5 or any(sw in name for sw in skip_words):
            continue
        
        products.append({
            "name": name.strip(),
            "price": price,
        })
    
    return products


if __name__ == "__main__":
    print("=== EDEKA Web Scraper ===\n")
    
    products = fetch_edeka_offers()
    print(f"{len(products)} aanbiedingen gevonden:\n")
    
    for i, p in enumerate(products):
        print(f"{i+1}. {p['name']}")
        if p['price']:
            print(f"   Prijs: EUR{p['price']:.2f}")
        if p['normal_price']:
            print(f"   Normaal: EUR{p['normal_price']:.2f}")
        if p['discount']:
            print(f"   Korting: {p['discount']}")
        if p.get('description'):
            print(f"   {p['description']}")
        print()
