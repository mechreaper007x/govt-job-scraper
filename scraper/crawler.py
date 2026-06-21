"""
scraper/crawler.py

Main crawler that orchestrates the full job discovery and scraping pipeline.

Pipeline:
  Discover (find URLs) → Fetch (download pages) → Parse (extract listings)
  → Filter (classify relevance) → Diff (track state) → Notify (Discord/Email)

Designed to be the primary entry point. The CLI in main.py delegates here.
Extension points are marked for future Playwright (SPA) and curl_cffi (TLS)
integration without changing the pipeline flow.
"""

import ssl
import sys
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from scraper.config import ORGS_CONFIG, DEFAULT_HEADERS, MAIN_ORGS
import scraper.parsers as parsers
import scraper.discovery as discovery
from scraper.filters import annotate
from scraper.diff import diff_and_update_state
from scraper.notify_discord import send_discord_notifications
from scraper.notify_email import send_email_notifications


# ─── SSL Adapter (shared across all HTTP requests) ───────────────────────────


class RobustGovAdapter(HTTPAdapter):
    """
    SSL adapter for Indian government sites that use:
      - Legacy TLS renegotiation (OP_LEGACY_SERVER_CONNECT)
      - Self-signed or locally-issued certificates (cert_reqs=CERT_NONE)

    Safe for monitoring-only use cases; not for auth/sensitive data.

    Extension point: Replace with curl_cffi's CurlSession for TLS fingerprint
    impersonation when targeting Cloudflare-protected sites.
    """
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context()
        ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
            cert_reqs=ssl.CERT_NONE,
            assert_hostname=False,
        )


# ─── Parser Map ──────────────────────────────────────────────────────────────

# Maps org keys to their parser functions.
# orgs with `None` are handled specially by _scrape_org (e.g. API-based parsers).
PARSER_MAP = {
    "cdac": parsers.parse_cdac,
    "bel": parsers.parse_bel,
    "drdo": parsers.parse_drdo,
    "isro": parsers.parse_isro,
    "barc": parsers.parse_barc,
    "bsnl": parsers.parse_bsnl,
    "certin": parsers.parse_certin,
    "employment_news": parsers.parse_employment_news,
    "cdot": parsers.parse_cdot,
    "uppsc": parsers.parse_uppsc,
    "nielit": None,   # handled via parsers.parse_nielit(session) — internal API
    "ncs": None,      # handled via parsers.parse_ncs(session) — internal API
    "ecil": parsers.parse_ecil,
    "stpi": parsers.parse_stpi,
    "nic": parsers.parse_nic,
    "hal": parsers.parse_hal,
    "cris": parsers.parse_cris,
}


# ─── GovJobCrawler ────────────────────────────────────────────────────────────


class GovJobCrawler:
    """
    Orchestrates the full job discovery-to-notification pipeline.

    Usage:
        crawler = GovJobCrawler()
        crawler.run_pipeline()                   # full pipeline: all orgs
        crawler.run_pipeline(orgs=["cdac"])      # single org
        crawler.run_discovery()                  # discover only
        crawler.run_discovery(orgs=["cdac"])     # discover single org
        crawler.run_scrape()                     # scrape only (no discovery)
    """

    def __init__(self, session=None):
        self.session = session or self._create_session()

    # ── Session factory ─────────────────────────────────────────────────────

    @staticmethod
    def _create_session():
        """
        Create a pre-configured requests.Session with the RobustGovAdapter.

        Extension point: When curl_cffi or httpx-with-fingerprint is added,
        this method can return a duck-typed session-like object that supports
        .get(), .post(), .mount(), and .close().
        """
        session = requests.Session()
        session.mount("https://", RobustGovAdapter())
        return session

    # ── Discovery phase ─────────────────────────────────────────────────────

    def run_discovery(self, orgs=None):
        """
        Phase 1: Discover job-related URLs by checking sitemaps and homepages.

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.

        Returns:
            dict: org_key -> list of discovered candidate URL dicts.
        """
        if orgs is None:
            orgs = MAIN_ORGS

        print("=" * 60)
        print("  CRAWLER — DISCOVERY PHASE")
        print("  Scanning org homepages & sitemaps for job listing URLs")
        print("=" * 60)

        results = discovery.discover_all(self.session, orgs=orgs)

        print("\n" + "=" * 60)
        print("  DISCOVERY SUMMARY")
        print("=" * 60)

        total_found = 0
        for key, candidates in results.items():
            name = ORGS_CONFIG.get(key, {}).get("name", key)
            high = [c for c in candidates if c["score"] >= 50]
            medium = [c for c in candidates if 30 <= c["score"] < 50]

            if candidates:
                print(f"\n{name} ({key}):")
                print(f"  Strong matches: {len(high)}")
                for c in high[:5]:
                    print(f"    [{c['score']:>3}] {c['url'][:90]}")
                if medium:
                    print(f"  Weak matches: {len(medium)}")
                total_found += len(candidates)
            else:
                print(f"\n{name} ({key}): No job-related URLs discovered")

        print(f"\n{'=' * 60}")
        print(f"  Total: {total_found} candidate URLs across {len(orgs)} org(s)")
        print(f"  Review candidates and add new URLs to ORGS_CONFIG in config.py")
        print(f"{'=' * 60}")

        return results

    # ── Scrape phase ────────────────────────────────────────────────────────

    def run_scrape(self, orgs=None):
        """
        Phase 2: Fetch and parse job listings from all configured org URLs.

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.

        Returns:
            dict: org_key -> list of filtered posting dicts (or None on failure).
        """
        if orgs is None:
            orgs = MAIN_ORGS

        print(f"Crawler targeting {len(orgs)} organization(s): {', '.join(orgs)}")

        scraped_data = {}
        for idx, key in enumerate(orgs):
            if idx > 0:
                delay = 4
                print(f"Polite delay: waiting {delay}s before next source...")
                time.sleep(delay)

            postings = self._scrape_org(key)
            scraped_data[key] = postings

        return scraped_data

    def _scrape_org(self, key):
        """
        Scrape a single organization. Handles all fetch strategies:
          - Standard GET + HTML parse
          - NIELIT internal JSON API
          - NCS internal JSON API
          - HAL WordPress POST API
          - BARC RSS feed (bytes)
          - NIC legacy encoding (bytes)

        Extension point: Add Playwright browser scraping for SPAs here.
        """
        if key not in ORGS_CONFIG:
            print(f"  SKIP: {key} not in ORGS_CONFIG")
            return None

        cfg = ORGS_CONFIG[key]
        org_name = cfg["name"]
        url = cfg["url"]
        parser_fn = PARSER_MAP.get(key)
        is_special = cfg.get("special") in ("api", "json_api", "hal_api", "ncs_api")

        if not parser_fn and not is_special:
            print(f"  ERROR: No parser mapped for {org_name} ({key})")
            return None

        print(f"  Fetching {org_name}...", end=" ")

        try:
            # ── Special API-based parsers ────────────────────────────────
            if key == "nielit":
                postings = parsers.parse_nielit(session=self.session)
            elif key == "ncs":
                postings = parsers.parse_ncs(session=self.session)
            elif cfg.get("special") == "hal_api":
                postings = self._fetch_hal(url)
            else:
                # ── Standard HTTP fetch ──────────────────────────────────
                r = self.session.get(url, headers=DEFAULT_HEADERS, timeout=15)
                r.raise_for_status()

                # Some parsers need raw bytes (NIC, BARC)
                content = r.content if key in ("barc", "nic") else r.text
                postings = parser_fn(content)

            # ── Filter by relevance (with per-org context + URL awareness) ─
            annotate(postings, org_key=key, session=self.session)
            filtered = [p for p in postings if p.get("relevance") != "excluded"]
            print(f"{len(filtered)} listings (from {len(postings)})")
            return filtered

        except Exception as exc:
            print(f"ERROR: {exc}")
            return None  # None = failed, preserves state in diff

    def _fetch_hal(self, url):
        """
        Fetch HAL career data via the WordPress REST API.
        The site's WAF blocks requests with default script UA; must send
        browser-like headers to get JSON instead of an HTML block page.

        Extension point: Replace with Playwright for Angular SPA rendering
        when the REST API changes.
        """
        hal_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": "https://hal-india.co.in/",
            "Origin": "https://hal-india.co.in",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = self.session.post(url, headers=hal_headers, json={}, timeout=30)
        r.raise_for_status()
        return parsers.parse_hal(r.text)

    # ── Full pipeline ─────────────────────────────────────────────────────

    def run_pipeline(self, orgs=None, discover_first=False):
        """
        Full pipeline: optionally discover, then scrape, diff, and notify.

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.
            discover_first: If True, run discovery before scraping.

        Returns:
            dict: org_key -> list of new posting dicts from this run.
        """
        if orgs is None:
            orgs = MAIN_ORGS

        if discover_first:
            self.run_discovery(orgs=orgs)
            print("\n" + "─" * 60 + "\n")

        scraped_data = self.run_scrape(orgs=orgs)

        # Diff against previous state
        print()
        new_postings = diff_and_update_state(scraped_data)

        # Notify
        total_new = sum(len(v) for v in new_postings.values())
        if total_new > 0:
            print(f"\nAlert! Detected {total_new} new posting(s).")
            send_discord_notifications(new_postings, ORGS_CONFIG)
            send_email_notifications(new_postings, ORGS_CONFIG)
        else:
            print("\nNo new postings detected. Skipping notifications.")

        return new_postings
