# main.py
# Main orchestrator for government job notification tracker

import sys
import time
import argparse
import requests

from scraper.config import ORGS_CONFIG, DEFAULT_HEADERS, MAIN_ORGS, UPPSC_ORGS
import scraper.parsers as parsers
import scraper.discovery as discovery
from scraper.diff import diff_and_update_state
from scraper.notify_discord import send_discord_notifications
from scraper.notify_email import send_email_notifications
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RobustGovAdapter(HTTPAdapter):
    """
    SSL adapter for Indian government sites that use:
      - Legacy TLS renegotiation (OP_LEGACY_SERVER_CONNECT)
      - Self-signed or locally-issued certificates (cert_reqs=CERT_NONE)
    Safe for monitoring-only use cases; not for auth/sensitive data.
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

# Map configuration keys to their parsing function references
# Note: "nielit" is handled specially below (API-based, not HTML scraping)
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
    "nielit": None,  # special: uses parse_nielit(session) directly
    "ncs": None,  # special: uses parse_ncs(session) via API
    "ecil": parsers.parse_ecil,
    "stpi": parsers.parse_stpi,
    "nic": parsers.parse_nic,
    "hal": parsers.parse_hal,
    "cris": parsers.parse_cris,
}

def main():
    parser = argparse.ArgumentParser(description="Indian Government Job Scraper and Notifier")
    parser.add_argument("--main", action="store_true", help="Run main job scraper across all configured orgs")
    parser.add_argument("--discover", action="store_true", help="Run discovery engine to find new/changed job listing URLs")
    parser.add_argument("--uppsc", action="store_true", help="Run UPPSC job scraper")
    parser.add_argument("--org", type=str, help="Run a specific organization scraper by key")
    
    args = parser.parse_args()
    
    # --discover flag: run URL discovery instead of scraping
    if args.discover:
        session = requests.Session()
        session.mount('https://', RobustGovAdapter())

        print("=" * 60)
        print("  URL DISCOVERY ENGINE")
        print("  Scanning org homepages & sitemaps for job-related URLs")
        print("=" * 60)

        # Determine which orgs to discover
        if args.org:
            if args.org in ORGS_CONFIG:
                discover_keys = [args.org]
            else:
                print(f"Error: Organization '{args.org}' not found.")
                sys.exit(1)
        else:
            discover_keys = MAIN_ORGS

        results = discovery.discover_all(session, orgs=discover_keys)

        print("\n" + "=" * 60)
        print("  DISCOVERY SUMMARY")
        print("=" * 60)

        total_found = 0
        for key, candidates in results.items():
            name = ORGS_CONFIG.get(key, {}).get("name", key)
            high_score = [c for c in candidates if c["score"] >= 50]
            medium_score = [c for c in candidates if 30 <= c["score"] < 50]

            if candidates:
                print(f"\n{name} ({key}):")
                print(f"  Strong matches (score >= 50): {len(high_score)}")
                for c in high_score[:5]:
                    print(f"    [{c['score']:>3}] {c['url'][:90]}")
                if high_score:
                    print(f"    from: {high_score[0]['source']}")
                if medium_score:
                    print(f"  Weak matches (score 30-49): {len(medium_score)}")
                total_found += len(candidates)
            else:
                print(f"\n{name} ({key}): No job-related URLs discovered")

        print(f"\n{'=' * 60}")
        print(f"  Total discovered: {total_found} candidate URLs across {len(discover_keys)} orgs")
        print("  Review candidates and add new URLs to ORGS_CONFIG in config.py")
        print(f"{'=' * 60}")
        return

    # Determine the target organizations based on arguments
    if args.org:
        if args.org in ORGS_CONFIG:
            target_keys = [args.org]
        else:
            print(f"Error: Organization '{args.org}' not found in configuration.")
            sys.exit(1)
    elif args.main:
        target_keys = MAIN_ORGS
    elif args.uppsc:
        target_keys = UPPSC_ORGS
    else:
        # If no arguments are provided, check everything in configuration
        target_keys = list(ORGS_CONFIG.keys())
        
    print(f"Targeting organizations: {', '.join(target_keys)}")
    
    session = requests.Session()
    session.mount('https://', RobustGovAdapter())
    
    scraped_data = {}
    
    for idx, key in enumerate(target_keys):
        org_name = ORGS_CONFIG[key]["name"]
        url = ORGS_CONFIG[key]["url"]
        parser_fn = PARSER_MAP.get(key)
        
        # NIELIT/NCS use None in PARSER_MAP as sentinels (handled by special API paths below)
        is_special_api = ORGS_CONFIG[key].get("special") in ("api", "json_api", "hal_api", "ncs_api")
        if not parser_fn and not is_special_api:
            print(f"Error: No parser function mapped for {org_name} ({key})")
            continue
            
        # Politely wait 3-5 seconds between targets to respect servers (except the first request)
        if idx > 0:
            delay = 4  # 4 seconds delay satisfies the 3-5s requirement
            print(f"Polite delay: waiting {delay} seconds before scraping next source...")
            time.sleep(delay)
            
        print(f"Fetching URL for {org_name}: {url}")
        try:
            # NIELIT uses an internal JSON API (React SPA backend) — no static HTML to GET
            if key == "nielit":
                postings = parsers.parse_nielit(session=session)
            elif key == "ncs":
                # NCS uses the beta portal's internal job search API (POST)
                postings = parsers.parse_ncs(session=session)
            elif ORGS_CONFIG[key].get("special") == "hal_api":
                # HAL uses a custom WordPress POST API. The site's WAF blocks
                # requests with the default script-style User-Agent and returns
                # an "Unauthorized Request Blocked" HTML page instead of JSON,
                # so we must send browser-like headers (Chrome UA + Referer +
                # Origin + Accept) to get the actual career listing JSON.
                hal_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Referer": "https://hal-india.co.in/",
                    "Origin": "https://hal-india.co.in",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                r = session.post(url, headers=hal_headers, json={}, timeout=30)
                r.raise_for_status()
                postings = parsers.parse_hal(r.text)
            else:
                r = session.get(url, headers=DEFAULT_HEADERS, timeout=15)
                r.raise_for_status()

                # Feedparser can decode bytes itself; BeautifulSoup handles HTML strings
                # HAL's parser receives raw JSON text from the WP REST API
                # NIC uses windows-1251 charset; pass bytes to avoid decode errors
                content = r.content if key in ("barc", "nic") else r.text

                parser_fn = PARSER_MAP.get(key)
                if not parser_fn:
                    print(f"Error: No parser function mapped for {org_name} ({key})")
                    continue

                postings = parser_fn(content)

            from scraper.filters import annotate
            annotate(postings)
            filtered_postings = [p for p in postings if p.get("relevance") != "excluded"]
            scraped_data[key] = filtered_postings
            print(f"Successfully scraped {len(filtered_postings)} listings (filtered from {len(postings)}) for {org_name}.")
        except Exception as e:
            # Wrap in try/except for error isolation (one failure must not block others)
            print(f"ERROR: Scraper failed for {org_name} ({key}): {e}")
            scraped_data[key] = None  # None indicates failure, preserving its state in state.json
            
    # Compute diff and update state.json
    new_postings = diff_and_update_state(scraped_data)
    
    # Calculate count of new entries
    total_new = sum(len(listings) for listings in new_postings.values())
    
    if total_new > 0:
        print(f"\nAlert! Detected {total_new} new postings in total.")
        send_discord_notifications(new_postings, ORGS_CONFIG)
        send_email_notifications(new_postings, ORGS_CONFIG)
    else:
        print("\nNo new postings detected. Skipping notifications.")

if __name__ == "__main__":
    main()
