# 🛒 Aanbiedingen Vergelijken

Webapp om supermarkt aanbiedingen te vergelijken — lokaal op je computer.

## ⚡ Snel Starten

```bash
pip install flask requests playwright
playwright install chromium
python app.py
# Open http://localhost:9090
```

## 📦 Features

- **12+ winkels** gecached in SQLite (checkjebon data)
- **Lokale database** — je data blijft op je computer (~106.000 producten)
- **Jumbo web scraping** — producten, prijzen, hoeveelheden en afbeeldingen
- **EDEKA web scraping** — aanbiedingen, kortingen en normale prijzen
- **Product detail pagina** met prijsgeschiedenis en vergelijkbare producten
- **Uitbreidbaar** — voeg nieuwe winkels toe via plugins
- **Responsive design** — werkt op mobiel en desktop

## 🏪 Beschikbare Winkels

### ✅ Direct beschikbaar (gecacheerd)

| Winkel | Data bron |
|--------|-----------|
| **Albert Heijn** | checkjebon |
| **Aldi** | checkjebon |
| **Jumbo** | checkjebon + web scraping |
| **Plus** | checkjebon |
| **Dirk** | checkjebon |
| **Coop** | checkjebon |
| **SPAR** | checkjebon |
| **Vomar** | checkjebon |
| **Picnic** | checkjebon |
| **Hoogvliet** | checkjebon |
| **Jan Linders** | checkjebon |
| **DekaMarkt** | checkjebon |
| **EDEKA** | web scraping (Tübingen) |

## 📁 Projectstructuur

```
aanbiedingen/
├── app.py                    # Flask webapp
├── edeka_scraper.py          # EDEKA web scraper (Playwright)
├── jumbo_scraper.py          # Jumbo web scraper (Playwright)
├── TODO.md                   # Takenplan
├── data/
│   ├── aanbiedingen.db       # SQLite database
│   └── product-images/       # Gecachte product afbeeldingen
├── templates/
│   ├── base.html             # Hoofd sjabloon
│   ├── index.html            # Zoekpagina
│   ├── compare.html          # Prijsvergelijking
│   ├── history.html          # Geschiedenis
│   ├── stores.html           # Winkels info
│   ├── product.html          # Product detail pagina
│   └── 404.html              # Fout pagina
└── static/css/
    └── style.css             # Styling
```

## 🔌 Plugins toevoegen

```python
def fetch_jouw_winkel(query):
    return [{"name": "Product", "price": 1.99, "amount": "500g"}]

register_store("jouwcode", "Jouw Winkel", fetch_jouw_winkel)
```

## 🛠️ Ondersteunde Winkels

| Source | Winkels |
|--------|---------|
| **checkjebon** | 12+ Nederlandse winkels |
| **Playwright** | Jumbo, EDEKA (web scraping) |
