#!/usr/bin/env python3
"""
Webapp om supermarkt aanbiedingen te vergelijken.
Gebruikt SQLite voor lokale caching van alle winkeldata.

Beschikbare winkels:
  - checkjebon (AH, Aldi, Coop, DekaMarkt, Dirk, Hoogvliet, Jan Linders, Jumbo,
    Picnic, Plus, SPAR, Vomar)
  - Jumbo (via SupermarktConnector)

Uitbreidbaar: EDEKA, Lidl, Plus, Dirk, Coop, etc.
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
import requests
import time
import logging
import sys

# =============================================================================
# App setup
# =============================================================================

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "dev-secret-key"
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "aanbiedingen.db"

# Zorg dat data directory bestaat
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# SQLite Database — alles lokaal
# =============================================================================

def get_db():
    """Haal een database connectie (met row factory)."""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Betere concurrentie
    conn.execute("PRAGMA busy_timeout=5000")  # Wacht bij gelockte DB
    return conn


def init_db():
    """Maak database aan met alle benodigde tabellen."""
    conn = get_db()

    conn.executescript("""
        -- Alle producten uit alle winkels
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            supermarket TEXT    NOT NULL,      -- "AH", "Jumbo", etc.
            sm_code     TEXT    NOT NULL,      -- "ah", "jumbo" (key voor winkels)
            name        TEXT    NOT NULL,      -- Productnaam
            price       REAL,                  -- Prijs in euros (geheel, zonder decimale punt)
            amount      TEXT,                  -- Hoeveelheid "1,5 liter"
            category    TEXT,                  -- Categorie
            is_estimate INTEGER DEFAULT 0,     -- Geschatte prijs?
            link        TEXT,                  -- URL naar productpagina
            updated_at  TEXT    DEFAULT (datetime('now')),
            UNIQUE(supermarket, name, amount)  -- Uniek per winkel+naam+hoeveelheid
        );

        -- Indexen voor snelle searches
        CREATE INDEX IF NOT EXISTS idx_products_sm ON products(sm_code);
        CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
        CREATE INDEX IF NOT EXISTS idx_products_sm_name ON products(sm_code, name);

        -- Metadata: wanneer is welke winkel het laatst geupdate?
        CREATE TABLE IF NOT EXISTS update_log (
            supermarket TEXT PRIMARY KEY,
            sm_code     TEXT,
            updated_at  TEXT DEFAULT (datetime('now')),
            product_count INTEGER DEFAULT 0
        );

        -- Prijsvergelijkingen geschiedenis
        CREATE TABLE IF NOT EXISTS comparisons (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    DEFAULT (datetime('now')),
            products    TEXT,              -- JSON lijst van producten
            results_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_comparisons_time ON comparisons(timestamp);

        -- Config (bijv. of update automatisch mag)
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database aangemaakt/geopend: {DB_FILE}")


def count_products():
    """Tel hoeveel producten er in de DB zitten."""
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()
    conn.close()
    return row["c"] if row else 0


def update_from_checkjebon(data):
    """
    Schrijf checkjebon data naar de SQLite database.
    Ververs alle bestaande producten voor de betreffende winkels.
    
    Nieuwe checkjebon formaat:
    [{
        "n": "ah",                    # winkel code
        "d": [                        # products
            {"n": "Productnaam", "p": 2.49, "s": "1 l", "l": "path"},
            ...
        ]
    }]
    """
    conn = get_db()
    total = 0

    for sm in data:
        sm_code = (sm.get("n") or "").upper()
        sm_name = sm.get("n", sm_code)
        
        # De producten zitten in "d" (compact formaat)
        products = sm.get("d", [])

        # Bestaande producten voor deze winkel wissen (ververs)
        conn.execute(
            "DELETE FROM products WHERE sm_code = ?", (sm_code,)
        )

        for p in products:
            conn.execute("""
                INSERT OR IGNORE INTO products
                    (supermarket, sm_code, name, price, amount, category, is_estimate, link, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                sm_name,
                sm_code,
                p.get("n", ""),           # productnaam
                p.get("p"),                # prijs
                p.get("s"),                # hoeveelheid
                None,                      # category
                0,                         # is_estimate
                p.get("l"),                # link (path, niet volledige URL)
            ))
            total += 1

        # Update metadata
        conn.execute("""
            INSERT OR REPLACE INTO update_log (supermarket, sm_code, updated_at, product_count)
            VALUES (?, ?, datetime('now'), ?)
        """, (sm_name, sm_code, total))

    conn.commit()
    conn.close()
    logger.info(f"{total} producten weggeschreven naar SQLite")


def search_db(query, sm_code=None):
    """
    Zoek producten in de lokale SQLite database.
    """
    conn = get_db()

    query_lower = query.lower().strip()

    # Eerst exact zoeken, dan fuzzy
    if sm_code:
        base_query = "SELECT * FROM products WHERE sm_code = ? AND LOWER(name) LIKE ?"
        params = [sm_code, f"%{query_lower}%"]
    else:
        base_query = "SELECT * FROM products WHERE LOWER(name) LIKE ?"
        params = [f"%{query_lower}%"]

    rows = conn.execute(base_query, params).fetchall()

    # Fuzzy filter: alle karakters van query moeten in naam voorkomen
    results = []
    for row in rows:
        name = (row["name"] or "").lower()
        if query_lower in name or _fuzzy_match(query_lower, name):
            results.append(dict(row))

    conn.close()

    # Groepeer per winkel
    by_sm = {}
    for p in results:
        code = p["sm_code"]
        if code not in by_sm:
            by_sm[code] = {
                "supermarket": p["supermarket"],
                "code": code,
                "products": [],
            }
        by_sm[code]["products"].append({
            "name": p["name"],
            "price": p["price"],
            "amount": p["amount"],
            "category": p["category"],
            "isEstimate": bool(p["is_estimate"]),
            "link": p["link"],
        })

    return list(by_sm.values())[:20]  # max 20 winkels met resultaten


def save_comparison(products):
    """Sla een prijsvergelijking op."""
    conn = get_db()
    conn.execute(
        "INSERT INTO comparisons (products, results_count) VALUES (?, ?)",
        (json.dumps(products), 0)
    )
    conn.commit()
    conn.close()


def load_comparisons(limit=50):
    """Haal laatste vergelijkingen."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM comparisons ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_update_status():
    """Laat zien wanneer welke winkel het laatst geüpdatet is."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM update_log ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _fuzzy_match(query, text):
    """Alle karakters van query moeten in text voorkomen (in volgorde, niet noodzakelijk aangrenzend)."""
    qi = 0
    for c in text:
        if qi < len(query) and c == query[qi]:
            qi += 1
            if qi == len(query):
                return True
    return False


# =============================================================================
# Data download: checkjebon → SQLite
# =============================================================================

def fetch_checkjebon_to_db():
    """Download checkjebon data en schrijf naar SQLite."""
    url = "https://raw.githubusercontent.com/supermarkt/checkjebon/main/data/supermarkets.json"
    logger.info("checkjebon data downloaden...")

    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    update_from_checkjebon(data)
    total = count_products()
    logger.info(f"Klaar! {total} producten in lokale database.")
    return total


# =============================================================================
# SupermarktConnector (Jumbo via API)
# =============================================================================

def fetch_jumbo_online(query):
    """Zoek live bij Jumbo (buiten cache)."""
    try:
        from supermarktconnector.jumbo import JumboConnector
        jm = JumboConnector()
        found = jm.search_products(query=query, size=10)
        products = []
        if found and found.get("products", {}).get("data"):
            for p in found["products"]["data"]:
                price_info = p.get("prices", {}).get("price", {})
                unit_info = p.get("prices", {}).get("unitPrice", {}).get("price", {})
                img = (p.get("imageInfo", {}).get("primaryView", [{}]) or [{}])[0]
                products.append({
                    "name": p.get("title"),
                    "price": price_info.get("amount", 0) / 100,
                    "unit_price": unit_info.get("amount", 0) / 100,
                    "amount": p.get("quantity"),
                    "available": p.get("available"),
                    "image": img.get("url"),
                    "link": f"https://www.jumbo.com/product/{p.get('id')}",
                })
        return [{"supermarket": "Jumbo (live)", "code": "jumbo_live", "products": products}]
    except Exception as e:
        logger.warning(f"Jumbo live search faalde: {e}")
        return []


# =============================================================================
# Plugin interface voor winkels
# =============================================================================

_store_plugins = {}


def register_store(code, name, fetch_func):
    """Registreer een winkel-connector."""
    _store_plugins[code] = {"name": name, "func": fetch_func}


def search_plugin(query, store_code):
    """Zoek via een plugin."""
    if store_code in _store_plugins:
        try:
            return _store_plugins[store_code]["func"](query)
        except Exception as e:
            logger.warning(f"Plugin {store_code} faalde: {e}")
    return []


# TODO plugins
def _fetch_edeka(query):
    """EDEKA scraper -- haalt aanbiedingen op van edeka.de website."""
    try:
        from edeka_scraper import fetch_edeka_offers
        products = fetch_edeka_offers(query)
        return [{"supermarket": "EDEKA (Tübingen)", "code": "edeka", "products": products}]
    except Exception as e:
        logger.warning(f"EDeka scraper faalde: {e}")
        return []

def _fetch_jumbo(query):
    """Jumbo scraper -- haalt producten op via web scraping (API is down)."""
    try:
        from jumbo_scraper import fetch_jumbo_products
        products = fetch_jumbo_products(query)
        return [{"supermarket": "Jumbo", "code": "jumbo", "products": products}]
    except Exception as e:
        logger.warning(f"Jumbo scraper faalde: {e}")
        return []

def _fetch_lidl(query): return []
def _fetch_plus(query): return []
def _fetch_dirk(query): return []
def _fetch_coop(query): return []

register_store("edeka", "EDEKA", _fetch_edeka)
register_store("jumbo", "Jumbo", _fetch_jumbo)
register_store("lidl", "Lidl", _fetch_lidl)
register_store("plus", "Plus", _fetch_plus)
register_store("dirk", "Dirk", _fetch_dirk)
register_store("coop", "Coop", _fetch_coop)


# =============================================================================
# Flask Routes
# =============================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["GET"])
def api_search():
    query = request.args.get("q", "").strip()
    store = request.args.get("store", "all")

    if not query:
        return jsonify({"error": "Geen zoekterm"}), 400

    results = []

    # Local SQLite DB (checkjebon)
    if store in ("all", "checkjebon", "local"):
        results.extend(search_db(query, sm_code=None if store == "all" else None))

    # Live Jumbo API
    if store in ("all", "jumbo"):
        results.extend(fetch_jumbo_online(query))

    # Plugins (EDEKA, Lidl, etc.)
    if store not in ("all", "checkjebon", "jumbo", "local"):
        results.extend(search_plugin(query, store))

    return jsonify({"query": query, "results": results})


@app.route("/api/search-all", methods=["POST"])
def api_search_all():
    data = request.get_json() or {}
    products = data.get("products", [])

    if not products:
        return jsonify({"error": "Geen producten"}), 400

    results = []
    # Local DB (alle winkels)
    results.extend(search_db(products[0], None))
    # Live Jumbo
    results.extend(fetch_jumbo_online(products[0]))

    save_comparison(products)
    return jsonify({"query": products, "results": results})


@app.route("/api/db-status", methods=["GET"])
def api_db_status():
    """Toon status van de lokale database."""
    count = count_products()
    updates = get_update_status()
    return jsonify({
        "total_products": count,
        "updates": updates,
        "db_file": str(DB_FILE),
    })


@app.route("/api/store-list", methods=["GET"])
def api_store_list():
    stores = [
        {"code": "local", "name": "Alle (cached)", "desc": "AH, Aldi, Coop, Dirk, Jumbo, Plus, SPAR, Vomar, Picnic, Hoogvliet, Jan Linders, DekaMarkt"},
        {"code": "jumbo", "name": "Jumbo (live)", "desc": "Directe API van Jumbo.com"},
    ]
    for code, info in _store_plugins.items():
        stores.append({"code": code, "name": info["name"], "desc": info["desc"], "status": "coming-soon"})
    return jsonify({"stores": stores})


@app.route("/compare", methods=["GET", "POST"])
def compare():
    result = None
    if request.method == "POST":
        data = request.get_json() or {}
        products = data.get("products", [])
        if products:
            all_results = []
            for p in products[:10]:
                all_results.extend(search_db(p))
            result = {"products": products, "results": all_results}
    return render_template("compare.html", result=result)


@app.route("/history")
def history():
    comps = load_comparisons()
    return render_template("history.html", comparisons=comps)


@app.route("/stores")
def stores_page():
    stores_resp = app.url_map["api_store_list"](None)
    stores = json.loads(stores_resp.get_data(as_text=True)).get("stores", [])
    db_status = json.loads(app.url_map["api_db_status"](None).get_data(as_text=True))
    return render_template("stores.html", stores=stores, db_status=db_status)


@app.route("/admin/update", methods=["POST"])
def admin_update():
    """Update de lokale database met nieuwste checkjebon data."""
    try:
        total = fetch_checkjebon_to_db()
        return jsonify({"ok": True, "products": total})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    init_db()

    if "--update" in sys.argv:
        total = fetch_checkjebon_to_db()
        print(f"\nDatabase: {DB_FILE}")
        print(f"Producten: {total}")
    else:
        # Controleer of DB leeg is — automatische eerste update
        if count_products() == 0:
            print("📦 Lokale DB is leeg. checkjebon data downloaden...")
            fetch_checkjebon_to_db()
        app.run(host="0.0.0.0", port=9090)
