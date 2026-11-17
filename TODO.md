# 📋 Project Stappen Plan — ASD & AAR Loop

## Status: ✅ Basiswebapp voltooid

### Volgende taken (prioriteit):

---

### 🔴 HOOG — Core functionaliteit

#### 1. EDEKA scraper integratie testen
- **Status:** In ontwikkeling
- **Waarom:** EDEKA werkt alleen via browser (Playwright), maar de API werkt niet zonder Duitsland VPN
- **Actie:** 
  1. Test `python edeka_scraper.py` — opent browser en toont 28+ aanbiedingen
  2. Test `/api/search?store=edeka&q=melk` op de webpagina
  3. Voeg EDEKA toe aan de winkel dropdown
- **Gecreëerd:** 2026-11-17 13:35
- **Bijwerken:** `edit TODO.md` als taak voltooid is (verplaats naar "Done")

#### 2. Cache strategie implementeren
- **Status:** In ontwikkeling
- **Waarom:** Elke EDEKA zoekopdracht open een nieuwe browser — traag
- **Actie:**
  1. Cache EDEKA resultaten in SQLite (zelfde als checkjebon)
  2. Update cache als "Update DB" wordt geklikt
  3. Toon cache datum in UI
- **Gecreëerd:** 2026-11-17 13:35

---

### 🟡 MIDDEN — Uitbreidingen

#### 3. Boodschappenlijst optimalisatie
- **Status:** TODO
- **Beschrijving:** Voer meerdere producten in en krijg het optimale winkelplan
  (waar haal ik elk product goedkoopst?)
- **Gecreëerd:** 2026-11-17 13:35
- **Checkjebon heeft dit al:** `getOptimalShoppingPlan()` — kan in onze app worden gebruikt

#### 4. Prijs alerts
- **Status:** TODO
- **Beschrijving:** Notificatie als een product in de lijst daalt
- **Gecreëerd:** 2026-11-17 13:35

#### 5. Prijs geschiedenis grafiekken
- **Status:** TODO
- **Beschrijving:** Toon prijsveranderingen over tijd per product
- **Gecreëerd:** 2026-11-17 13:35

---

### 🟢 LAAG — UX & Polish

#### 6. Responsive design checks
- **Status:** TODO
- **Beschrijving:** Test op mobiel/tablet
- **Gecreëerd:** 2026-11-17 13:35

#### 7. Toegankelijkheid (a11y)
- **Status:** TODO
- **Beschrijving:** WCAG 2.2 AA compliance — keyboard navigation, screen reader
- **Gecreëerd:** 2026-11-17 13:35

#### 8. Documentation
- **Status:** TODO
- **Beschrijving:** README.md complete + commentaar in code
- **Gecreëerd:** 2026-11-17 13:35

---

### 📌 Gereed (Done)

- ✅ SQLite database met ~106.000 producten
- ✅ Checkjebon data integratie
- ✅ Jumbo live API
- ✅ EDEKA web scraper (werkt via Playwright)
- ✅ Zoekpagina met filter
- ✅ Prijsvergelijking pagina
- ✅ Geschiedenis pagina
- ✅ Plugin systeem voor nieuwe winkels

---

## AAR Loop (Ask-Archive-Respond)

Deze loop wordt uitgevoerd voor elke taak:

1. **ASK:** Wat is de status van deze taak? (Check TODO.md)
2. **ARCHIVE:** Wat is de huidige state? (Lees files, check database)
3. **RESPOND:** Wat moet de volgende actie zijn? (Voer taak uit)

### Gebruik:
```bash
# Bekijk huidige taken
cat TODO.md

# Markeer een taak als voltooid (verplaats naar "Done")
# (handmatig TODO.md aanpassen)

# Voeg nieuwe taak toe
# (handmatig TODO.md aanpassen, kopieer een bestaande taak)
```

---

## AAR Loop Script (optioneel — automatisch)

```bash
#!/bin/bash
#aar-loop.sh — automatiseert de AAR loop

# ASK: wat is te doen?
next_task=$(grep -A1 "^#### [0-9]" TODO.md | head -1)

# ARCHIVE: wat is de huidige state?
python3 -c "from app import count_products; print(f'Producten in DB: {count_products()}')"

# RESPOND: voer taak uit
echo "Volgende taak: $next_task"
```
