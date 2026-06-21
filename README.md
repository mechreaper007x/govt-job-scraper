# Indian Government & PSU Job Notification Tracker

A highly resilient, concurrent, and adaptive monitoring system designed to crawl and track recruitment notifications across **83 core Indian public sector, banking, and government portals**, with built-in scalability to support **2,370+ municipal, state, and academic domains** in batches.

The system filters out noise and prioritizes **Computer Science & Engineering (CSE) and IT positions**, sending instant, aggregated alerts via Discord Webhooks and Email notifications when new listings are detected.

---

## Key Features & Architecture

### 1. Unified Layout-Invariant Adaptive Parser
* **Core Engine:** [adaptive_parser.py](file:///c:/Users/Savyasachi%20Mishra/Desktop/Job%20scraper/scraper/adaptive_parser.py)
* **Design:** Adapts to arbitrary HTML layouts without brittle hardcoded CSS selectors.
* **Contextual Link Scoring:** Employs heuristics evaluating link text, URL paths, and anchors with positive boosts (e.g. `recruit`, `vacanc`, `career`, `scientist`, `developer`) and negative penalties (e.g. `tender`, `faq`, `contact`, `login`).
* **Active Proximity Date Finder:** Scrapes nearby DOM sibling and parent text nodes to extract publication dates and deadlines.
* **Self-Healing Exclusions:** Bypasses boilerplate page fragments (like `#nav`) and filters out historical listings (2025 and older) using year/date thresholds and parent archive container detection.

### 2. High-Performance Concurrency & SPAs
* **Fast Concurrent Scrapes:** Leverages a `ThreadPoolExecutor` to query multiple sites in parallel, slashing wall-clock crawl time.
* **Playwright browser integration:** Uses headless Chromium (`spa_scraper.py`) to render modern Single Page Applications (like **RRB Apply**, **DRDO SPA**, **SJVN**, and **CONCOR**) with seamless fallback mechanisms.
* **SSL Renegotiation Bypass:** Utilizes a custom `RobustGovAdapter` (urllib3) to bypass legacy TLS renegotiation blocks and certificate errors on older government servers.

### 3. Scaling & Career Path Seeder
* **Seeder Engine:** [domain_seeder.py](file:///c:/Users/Savyasachi%20Mishra/Desktop/Job%20scraper/scraper/domain_seeder.py)
* **Expanded Targets:** Generates a registry of **2,372 unique target domains** (including 589 district NIC portals, 30+ state departments for all 36 states/UTs, state PSUs, municipal corporations, and regional rural banks).
* **Self-Healing Career Resolver:** Probes homepages dynamically to discover updated career links.
* **Batch Execution:** Supports batching parameters (`--limit`, `--offset`) to run large-scale crawls safely without triggering server blocks.

---

## Directory Structure

```
job-scraper/
├── .github/workflows/
│   └── daily-check.yml       # Automated daily check runner
├── scraper/
│   ├── adaptive_parser.py    # Layout-invariant link-scoring parser
│   ├── domain_seeder.py      # Expanded seed registry of 2,370+ domains
│   ├── config.py             # Core config and 83 main portal metadata
│   ├── crawler.py            # Concurrent crawl controller and strategy router
│   ├── parsers.py            # API-specific and legacy parser fallbacks
│   ├── spa_scraper.py        # Playwright headless chromium SPA handlers
│   ├── filters.py            # Three-tier CSE/IT relevancy engine & date filtering
│   ├── diff.py               # Hashing and state diffing (state.json comparison)
│   ├── notify_discord.py     # Discord Webhook sender logic
│   ├── notify_email.py       # Gmail SMTP sender logic
│   └── main.py               # Orchestrator CLI entry point
├── state.json                # Persisted content hashes (updated by action)
├── seeded_organizations.md   # Searchable markdown database of all 2,370+ seeds
├── relevancy_analysis.md     # Updated signal-to-noise relevancy report
├── all_relevant_jobs.md      # Auto-generated markdown list of active CS/IT jobs
├── requirements.txt          # Python dependencies
└── README.md                 # Setup & configuration guide
```

---

## Target Job Portals (83 Core Channels)
The crawler monitors 83 core agencies including:
* **MeitY & Strategic:** C-DAC, NIELIT, STPI, NIC, C-DOT, CERT-In, SAMEER, ERNET.
* **Defense & Space:** DRDO, ISRO, BARC, BEL, IGCAR, RRCAT, SCL Mohali.
* **Maharatna & Navratna PSUs:** HAL, ECIL, ONGC, SAIL, NTPC, AAI, IOCL, BHEL, Coal India, PGCIL, BPCL, HPCL, GAIL.
* **Banking & Finance:** RBI, SEBI, SBI, IBPS, NABARD, NHB, SIDBI.
* **Commissions & Staff Boards:** UPSC, SSC, DSSSB, RSMSSB, HSSC, and all State Public Service Commissions (UPPSC, MPSC, GPSC, PPSC, etc.).

---

## Configuration & Setup

Add the following four repository secrets in your GitHub repository (**Settings > Secrets and variables > Actions > New repository secret**):

1. `DISCORD_WEBHOOK_URL`: Copy the Webhook URL from your Discord channel integration settings to enable chat alerts.
2. `SMTP_EMAIL`: The Gmail address used to send alerts (e.g. `sender@gmail.com`).
3. `SMTP_APP_PASSWORD`: A 16-character Google App Password (requires 2-Step Verification enabled in Gmail Account settings).
4. `NOTIFY_EMAIL_TO`: The destination email address where job alert emails will be delivered.

---

## Local Development & CLI Usage

To run the pipeline or test the scrapers locally:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install  # Required for SPA scrapers (rrb, concor, sjvn)
```

### 2. Set Up Environment Variables
On Windows (PowerShell):
```powershell
$env:DISCORD_WEBHOOK_URL="your_webhook_url"
$env:SMTP_EMAIL="your_email@gmail.com"
$env:SMTP_APP_PASSWORD="your_app_password"
$env:NOTIFY_EMAIL_TO="recipient_email@gmail.com"
```

### 3. Run Commands

* **Run core scraper (83 main orgs):**
  ```powershell
  python -m scraper.main
  ```

* **Run seeder in batch mode (e.g. first 20 domains):**
  ```powershell
  python -m scraper.main --scale-all --limit 20 --offset 0
  ```

* **Generate signal-to-noise coverage reports:**
  ```powershell
  python -m scraper.main --report-json
  ```

* **Show historical trend metrics:**
  ```powershell
  python -m scraper.main --trend
  ```

* **Watch Mode (continuous monitor, alert on diff):**
  ```powershell
  python -m scraper.main --watch --interval 30
  ```

* **Target a single organization:**
  ```powershell
  python -m scraper.main --org cdac
  ```
