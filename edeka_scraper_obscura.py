#!/usr/bin/env python3
"""
EDEKA Scraper using Obscura (Rust-based headless browser).

Replaces edeka_scraper.py with a much lighter browser alternative.
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


def fetch_edeka_offers(query: str = "", market_url: str = "https://www.edeka.de/") -> list[dict]:
    """
    Haal huidige EDEKA aanbiedingen op via Obscura CLI.

    Args:
        query: Optionele zoekterm (wordt gefilterd na ophalen)
        market_url: URL van EDEKA markt pagina (standaard: hoofdpagina)

    Returns:
        Lijst van dicts met producten (standaard formaat)
    """
    if not obscura_available():
        return []  # Fallback: no products (scraper unavailable)

    try:
        # Fetch the EDEKA offers page with Obscura
        cmd = [
            "obscura",
            "fetch",
            market_url,
            "--dump", "html",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return []

        html = result.stdout
        return _parse_edeka_html(html, query)

    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def _parse_edeka_html(html: str, query: str = "") -> list[dict]:
    """Parse EDEKA HTML (same regex logic as Playwright scraper)."""
    products = []

    # Extract body text from HTML
    body = _extract_body_text(html)

    # Methode 1: "Angebot:" blokken parsen (same as Playwright version)
    blocks = re.split(r'Angebot:\s*\n', body)

    for block in blocks[1:]:
        lines = block.strip().split('\n')
        name = lines[0].strip() if len(lines) > 0 else ""

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

            price_match = re.match(r'^([\d.,]+)$', line)
            if price_match and price is None:
                price = float(line.replace(',', '.'))
                continue

            festpreis = re.search(r'Festpreis von ([\d.,]+)€', line)
            if festpreis:
                price = float(festpreis.group(1).replace(',', '.'))
                continue

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

            apppreis = re.search(r'App Preis von ([\d.,]+)€', line)
            if apppreis:
                price = float(apppreis.group(1).replace(',', '.'))
                continue

        desc_parts = []
        for line in lines:
            line = line.strip()
            if line and not re.match(r'^[\d.,]+$', line) and 'Preis' not in line:
                if line and line not in ['Gültig vom', 'Wähle']:
                    desc_parts.append(line)

        desc = ' '.join(desc_parts)[:80] if desc_parts else ""

        if price:
            products.append({
                "name": name,
                "price": price,
                "normal_price": normal_price,
                "discount": discount,
                "amount": desc.split(",")[0] if desc else "",
                "description": desc,
            })

    # Fallback: prijs patronen
    if not products:
        products = _parse_price_patterns(body)

    # Filter op query
    if query:
        query_lower = query.lower()
        products = [p for p in products
                    if query_lower in p["name"].lower()
                    or query_lower in p.get("description", "").lower()]

    return products


def _extract_body_text(html: str) -> str:
    """Extract text from <body> tag in HTML string."""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_html = body_match.group(1)
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', body_html)
        return ' '.join(text.split())  # Normalize whitespace
    return ""


def _parse_price_patterns(body: str) -> list[dict]:
    """Fallback: parse 'Prijs: € X,XX' patronen uit body tekst (same as Playwright)."""
    products = []
    blocks = re.split(r'€\s*([\d.,]+)', body)

    for i in range(1, len(blocks), 2):
        price = float(blocks[i].replace(',', '.'))
        name = blocks[i-1].strip()

        skip_words = {'Gültig', 'Wähle', 'Markt'}
        if len(name) < 5 or any(sw in name for sw in skip_words):
            continue

        products.append({
            "name": name.strip(),
            "price": price,
        })

    return products


def main():
    """Standalone test."""
    print("=== EDEKA Scraper (Obscura) ===\n")

    if not obscura_available():
        print("⚠️  Obscura binary not found on PATH.")
        print("   Download from: https://github.com/h4ckf0r0day/obscura/releases")
        print("   Place in ~/bin/ or add to PATH.")
        sys.exit(1)

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


if __name__ == "__main__":
    main()
