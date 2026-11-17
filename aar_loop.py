#!/usr/bin/env python3
"""
AAR Loop (Ask-Archive-Respond) voor ASD (Agent-Driven Development).
Leest TODO.md, bepaalt volgende taak, archiveert state, voert taak uit.
"""

import re
import json
import sqlite3
from pathlib import Path

TODO_FILE = Path(__file__).parent / "TODO.md"


def parse_tasks():
    text = TODO_FILE.read_text()
    tasks = []
    current_section = None
    for line in text.split("\n"):
        if line.startswith("### "):
            current_section = line[4:]
        elif line.startswith("#### "):
            parts = line.split(" ", 2)
            task_id = parts[1].strip() if len(parts) > 1 else parts[0][7:].strip()
            task_name = parts[2].strip() if len(parts) > 2 else ""
            tasks.append({
                "id": task_id,
                "name": task_name,
                "section": current_section,
                "status": "TODO" if "Done" not in current_section else "DONE",
            })
    return tasks


def get_next_task():
    tasks = parse_tasks()
    for task in tasks:
        if task["status"] == "TODO":
            return task
    return None


def archive_state():
    state = {"database": {}, "files": {}}
    db_path = Path(__file__).parent / "data" / "aanbiedingen.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()
        state["database"]["total_products"] = row["c"]
        stores = conn.execute(
            "SELECT sm_code, COUNT(*) as cnt FROM products GROUP BY sm_code"
        ).fetchall()
        state["database"]["stores"] = {r["sm_code"]: r["cnt"] for r in stores}
        conn.close()
    for f in (Path(__file__).parent).glob("*"):
        if f.is_file() and not f.is_dir() and str(f).endswith((".py", ".md", ".db")):
            state["files"][f.name] = f.stat().st_size
    return state


def respond(task):
    print(f"\n{'='*60}")
    print(f"TAKE: #{task['id']} -- {task['name']}")
    print(f"Sectie: {task['section']}")
    print(f"{'='*60}\n")
    
    if task["id"] == "1":
        print("Actie: Test EDEKA scraper")
        print("  1. Voer uit: python edeka_scraper.py")
        print("  2. Open http://localhost:9090 en zoek op 'edeka'")
        print("  3. Kies EDEKA in dropdown")
        print()
    elif task["id"] == "2":
        print("Actie: Implementeer EDEKA caching in SQLite")
        print("  1. Voeg edeka_offers tabel toe aan database")
        print("  2. Schrijf EDEKA resultaten bij update")
        print("  3. Toon cache datum in UI")
        print()
    else:
        print(f"Actie: Werk {task['name']} uit")
        print()


def run_loop():
    print("=== AAR Loop ===\n")
    task = get_next_task()
    if not task:
        print("Alle taken voltooid!\n")
        return
    
    print(f"Huidige taak: #{task['id']} -- {task['name']}")
    state = archive_state()
    print(f"Database: {state['database'].get('total_products', 0)} producten")
    for store, count in state['database'].get('stores', {}).items():
        print(f"  {store}: {count}")
    respond(task)


if __name__ == "__main__":
    run_loop()
