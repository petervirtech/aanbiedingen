# 🛒 Aanbiedingen Vergelijken

> **Lokale supermarkt prijsvergelijker voor Nederland & Duitsland.** 106.000+ producten uit 12+ winkels — 100% lokaal, 0 cloud dependency.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Webapp-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-lightgray.svg)](https://www.sqlite.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Scraper-purple.svg)](https://playwright.dev/)
[![Obscura](https://img.shields.io/badge/Obscura-Headless%20Browser-darkred.svg)](https://github.com/h4ckf0r0day/obscura)
[![License](https://img.shields.io/badge/License-Private-%236e7681.svg)]()

---

## ✨ Snel Starten

### Met Playwright (standaard)

```bash
pip install flask requests playwright
playwright install chromium
python app.py
```

Open **http://localhost:9090** in je browser.

### Met Obscura (lichtgewicht alternatief)

```bash
# Download Obscura binary — zie [obscura.md](obscura.md)
pip install flask requests
python app.py
```

> **Let op:** De Obscura scrapers vallen automatisch terug op Playwright als de binary niet beschikbaar is.

---

## 🚀 Features

| Feature | Details |
|---------|---------|
| **📊 12+ Winkels** | AH, Aldi, Jumbo, Plus, Dirk, Coop, SPAR, Vomar, Picnic, Hoogvliet, Jan Linders, DekaMarkt |
| **💾 Lokale DB** | SQLite database met ~106.000 producten — je data blijft op je computer |
| **🔍 Slim zoeken** | Fuzzy matching, woord-niveau prioriteit, filters per winkel |
| **📈 Prijsvergelijking** | Vergelijk prijzen tussen winkels, met eenheid-normalisatie (per liter, kg, stuk) |
| **📉 Prijsgeschiedenis** | 30-dagen rolling history per product |
| **🖼️ Image caching** | Productafbeeldingen lokaal opgeslagen |
| **🔌 Plugin-systeem** | Voeg nieuwe winkels toe met `register_store(code, name, fetch_func)` |
| **📱 Responsive** | Werkt op desktop en mobiel |
| **🛡️ Stealth scraping** | Built-in anti-detectie via Obscura (3.520+ geblokkeerde trackers) |

---

## 🏪 Beschikbare Winkels

### ✅ Cacakheerd via checkjebon

| Winkel | Status | Data bron |
|--------|--------|-----------|
| 🟢 **Albert Heijn** | Gecached | checkjebon |
| 🟢 **Aldi** | Gecached | checkjebon |
| 🟢 **Jumbo** | Cached + Live scraping | checkjebon + Obscura / Playwright |
| 🟢 **Plus** | Gecached | checkjebon |
| 🟢 **Dirk** | Gecached | checkjebon |
| 🟢 **Coop** | Gecached | checkjebon |
| 🟢 **SPAR** | Gecached | checkjebon |
| 🟢 **Vomar** | Gecached | checkjebon |
| 🟢 **Picnic** | Gecached | checkjebon |
| 🟢 **Hoogvliet** | Gecached | checkjebon |
| 🟢 **Jan Linders** | Gecached | checkjebon |
| 🟢 **DekaMarkt** | Gecached | checkjebon |
| 🟢 **EDEKA** | Live scraping | Obscura / Playwright (Tübingen) |

### 📡 Data bronnen

| Bron | Beschrijving | Winkels |
|------|-------------|---------|
| **checkjebon** | Offline dataset, handmatig bijgewerkt | 12+ Nederlandse winkels |
| **Playwright** | Headless Chromium, browser automation | Jumbo, EDEKA |
| **Obscura** | Rust-based headless browser, stealth mode | Jumbo, EDEKA (optioneel) |

---

## 📁 Projectstructuur

```
aanbiedingen/
├── app.py                    # Flask webapp — routes, DB, plugin systeem
├── edeka_scraper.py          # EDEKA scraper (Playwright fallback)
├── edeka_scraper_obscura.py  # EDEKA scraper (Obscura, met Playwright fallback)
├── jumbo_scraper.py          # Jumbo scraper (Playwright fallback)
├── jumbo_scraper_obscura.py  # Jumbo scraper (Obscura, met Playwright fallback)
├── obscura.md                # Installatie & CLI referentie
├── TODO.md                   # Takenplan
├── README.md                 # Dit bestand
│
├── data/
│   ├── aanbiedingen.db       # SQLite (~30 MB, ~106k producten)
│   └── product-images/       # Gecachte afbeeldingen
│
├── templates/
│   ├── base.html             # Hoofd sjabloon
│   ├── index.html            # Zoekpagina
│   ├── compare.html          # Prijsvergelijking
│   ├── history.html          # Geschiedenis overzicht
│   ├── stores.html           # Winkels info
│   ├── product.html          # Product detail + prijsverloop
│   └── 404.html              # Foutpagina
│
└── static/css/
    └── style.css             # Responsive styling
```

---

## 🔌 Eigen plugin toevoegen

```python
# Voorbeeld: een nieuwe winkel toevoegen

def fetch_jouw_winkel(query):
    """Haal producten op van jouw favoriete winkel."""
    # Retourneer producten in standaard formaat:
    return [{
        "supermarket": "Jouw Winkel",
        "code": "jouwcode",
        "products": [
            {"name": "Product Naam", "price": 1.99, "amount": "500g"},
        ]
    }]

# Registreer de plugin
register_store("jouwcode", "Jouw Winkel", fetch_jouw_winkel)
```

---

## ⚙️ Tech Stack

| Laag | Technologie |
|------|-------------|
| **Backend** | Python 3.11+ met Flask |
| **Database** | SQLite (lokaal, ~30 MB) |
| **Scraping** | Playwright (Chromium) + **Obscura** (Rust-based, stealth) |
| **Frontend** | Vanilla HTML templates + CSS |

---

## 📖 Documentatie

- **[Installatie gids](obscura.md)** — Obscura installatie, CLI referentie, stealth mode
- **[Takenplan](TODO.md)** — In ontwikkeling en te doen taken
- **[Workflow](my-workflow.md)** — Complete project workflow en tooling

---

## 🤝 Bijdragen

Dit project is gebouwd voor lokaal gebruik. Nieuwe winkels toevoegen via het plugin-systeem is welkom.

---
