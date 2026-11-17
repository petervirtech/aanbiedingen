# 📋 Project Stappen Plan

## ✅ Voltooid

### Core functionaliteit
1. **EDEKA scraper** — Playwright web scraping ✅
2. **Jumbo scraper** — Playwright web scraping met images, amounts, links ✅
3. **Zoekpagina** — search met filter (alle winkels + per winkel) ✅
4. **Plugin systeem** — uitbreidbaar met nieuwe winkels ✅
5. **Prijsvergelijking** pagina ✅
6. **Geschiedenis** pagina ✅
7. **Winkels pagina** ✅
8. **Product detail pagina** — met prijsgeschiedenis en vergelijkbare producten ✅
9. **Product image caching** — lokaal opgeslagen in `data/product-images/` ✅

### Database (~106.000 producten)
- ✅ SQLite database met checkjebon data
- ✅ Product groepering + unit normalisatie
- ✅ Favorieten systeem (API)
- ✅ Product images tabel

## 🟡 In ontwikkeling

### Product groepering en unit normalisatie
- ✅ Basis functionaliteit (`normalize_price`, `normalize_name`)
- ✅ `/api/group` endpoint
- 🔄 Fuzzy matching verbeteren (woord match voorrang > substring match)

### Boodschappenlijst optimalisatie
- 📝 Checkjebon heeft `getOptimalShoppingPlan()` — kan integreren
- 📝 UI ontbrekt nog

### Prijs alerts
- 📝 Notificatie als product in lijst daalt
- 📝 Database schema ontbreekt

### Obscura integratie ✅
- ✅ Obscura browser geïnstalleerd en getest (v0.2.7)
- ✅ `edeka_scraper_obscura.py` — EDEKA scraper met Obscura + Playwright fallback
- ✅ `jumbo_scraper_obscura.py` — Jumbo scraper met Obscura + Playwright fallback
- ✅ Plugins geregistreerd in `app.py` (`edeka_obscura`, `jumbo_obscura`)
- ✅ `obscura.md` documentatie geschreven
- ✅ Obscura geïntegreerd in store-list API met status
- 🔄 Stealth mode testen tegen Cloudflare-protected sites

## 🟢 Te doen

- 📝 Responsive design tests
- 📝 Accessibility (a11y) checks
- 📝 Documentatie voltooien
