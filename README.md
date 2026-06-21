# Indian Government Job Notification Tracker

A Python-based monitoring system that automatically scans a fixed list of Indian government and PSU recruitment portals once a day. It identifies *new* job notifications via content hashing and alerts you instantly via a Discord Webhook and Email.

The system runs entirely on **GitHub Actions free tier**, requiring no server of your own, and persists its state by committing an updated `state.json` file back to the repository.

---

## Architecture & Features

- **CSE / IT Relevance Filtering:** Design optimized specifically for Computer Science & Engineering (CSE) and IT postings. Employs a three-tier relevance check (`relevant`, `excluded`, `uncertain`) to ensure no potential CSE/IT jobs are silently dropped. Vague/general recruitment titles (e.g., general "Scientist B" posts) are classified as `uncertain` and surfaced with a warning flag (⚠️) instead of being excluded.
- **Automated Scanning:** Daily runs on GitHub Actions (at `11:30 AM IST` / `06:00 UTC`). Manual run triggers are also configured (`workflow_dispatch`).
- **Resilient Checking & SSL Renegotiation:** Individual site scrapes are isolated inside `try/except` blocks. Features a custom HTTP `LegacyAdapter` mapping that bypasses OpenSSL TLS errors encountered on older government webservers (such as C-DOT). If one site goes offline, it does not block the check for the rest of the portals.
- **State Persistence:** A root-level `state.json` tracks hashes of previously scanned posts. If state changes, GitHub Actions automatically commits the changes back to your repository.
- **Batched Notifications:** Rather than flooding your inbox or chat, all new postings from a single run are batched and delivered as a single clean alert.
- **Polite Crawling:** Implements delays between scraping different targets to avoid overloading servers, and strictly respects `robots.txt` instructions.

---

## Directory Structure

```
govt-job-tracker/
├── .github/workflows/
│   ├── daily-check.yml       # Scrapes CDAC, BEL, DRDO, ISRO, BARC, BSNL, CERT-In, Employment News, C-DOT
│   └── uppsc-check.yml       # Isolated scraper workflow for UPPSC
├── scraper/
│   ├── config.py             # Target URLs and basic user-agent headers
│   ├── parsers.py            # Site-specific BeautifulSoup parsing functions
│   ├── filters.py            # Three-tier CSE/IT relevance classification logic
│   ├── diff.py               # Hashing and state diffing (state.json comparison)
│   ├── notify_discord.py     # Discord Webhook sender logic
│   ├── notify_email.py       # Gmail SMTP sender logic
│   └── main.py               # Orchestrator entry point (with CLI support)
├── state.json                # Persisted content hashes (updated by action)
├── MANUAL_CHECK.md           # Reminder urls for portals blocking scrapers (SSC, NIC)
├── requirements.txt          # Python dependencies
└── README.md                 # Setup & configuration guide
```

---

## Target Job Portals

1. **C-DAC:** `Current Openings`, `Rolling Advertisements`, and `Notifications`.
2. **BEL (Bharat Electronics Limited):** WordPress job notification cards.
3. **DRDO:** Drupal vacancy grids.
4. **ISRO:** Opportunities table layout.
5. **BARC:** Scrapes the official RSS feed for `New Vacancies` and `Results`, with HTML table fallback.
6. **BSNL:** Active exams and registration forms on the BSNL external exam portal.
7. **UPPSC:** Home page "What's New" announcements (avoiding Candidate postbacks).
8. **CERT-In (Indian Computer Emergency Response Team):** Recruitment page containing cybersecurity and IT vacancies.
9. **Employment News (MIB):** Supplementary aggregator of central government recruitment ads.
10. **C-DOT (Centre for Development of Telematics):** Current openings table layout. Uses custom SSL legacy renegotiation support for compatibility with older government servers.

---

## Configuration & Setup

To make the tracker work, you need to set up a few repository secrets in your GitHub repository. Go to **Settings > Secrets and variables > Actions > New repository secret** and add the following four secrets:

### 1. Discord Webhook Setup (`DISCORD_WEBHOOK_URL`)
To get job alerts sent to a Discord channel:
1. Open your Discord server, right-click on the target channel, and select **Edit Channel**.
2. Go to **Integrations** > **Webhooks** > **New Webhook**.
3. Copy the **Webhook URL**.
4. Paste it as a secret named `DISCORD_WEBHOOK_URL` in your GitHub repository.

### 2. Gmail App Password Setup (`SMTP_EMAIL` and `SMTP_APP_PASSWORD`)
The system sends email alerts via Google's secure SMTP servers.
1. Log in to the Google account you wish to send emails from.
2. Go to **Google Account Settings** > **Security**.
3. Under **How you sign in to Google**, ensure **2-Step Verification** is enabled.
4. Click on **2-Step Verification**, scroll to the bottom, and select **App passwords**.
5. Generate an app password for `Mail` / `Other` and name it `Job Scraper`.
6. Copy the generated 16-character password (without spaces).
7. In your GitHub repository, create two secrets:
   - `SMTP_EMAIL`: Your full Gmail address (e.g. `sender@gmail.com`).
   - `SMTP_APP_PASSWORD`: The 16-character app password.

### 3. Destination Address (`NOTIFY_EMAIL_TO`)
Add the destination email where alerts should be sent:
- Create a secret named `NOTIFY_EMAIL_TO` with the target email address (this can be the same as your `SMTP_EMAIL`).

---

## Local Development & Testing

To test the scrapers or notifications locally on your machine:

1. Clone the repository and navigate into it.
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your local environment variables:
   ```bash
   # On Windows (PowerShell)
   $env:DISCORD_WEBHOOK_URL="your_webhook_url"
   $env:SMTP_EMAIL="your_email@gmail.com"
   $env:SMTP_APP_PASSWORD="your_app_password"
   $env:NOTIFY_EMAIL_TO="recipient_email@gmail.com"
   ```
4. Run the scraper:
   - **Check all portals:** `python scraper/main.py`
   - **Check main scrapers only:** `python scraper/main.py --main`
   - **Check UPPSC scraper only:** `python scraper/main.py --uppsc`
   - **Check a single specific portal:** `python scraper/main.py --org cdac`
