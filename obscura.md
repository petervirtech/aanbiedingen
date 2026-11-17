# Obscura — Lightweight Headless Browser voor Scraping

## Wat is Obscura?

**Obscura** is een headless browser engine geschreven in Rust, speciaal gebouwd voor web scraping en AI agent automatisering. Het is een lichtgewicht alternatief voor Chromium/Playwright met ingebouwde stealth (anti-detectie) functionaliteit.

📦 Repository: https://github.com/h4ckf0r0day/obscura

## Waarom Obscura boven Playwright/Chromium?

| Meting | Obscura | Headless Chrome |
|--------|---------|-----------------|
| Geheugengebruik | **30 MB** | 200+ MB |
| Binary grootte | **~70 MB** | 300+ MB |
| Anti-detectie | **Ingebouwd** | Geen |
| Pagina laadtijd | **85 ms** | ~500 ms |
| Starttijd | **Direct** | ~2 seconden |
| Puppeteer | **Ja** | Ja |
| Playwright | **Ja** | Ja |

## Installatie (macOS)

```bash
# Download de laatste release (ARM64 / Apple Silicon)
curl -LO https://github.com/h4ckf0r0day/obscura/releases/latest/download/obscura-aarch64-macos.tar.gz
tar xzf obscura-aarch64-macos.tar.gz

# Plaats binaries in PATH
mkdir -p ~/bin
cp obscura ~/bin/obscura
cp obscura-worker ~/bin/obscura-worker
```

Controleer of het werkt:

```bash
export PATH="$HOME/bin:$PATH"
obscura fetch https://example.com --dump text
```

## Gebruik in dit project

Dit project bevat twee Obscura scrapers die fungeren als lichtgewicht alternatieven voor de Playwright-versies:

| Plugin | Playwright versie | Obscura versie |
|--------|-------------------|-----------------|
| EDEKA | `edeka_scraper.py` | `edeka_scraper_obscura.py` |
| Jumbo | `jumbo_scraper.py` | `jumbo_scraper_obscura.py` |

### Automatische fallback

De Obscura scrapers controleren of de `obscura` binary op PATH staat. Wanneer niet beschikbaar, retourneren ze een lege lijst en valt het systeem automatisch terug op andere data bronnen (checkjebon cache, SupermarktConnector).

### Handmatig testen

```bash
# EDEKA scraper testen
python edeka_scraper_obscura.py

# Jumbo scraper testen
python jumbo_scraper_obscura.py

# Simpele pagina fetch
obscura fetch https://example.com --dump text

# JavaScript uitvoeren
obscura fetch https://example.com --eval "document.title"

# Parallell scrapen
obscura scrape url1 url2 url3 --eval "document.title" --format json
```

## CLI Referentie

### `fetch` — Eén pagina ophalen

```bash
# Tekst extraheren
obscura fetch https://example.com --dump text

# HTML ophalen
obscura fetch https://example.com --dump html

# Links extraheren
obscura fetch https://example.com --dump links

# JavaScript uitvoeren
obscura fetch https://example.com --eval "document.title"

# Screenshots
obscura fetch https://example.com --screenshot page.png
```

### `scrape` — Parallelle scrapen

```bash
obscura scrape https://site1.com https://site2.com --eval "document.title" --format json
```

### `serve` — CDP Server (voor Puppeteer/Playwright)

```bash
obscura serve --port 9222
```

## Stealth Mode (Anti-detectie)

Met `--stealth` krijgt Obscura:
- **Per-session fingerprint randomisatie** (GPU, scherm, canvas, audio, batterij)
- **Realistische `navigator.userAgentData`** (Chrome 145, high-entropy values)
- **`event.isTrusted = true`** voor verstuuriende events
- **Native function masking** (`Function.prototype.toString()` → `[native code]`)
- **`navigator.webdriver = false`**
- **Tracker blocking** (3.520 domeinen geblokkeerd)

```bash
obscura --stealth fetch https://example.com
obscura --stealth serve --port 9222
```

## Integratie in app.py

De Obsura scrapers integreren naadloos via het bestaande plugin systeem:

```python
# In app.py, plugin registratie:
def _fetch_edeka_obscura(query):
    from edeka_scraper_obscura import fetch_edeka_offers
    products = fetch_edeka_offers(query)
    if not products:  # Obscura niet beschikbaar
        from edeka_scraper import fetch_edeka_offers  # Fallback naar Playwright
        products = fetch_edeka_offers(query)
    return [{"supermarket": "EDEKA (Tübingen via Obscura)", "code": "edeka", "products": products}]

def _fetch_jumbo_obscura(query):
    from jumbo_scraper_obscura import fetch_jumbo_products
    products = fetch_jumbo_products(query)
    if not products:  # Fallback naar Playwright
        from jumbo_scraper import fetch_jumbo_products
        products = fetch_jumbo_products(query)
    return [{"supermarket": "Jumbo (via Obscura)", "code": "jumbo", "products": products}]
```

## Docker

Voor gebruik in Docker containers:

```bash
export OBSCURA_CDP_TOKEN="$(openssl rand -hex 32)"
docker run -d --name obscura -p 127.0.0.1:9222:9222 \
  -e OBSCURA_CDP_TOKEN \
  h4ckf0r0day/obscura
```

## Licentie

Apache 2.0 — vrij te gebruiken, te modificeren en te distribueren.
