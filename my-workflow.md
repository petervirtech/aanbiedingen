# My Workflow

A map of who I am, what tools I use, what I own, and the steps I repeat.

---

## 1. Identity & Role

I'm building **Aanbiedingen** — a local web app that scrapes and caches Dutch/German supermarket deals (supermarkt aanbiedingen) and lets you compare prices across 12+ stores. The project is a side tool that stays on my machine.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python (Flask) |
| **Storage** | SQLite (`data/aanbiedingen.db`, ~30 MB, ~106k products) |
| **Scraping** | Playwright (headless Chromium) + `requests` |
| **Scraping (optional)** | [Obscura](https://github.com/h4ckf0r0day/obscura) — Rust-based headless browser, stealth mode, 30MB memory, CLI + CDP server |
| **Frontend** | Vanilla HTML templates, plain CSS |
| **Package manager** | npm (OpenCode plugin only: `@opencode-ai/plugin` v1.18.31) |
| **Shell** | Bash, with `atuin` (command history), `homebrew`, `.NET SDK` |

---

## 3. Skills Installed

### Global (project-level, in `~/.agents/skills/`)

| Skill | Source | Purpose |
|---|---|---|
| **find-skills** | `vercel-labs/skills` | Discover and install new agent skills |
| **astro** | `astrolicious/agent-skills` | Astro web framework workflows |
| **accessibility** | `addyosmani/web-quality-skills` | WCAG 2.2 audits, a11y checks |
| **tailwind-css-patterns** | `giuseppe-trisciuoglio/developer-kit` | Tailwind utility-first CSS patterns |

### Project-level (in `.config/opencode/skills/`)

| Skill | Purpose |
|---|---|
| **aar-loop** | After-Action Review: 4-question debrief, log lessons to `LESSONS.md`, propose fix plans |
| **asd-ste100** | Simplified Technical English rewrite for unambiguous agent/system text |

---

## 4. OpenCode Configuration

- **Model:** `rapid-mlx/qwen3.6-35b-4bit` (235k context, 8k output)
- **Local provider:** OMLX / Rapid-MLX via `@ai-sdk/openai-compatible` at `http://127.0.0.1:8000/v1` (MLX local inference)
- **Plugin:** `@opencode-ai/plugin` v1.18.31
- **Config file:** `~/.config/opencode/opencode.json`
- **Last selected agents:** amp, cline, codex, cursor, droid, gemini-cli, github-copilot, kilo, kimi-code-cli, opencode, warp, zed

---

## 5. Project Structure

```
aanbiedingen/
├── app.py                    # Flask webapp (main entry, all routes, DB logic)
├── edeka_scraper.py          # EDEKA deals scraper (Playwright)
├── jumbo_scraper.py          # Jumbo products scraper (Playwright)
├── README.md                 # Dutch-language docs + store table
├── TODO.md                   # In-progress & backlog items
├── data/
│   ├── aanbiedingen.db       # SQLite (~30 MB, ~106k products)
│   └── product-images/       # Cached product images
├── templates/
│   ├── base.html
│   ├── index.html            # Search page
│   ├── compare.html          # Price comparison
│   ├── history.html          # Comparison history
│   ├── stores.html           # Store info
│   └── product.html          # Product detail + price history
└── static/css/
    └── style.css
```

---

## 6. Weekly Routine — Steps I Repeat

### Every Week (or whenever data is stale)

1. **Update database** — Run `python app.py --update` to fetch fresh checkjebon data from `supermarkt.checkjebon` GitHub repo and write to local SQLite. This pulls 12+ Dutch supermarket deals (AH, Aldi, Jumbo, Plus, Dirk, Coop, SPAR, Vomar, Picnic, Hoogvliet, Jan Linders, DekaMarkt).

2. **Run scrapers** (when cached data is insufficient) — Execute `edeka_scraper.py` (or `edeka_scraper_obscura.py`) and `jumbo_scraper.py` (or `jumbo_scraper_obscura.py`) with Playwright/Obscura to scrape live German/Dutch store pages for deals not covered by checkjebon.

3. **Obscura vs Playwright:** Obscura offers a much lighter alternative (~30MB memory vs 200MB+ for Chrome) with built-in stealth mode (anti-detection, tracker blocking). Use it via the CLI (`obscura fetch/url --eval`) or the CDP server for Puppeteer/Playwright compatibility. When the `obscura` binary is on PATH, the `_obscura.py` scraper variants use it automatically.

3. **Review TODO.md** — Check what's in-progress (fuzzy matching, shopping list optimization, price alerts) and what's still todo (responsive design tests, accessibility).

4. **Restart Flask** — Start `python app.py` (listens on `localhost:9090`) and browse `http://localhost:9090` in a browser to verify everything works.

5. **Search & compare** — Use the web UI to search products, filter by store, compare prices across stores, view price history (30-day rolling), and check product details with cached images.

---

## 7. How I Solve Problems (Patterns)

- **Scraper when API is down:** When an API is unavailable (like Jumbo's `mobileapi`), fall back to Playwright browser scraping and parse HTML/HTML body text with regex.
- **Caching everything locally:** No cloud dependency. Products, images, comparisons — all stored in SQLite on the machine.
- **Plugin system:** Extend with new stores by registering a `fetch_func` via `register_store(code, name, fetch_func)`.
- **Name/amount normalization:** `normalize_name()` strips quantities; `normalize_price()` computes unit prices (per liter, kg, piece) for cross-store comparison.
- **After Action Review:** Use the `aar-loop` skill to debrief failed or friction-heavy sessions, log lessons to `LESSONS.md`, and propose concrete fix plans.
- **Controlled language:** Use `asd-ste100` to rewrite ambiguous text into unambiguous, agent-parseable instructions.

---

## 8. Tools on This Machine

| Category | Tools |
|---|---|
| **Local inference** | LM Studio CLI (`lms`), Ollama, MLX (`rapid-mlx`) |
| **Package managers** | Homebrew, npm, nvm, `.NET SDK` |
| **Shell features** | Atuin (command history search), `.bash-preexec.sh` |
| **Container** | Docker, Colima |
| **Browser (scraping)** | Playwright (Chromium), **Obscura** (Rust-based, stealth mode, CLI + CDP) |
| **Workflow** | OpenCode (primary agent harness), Claude, Copilot, Gemini CLI, Cursor, Codex, Warp, Zed, Kilo, Kimi, Droid, Amp |

---

## 9. What I'm Building Toward

- **Complete coverage** of all Dutch supermarkets via a plugin architecture
- **Fuzzy product matching** — "melk 1L" and "halfvolle melk 1.5L" recognized as the same product
- **Price alerts** — notifications when a product in a wishlist drops
- **Optimal shopping plan** — integrate checkjebon's `getOptimalShoppingPlan()` to minimize total cost
- **Accessibility** — WCAG 2.2 compliance for the web UI

---

## 10. Where Things Live

| Item | Location |
|---|---|
| **Project** | `~/source/aanbiedingen/` |
| **OpenCode config** | `~/.config/opencode/opencode.json` |
| **Global skills** | `~/.agents/skills/` |
| **Project skills** | `~/.config/opencode/skills/` (aar-loop, asd-ste100) |
| **Database** | `~/source/aanbiedingen/data/aanbiedingen.db` |
| **Cached images** | `~/source/aanbiedingen/data/product-images/` |

---

*Created automatically from project analysis.*
