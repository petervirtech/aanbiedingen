#!/usr/bin/env python3
"""
Jumbo Web Scraper using Obscura (Rust-based headless browser).

Replaces jumbo_scraper.py with a much lighter browser alternative.
Requires the `obscura` CLI binary on PATH (see: https://github.com/h4ckf0r0day/obscura).

Advantages over Playwright:
  - ~30MB memory vs 200MB+ for Chrome
  - 85ms page load vs ~500ms
  - Built-in stealth mode (anti-detection, tracker blocking)
  - No Chromium/Node.js dependency
"""

import subprocess
import json
import re
import shutil
import sys


def obscura_available() -> bool:
    """Check if the obscura binary is on PATH."""
    return shutil.which("obscura") is not None


def fetch_jumbo_products(query: str = "") -> list[dict]:
    """
    Haal Jumbo producten en prijzen op via Obscura CLI.

    Haalt productnaam, prijs, hoeveelheid, link en image uit de HTML.
    """
    if not obscura_available():
        return []  # Fallback: no products (scraper unavailable)

    try:
        # Fetch Jumbo producten page with Obscura
        cmd = [
            "obscura",
            "fetch",
            "https://www.jumbo.com/producten",
            "--dump", "html",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return []

        html = result.stdout
        body = _extract_body_text(html)
        return _parse_jumbo_html(html, body, query)

    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def _extract_body_text(html: str) -> str:
    """Extract text from <body> tag in HTML string."""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_html = body_match.group(1)
        text = re.sub(r'<[^>]+>', ' ', body_html)
        return ' '.join(text.split())
    return ""


def _parse_jumbo_html(html: str, body: str, query: str = "") -> list[dict]:
    """Parse Jumbo HTML (same regex logic as Playwright scraper)."""
    products = []

    # Product links
    product_links = []
    for m in re.findall(
        r'href="(/product/[a-zA-Z0-9-/]+(?:/[a-zA-Z0-9-/]*)?)"',
        html, re.IGNORECASE
    ):
        if any(skip in m for skip in ['home', 'about', 'privacy', 'contact']):
            continue
        product_links.append(m)

    # Product images (src or srcset)
    product_images = []
    for m in re.findall(
        r'<img[^>]*(?:src|data-src)="(https?://[^"]*product[^"]*\.(?:jpg|webp|png))"',
        html, re.IGNORECASE
    ):
        product_images.append(m)

    # Unieke images
    seen = set()
    unique_images = []
    for img in product_images:
        if img not in seen:
            seen.add(img)
            unique_images.append(img)

    # Parse producten uit body text (same as Playwright version)
    blocks = re.split(r'\nPrijs:\s*€\s*', body)

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

    for block in blocks[1:]:
        lines = block.strip().split('\n')
        name_parts = []

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
            if len(name) > 200:
                continue
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

                if unique_images:
                    product["image"] = unique_images.pop(0)
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

    return products


def _extract_amount(name: str):
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


def main():
    """Standalone test."""
    print("=== Jumbo Scraper (Obscura) ===\n")

    if not obscura_available():
        print("⚠️  Obscura binary not found on PATH.")
        print("   Download from: https://github.com/h4ckf0r0day/obscura/releases")
        print("   Place in ~/bin/ or add to PATH.")
        sys.exit(1)

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


if __name__ == "__main__":
    main()
