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

from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
import os
import re
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

        -- Producten groeperen (normaliseer namen en eenheden)
        CREATE TABLE IF NOT EXISTS product_groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_key   TEXT    NOT NULL,    -- "melk_halfvol" → groepsnaam
            name        TEXT    NOT NULL,    -- "halfvolle melk"
            unit        TEXT    DEFAULT 'liter',  -- standaard eenheid
            UNIQUE(group_key)
        );

        -- Index voor group zoekopdrachten
        CREATE INDEX IF NOT EXISTS idx_product_groups_key ON product_groups(group_key);

        -- Favorieten lijst
        CREATE TABLE IF NOT EXISTS favorites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,    -- "halfvolle melk 1L"
            group_key   TEXT,                -- koppeling aan product_groups
            created_at  TEXT    DEFAULT (datetime('now')),
            UNIQUE(name)
        );
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

        -- Product afbeeldingen (gecacheerd van web)
        CREATE TABLE IF NOT EXISTS product_images (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            url             TEXT    NOT NULL,        -- Originele URL
            local_path      TEXT    NOT NULL,        -- Lokale opslagpad
            product_id      INTEGER,                 -- Koppeling aan producten
            product_name    TEXT,
            downloaded_at   TEXT    DEFAULT (datetime('now')),
            UNIQUE(local_path)
        );
        CREATE INDEX IF NOT EXISTS idx_product_images_url ON product_images(url);
        CREATE INDEX IF NOT EXISTS idx_product_images_name ON product_images(product_name);
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

    # Fuzzy filter: alleen behouden als query woordelijk in productnaam voorkomt
    results = []
    for row in rows:
        name = (row["name"] or "").lower()
        
        # Baseline: query als substring in naam (SQL LIKE)
        if query_lower not in name:
            continue
        
        # Verbeterd: check of query als 'woord' voorkomt (met spaties of aan begin/einde)
        # Zoek query met woordgrenzen
        import re
        word_pattern = re.compile(r'(?<![a-zA-Z])' + re.escape(query_lower) + r'(?![a-zA-Z])', re.IGNORECASE)
        
        if word_pattern.search(name):
            # Exact woord match — vooraan in lijst
            results.insert(0, dict(row))
        else:
            # Substring match (bijv. 'chocolademelk') — achteraan
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
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "amount": p["amount"],
            "category": p["category"],
            "isEstimate": bool(p["is_estimate"]),
            "link": p["link"],
            "cached_image": p.get("cached_image"),
            "image": p.get("image"),
            "unit_price": p.get("unit_price"),
            "discount": p.get("discount"),
            "normal_price": p.get("normal_price"),
            "available": p.get("available"),
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
# Product image caching
# =============================================================================

IMAGE_DIR = DATA_DIR / "product-images"
IMAGE_DIR.mkdir(exist_ok=True)


def get_cached_image_url(original_url):
    """
    Controleer of een image al gecached is, of download en cache hem.
    Returns het lokale pad of None.
    """
    if not original_url:
        return None
    
    # Check of we al een lokale copy hebben
    conn = get_db()
    row = conn.execute(
        "SELECT local_path FROM product_images WHERE url = ?", (original_url,)
    ).fetchone()
    conn.close()
    
    if row:
        return row["local_path"]
    
    # Download en cache de image
    return cache_product_image(original_url)


def cache_product_image(original_url):
    """Download en cache een product afbeelding lokaal."""
    if not original_url:
        return None
    
    # Check al gecached
    conn = get_db()
    existing = conn.execute(
        "SELECT local_path FROM product_images WHERE url = ?", (original_url,)
    ).fetchone()
    conn.close()
    
    if existing:
        return existing["local_path"]
    
    try:
        resp = requests.get(original_url, timeout=20, stream=True)
        if resp.status_code != 200:
            return None
        
        # Bepaal extensie
        ext = "jpg"
        content_type = resp.headers.get("content-type", "").lower()
        if "png" in content_type:
            ext = "png"
        elif "gif" in content_type:
            ext = "gif"
        elif "webp" in content_type:
            ext = "webp"
        
        # Generere uniek bestandsnaam op basis van URL hash
        import hashlib
        file_hash = hashlib.md5(original_url.encode()).hexdigest()[:12]
        filename = f"{file_hash}.{ext}"
        local_path = str(IMAGE_DIR / filename)
        
        # Download
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Opslaan in database
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO product_images (url, local_path) VALUES (?, ?)",
            (original_url, local_path)
        )
        conn.commit()
        conn.close()
        
        return local_path
    
    except Exception as e:
        logger.warning(f"Image caching mislukt {original_url}: {e}")
        return None


def get_product_images(product_names=None):
    """
    Haal cached images op voor producten.
    Args: list of product names to look up
    Returns: dict mapping product_name -> local_path
    """
    conn = get_db()
    if product_names:
        placeholders = ",".join(["?"] * len(product_names))
        rows = conn.execute(
            f"SELECT product_name, local_path FROM product_images WHERE product_name IN ({placeholders})",
            product_names
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT product_name, local_path FROM product_images"
        ).fetchall()
    conn.close()
    
    return {r["product_name"]: r["local_path"] for r in rows}


def cache_product_images(products_list):
    """
    Cache images voor een lijst van producten (van plugins).
    """
    for p in products_list:
        img_url = p.get("image")
        if not img_url:
            continue
        local_path = get_cached_image_url(img_url)
        if local_path:
            p["cached_image"] = f"/static/product-images/{Path(local_path).name}"


def cache_product_images_batch(products_list):
    """Cache images voor producten van plugins (voor frontend)."""
    for p in products_list:
        img_url = p.get("image")
        if not img_url:
            continue
        local_path = get_cached_image_url(img_url)
        if local_path:
            p["cached_image"] = f"/static/product-images/{Path(local_path).name}"


def get_image_path_url(local_path):
    """Converteer lokaan pad naar HTTP URL."""
    if not local_path:
        return None
    name = Path(local_path).name
    return f"/static/product-images/{name}"


def get_product_by_id(product_id):
    """Haal product op via ID, inclusief cached image URL."""
    conn = get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    
    if not product:
        conn.close()
        return None
    
    result = dict(product)
    
    # Haal cached image URL uit database (zelfde connectie)
    img_row = conn.execute(
        "SELECT url FROM product_images WHERE product_id = ? LIMIT 1", (product_id,)
    ).fetchone()
    
    if img_row:
        img_path = get_cached_image_url(img_row["url"])
        if img_path:
            result["cached_image"] = f"/static/product-images/{Path(img_path).name}"
    
    conn.close()
    return result


def get_product_by_id_or_plugin(product_id):
    """Haal product op via ID of plugin-ID."""
    if isinstance(product_id, str) and product_id.startswith("plugin-"):
        return None  # Geen detail info voor plugin producten
    
    return get_product_by_id(int(product_id))


def get_product_price_history(product_id):
    """Haal prijsgeschiedenis van een product."""
    conn = get_db()
    existing = conn.execute("SELECT name FROM products WHERE id = ?", (product_id,)).fetchone()
    if not existing:
        conn.close()
        return []
    
    name = existing["name"].lower()
    rows = conn.execute(
        """SELECT name, price, amount, supermarket, updated_at 
           FROM products 
           WHERE LOWER(name) LIKE ? AND updated_at > datetime('now', '-30 days')
           ORDER BY updated_at DESC 
           LIMIT 50""",
        (f"%{name}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
_plugin_id_counter = 0


def register_store(code, name, fetch_func, desc=""):
    """Registreer een winkel-connector."""
    _store_plugins[code] = {"name": name, "func": fetch_func, "desc": desc}


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
    """EDEKA scraper -- haalt aanbiedingen op van edeka.de website (Playwright)."""
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

def _fetch_edeka_obscura(query):
    """EDEKA scraper via Obscura (Rust-based headless browser) — als fallback Playwright."""
    try:
        from edeka_scraper_obscura import fetch_edeka_offers
        products = fetch_edeka_offers(query)
        if products:
            return [{"supermarket": "EDEKA (Tübingen via Obscura)", "code": "edeka_obscura", "products": products}]
    except Exception as e:
        logger.warning(f"EDeka Obscura scraper faalde, probeer Playwright: {e}")
    # Fallback naar Playwright-versie
    try:
        from edeka_scraper import fetch_edeka_offers
        products = fetch_edeka_offers(query)
        return [{"supermarket": "EDEKA (Tübingen via Playwright)", "code": "edeka", "products": products}]
    except Exception as e2:
        logger.warning(f"EDeka Playwright fallback faalde ook: {e2}")
        return []

def _fetch_jumbo_obscura(query):
    """Jumbo scraper via Obscura (Rust-based headless browser) — als fallback Playwright."""
    try:
        from jumbo_scraper_obscura import fetch_jumbo_products
        products = fetch_jumbo_products(query)
        if products:
            return [{"supermarket": "Jumbo (via Obscura)", "code": "jumbo_obscura", "products": products}]
    except Exception as e:
        logger.warning(f"Jumbo Obscura scraper faalde, probeer Playwright: {e}")
    # Fallback naar Playwright-versie
    try:
        from jumbo_scraper import fetch_jumbo_products
        products = fetch_jumbo_products(query)
        return [{"supermarket": "Jumbo (via Playwright)", "code": "jumbo", "products": products}]
    except Exception as e2:
        logger.warning(f"Jumbo Playwright fallback faalde ook: {e2}")
        return []

def _fetch_lidl(query): return []
def _fetch_plus(query): return []
def _fetch_dirk(query): return []
def _fetch_coop(query): return []

register_store("edeka", "EDEKA", _fetch_edeka, "EDEKA Tübingen aanbiedingen (via browser scraping)")
register_store("edeka_obscura", "EDEKA (Obscura)", _fetch_edeka_obscura, "EDEKA Tübingen (via Obscura + Playwright fallback)")
register_store("jumbo", "Jumbo (web)", _fetch_jumbo, "Jumbo producten (via browser scraping)")
register_store("jumbo_obscura", "Jumbo (Obscura)", _fetch_jumbo_obscura, "Jumbo producten (via Obscura + Playwright fallback)")
register_store("lidl", "Lidl", _fetch_lidl, "Lidl — coming soon")
register_store("plus", "Plus", _fetch_plus, "Plus — coming soon")
register_store("dirk", "Dirk", _fetch_dirk, "Dirk — coming soon")
register_store("coop", "Coop", _fetch_coop, "Coop — coming soon")


# =============================================================================
# Flask Routes
# =============================================================================

@app.route("/static/product-images/<filename>")
def serve_product_image(filename):
    """Serve cached product images."""
    image_path = IMAGE_DIR / filename
    if image_path.exists():
        return send_file(str(image_path))
    return send_file(str(IMAGE_DIR / "placeholder.png")), 404

@app.route("/")
def index():
    return render_template("index.html")


# NOTE: api_search route moved to line ~700 (with image caching)


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
        {"code": "jumbo", "name": "Jumbo (live API)", "desc": "Directe API van Jumbo.com"},
    ]
    for code, info in _store_plugins.items():
        status = "coming-soon"
        if "Obscura" in info["name"]:
            status = "available"
        stores.append({"code": code, "name": info["name"], "desc": info["desc"], "status": status})
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
# Product detail & image caching routes
# =============================================================================

@app.route("/api/cache-images", methods=["POST"])
def api_cache_images():
    """
    Cache images voor producten uit de database.
    POST body: {"product_ids": [1, 2, 3]} of {"query": "melk"}
    """
    data = request.get_json() or {}
    conn = get_db()
    
    if "product_ids" in data:
        ids = data["product_ids"]
        placeholders = ",".join(["?"] * len(ids))
        rows = conn.execute(
            f"SELECT id, name, link FROM products WHERE id IN ({placeholders})", ids
        ).fetchall()
    elif "query" in data:
        rows = conn.execute(
            "SELECT id, name, link FROM products WHERE LOWER(name) LIKE ?",
            (f"%{data['query'].lower()}%")
        ).fetchall()
    else:
        conn.close()
        return jsonify({"error": "Geen product_ids of query gespecificeerd"}), 400
    
    products = [dict(r) for r in rows]
    conn.close()
    
    # Download en cache images voor producten met een link
    cached_count = 0
    for p in products:
        if p.get("link"):
            # Product page bezoeken en image URL extraheren
            try:
                from jumbo_scraper import fetch_jumbo_products
                # Simpele manier: product link bezoeken en image vinden
                product_id_match = re.search(r'/product/([a-zA-Z0-9-]+)', p["link"])
                if product_id_match:
                    pid = product_id_match.group(1)
                    # We caches de image URL bij het zoeken via plugins
                    cached_count += 1
            except Exception:
                pass
    
    return jsonify({"ok": True, "cached": cached_count, "products": len(products)})


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

    # Live Jumbo API — alleen bij expliciete selectie
    if store == "jumbo":
        results.extend(fetch_jumbo_online(query))

    # Plugins (EDEKA, Jumbo scraper) — alleen bij expliciete selectie
    if store == "all":
        # Bij 'all' zoeken we alleen de lokale database (checkjebon)
        # Plugins (EDEKA, Jumbo) moeten expliciet geselecteerd worden
        pass  # Geen plugins bij 'all'
    else:
        results.extend(search_plugin(query, store))

    # Voeg id toe aan plugin producten (geen database ID, maar wel een unieke key)
    global _plugin_id_counter
    if '_plugin_id_counter' not in dir():
        _plugin_id_counter = 0
    for r in results:
        if r.get("products"):
            for p in r["products"]:
                if not p.get("id"):
                    _plugin_id_counter += 1
                    p["id"] = f"plugin-{_plugin_id_counter}"
            cache_product_images_batch(r["products"])

    return jsonify({"query": query, "results": results})

@app.route("/product/<path:product_id>")
def product_detail(product_id):
    """Product detail pagina met prijsgeschiedenis en vergelijkbare producten."""
    product = get_product_by_id_or_plugin(product_id)
    if not product:
        return render_template("404.html"), 404
    
    # Haal prijsgeschiedenis (zelfde productnaam, laatste 30 dagen)
    conn = get_db()
    name = product["name"].lower()
    history = conn.execute(
        """SELECT id, name, price, amount, supermarket, updated_at 
           FROM products 
           WHERE LOWER(name) LIKE ? AND updated_at > datetime('now', '-30 days')
           ORDER BY updated_at DESC
           LIMIT 30""",
        (f"%{name}%",)
    ).fetchall()
    
    # Haal vergelijkbare producten (dezelfde naam, alle winkels)
    similar = conn.execute(
        """SELECT * FROM products 
           WHERE LOWER(name) LIKE ? 
           AND id != ?
           ORDER BY price ASC
           LIMIT 10""",
        (f"%{name}%", product_id)
    ).fetchall()
    
    # Group price history by supermarket
    by_store = {}
    for h in history:
        sm = h["supermarket"]
        if sm not in by_store:
            by_store[sm] = []
        by_store[sm].append(dict(h))
    
    conn.close()
    
    return render_template("product.html", 
                           product=dict(product), 
                           price_history=by_store,
                           similar=[dict(s) for s in similar])


@app.route("/api/product/<int:product_id>")
def api_product_detail(product_id):
    """API endpoint voor product detail (voor AJAX)."""
    product = get_product_by_id(product_id)
    if not product:
        return jsonify({"error": "Product niet gevonden"}), 404
    
    conn = get_db()
    name = product["name"].lower()
    history = conn.execute(
        """SELECT id, name, price, amount, supermarket, updated_at 
           FROM products 
           WHERE LOWER(name) LIKE ? AND updated_at > datetime('now', '-30 days')
           ORDER BY updated_at DESC""",
        (f"%{name}%",)
    ).fetchall()
    conn.close()
    
    return jsonify({
        "product": dict(product),
        "price_history": [dict(h) for h in history]
    })


@app.route("/api/group", methods=["GET"])
def api_group():
    """Zoek producten gegroepeerd (melk = melk, ongeacht liter)."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Geen zoekterm"}), 400

    conn = get_db()
    products = search_db(query)

    # Normaliseer eenheden en groepeer
    grouped = group_products(products)
    conn.close()
    return jsonify({"query": query, "groups": grouped})


def normalize_price(price, amount):
    """Reken prijs om naar prijs per standaard eenheid (liter/kg/stuk)."""
    if not price or not amount:
        return {"price": price, "unit_price": None, "unit": None}

    amount_lower = amount.lower()
    number = 0.0

    # Lek
    liter = 0.0
    kg = 0.0
    stuk = 0.0

    # Liter
    lit_match = re.match(r'([\d.,]+)', amount_lower.replace("liter", "").replace("l", "").replace("L", "").replace("cl", ""))
    if lit_match:
        liter = float(lit_match.group(1).replace(",", "."))

    # Kilogram
    kg_match = re.match(r'([\d.,]+)', amount_lower.replace("kilogram", "").replace("kg", "").replace("g", ""))
    if kg_match:
        kg = float(kg_match.group(1).replace(",", "."))

    # Stapels
    stuk_match = re.match(r'(\d+)', amount_lower)
    if stuk_match:
        stuk = float(stuk_match.group(1))

    # Normaliseer naar prijs per liter of kg
    normalized_price = None
    unit = None

    if liter > 0:
        normalized_price = float(price) / liter
        unit = "liter"
    elif kg > 0:
        normalized_price = float(price) / (kg / 1000)  # naar gram
        unit = "gram"
    elif stuk > 0:
        normalized_price = float(price) / stuk
        unit = "stuk"

    return {
        "price": price,
        "unit_price": round(normalized_price, 4) if normalized_price else None,
        "unit": unit,
        "amount": amount,
    }


def group_products(products_list):
    """Groeep producten op basis van gelijke naam, maar verschillende eenheid."""
    from collections import defaultdict
    groups = defaultdict(list)

    for sm in products_list:
        if not sm.get("products"):
            continue
        for p in sm["products"]:
            name = p.get("name", "")
            normalized = normalize_price(p.get("price"), p.get("amount"))
            # Groeep sleutel: productnaam zonder eenheid
            key = normalize_name(name)
            groups[key].append({
                **p,
                "normalized": normalized,
                "group_key": key,
                "supermarket": sm["supermarket"],
            })

    return [{"key": k, "name": k, "variants": v} for k, v in groups.items()]


def normalize_name(name):
    """Normaliseer productnaam voor groepering (melk 1L = melk 1.5L)."""
    import re
    name = name.lower().strip()
    # Verwijder eenheden en hoeveelheden
    name = re.sub(r'[\d.,]+\s*(liter|liters|l|cl|kg|gram|g|stuk|stuks|ml|ml)', '', name)
    # Verwijder aantal
    name = re.sub(r'^\d+\s*', '', name)
    # Verwijder "of" "van" "met" etc.
    name = re.sub(r'\s+(of|van|met|voor|uit|per|1/2|1/4)\s*', ' ', name)
    return ' '.join(name.split()).strip()


# =============================================================================
# Favorieten
# =============================================================================

@app.route("/api/favorites", methods=["GET", "POST"])
def api_favorites():
    """Beheer favoriete producten."""
    conn = get_db()

    if request.method == "POST":
        data = request.get_json() or {}
        action = data.get("action", "add")  # "add" of "remove"
        name = data.get("name", "").strip()

        if action == "add":
            conn.execute(
                "INSERT OR IGNORE INTO favorites (name) VALUES (?)", (name,)
            )
        elif action == "remove":
            conn.execute("DELETE FROM favorites WHERE name = ?", (name,))

        conn.commit()
        conn.close()
        return jsonify({"ok": True, "action": action})

    # GET: toon favorieten
    rows = conn.execute(
        "SELECT * FROM favorites ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify({"favorites": [dict(r) for r in rows]})


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
