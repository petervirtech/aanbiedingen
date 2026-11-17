# 🛒 Aanbiedingen Vergelijken

Webapp om supermarkt aanbiedingen te vergelijken — lokaal op je computer.

## ⚡ Snel Starten

```bash
pip install flask requests supermarktconnector
python app.py
# Open http://localhost:9090
```

## 📦 Features

- **12+ winkels** direct beschikbaar via checkjebon data (gecacheerd in SQLite)
- **Lokale SQLite database** — je data blijft lokaal
- **Prijsvergelijking** tussen meerdere winkels
- **Uitbreidbaar** — voeg nieuwe winkels toe via plugins

## 🏪 Beschikbare Winkels

### ✅ Direct beschikbaar (gecacheerd in SQLite)

| Winkel | Data bron |
|--------|-----------|
| **Albert Heijn** | checkjebon |
| **Aldi** | checkjebon |
| **Jumbo** | checkjebon + live API |
| **Plus** | checkjebon |
| **Dirk** | checkjebon |
| **Coop** | checkjebon |
| **SPAR** | checkjebon |
| **Vomar** | checkjebon |
| **Picnic** | checkjebon |
| **Hoogvliet** | checkjebon |
| **Jan Linders** | checkjebon |
| **DekaMarkt** | checkjebon |

> ~106.000+ producten lokaal gekaakt!

### 🔜 Nieuw: EDEKA (Duitsland)

EDEKA connector is beschikbaar via `edeka_connector.py` maar vereist:
- **VPN naar Duitsland** (API is geografisch geblokkeerd)
- of een **Duitse proxy**

**Hoe te activeren:**
1. Zet een VPN op naar Duitsland
2. Herstart `python app.py`
3. EDEKA verschijnt nu bij de zoekopties

De connector haalt huidige aanbiedingen op van:
- **EDEKA Markte Tübingen** (GLN: 4314021182307) — jouw markt
- Of elke andere EDEKA winkel met een bekende GLN

## 📁 Projectstructuur

```
aanbiedingen/
├── app.py                    # Flask webapp (主 program)
├── edeka_connector.py        # EDEKA API connector (optional)
├── requirements.txt          # Dependencies
├── data/
│   └── aanbiedingen.db       # SQLite database (wordt automatisch aangemaakt)
├── templates/
│   ├── base.html             # Hoofd sjabloon
│   ├── index.html            # Zoekpagina
│   ├── compare.html          # Prijsvergelijking
│   ├── history.html          # Geschiedenis
│   └── stores.html           # Winkels + database info
└── static/css/
    └── style.css             # Styling
```

## 🔌 Eigen winkel toevoegen

```python
# In app.py, boven "if __name__":

def fetch_jouw_winkel(query):
    # Haal producten op van jouw_winkel.nl/aanbiedingen
    return [{"name": "Product", "price": 1.99, "amount": "500g"}]

register_store("jouwcode", "Jouw Winkel", fetch_jouw_winkel)
```

Dan is de winkel direct beschikbaar in de webapp!

## 🛠️ Ondersteunde Winkels (API bronnen)

| Source | Winkels | Python lib |
|--------|---------|------------|
| **checkjebon** | 12+ Nederlandse winkels | checkjebon open data |
| **SupermarktConnector** | AH, Jumbo | supermarktconnector package |
| **EDEKA** (Germany) | Alle EDEKA markten | edeka_connector.py |

## 📝 Licentie

Project code: MIT
Data: checkjebon (MIT), SupermarktConnector (MIT)
