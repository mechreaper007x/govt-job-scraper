# main.py
# Thin CLI wrapper that delegates all work to GovJobCrawler.
#
# Usage:
#   python -m scraper.main --main           # scrape all orgs (default)
#   python -m scraper.main --discover       # discover new URLs
#   python -m scraper.main --org cdac       # single org scrape
#   python -m scraper.main --discover --org cdac  # single org discovery

import sys
import argparse

from scraper.crawler import GovJobCrawler
from scraper.config import ORGS_CONFIG, MAIN_ORGS, UPPSC_ORGS


def main():
    parser = argparse.ArgumentParser(
        description="Indian Government Job Scraper and Notifier"
    )
    parser.add_argument(
        "--main", action="store_true",
        help="Run main job scraper across all configured orgs"
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Run discovery engine to find new/changed job listing URLs"
    )
    parser.add_argument(
        "--uppsc", action="store_true",
        help="Run UPPSC job scraper"
    )
    parser.add_argument(
        "--org", type=str,
        help="Run a specific organization scraper by key"
    )

    args = parser.parse_args()

    # ── Determine target orgs ──────────────────────────────────────────────
    if args.org:
        if args.org not in ORGS_CONFIG:
            print(f"Error: Organization '{args.org}' not found in configuration.")
            sys.exit(1)
        target_keys = [args.org]
    elif args.uppsc:
        target_keys = UPPSC_ORGS
    else:
        target_keys = MAIN_ORGS

    # ── Instantiate crawler and run ────────────────────────────────────────
    crawler = GovJobCrawler()

    if args.discover:
        crawler.run_discovery(orgs=target_keys)
        return  # discovery only, no scrape/diff/notify

    # ── Scrape pipeline (single run) ──────────────────────────────────────
    scraped_data = crawler.run_scrape(orgs=target_keys)

    # ── Diff + Notify ─────────────────────────────────────────────────────
    from scraper.diff import diff_and_update_state
    from scraper.notify_discord import send_discord_notifications
    from scraper.notify_email import send_email_notifications

    new_postings = diff_and_update_state(scraped_data)
    total_new = sum(len(v) for v in new_postings.values())

    if total_new > 0:
        print(f"\nAlert! Detected {total_new} new posting(s).")
        send_discord_notifications(new_postings, ORGS_CONFIG)
        send_email_notifications(new_postings, ORGS_CONFIG)
    else:
        print("\nNo new postings detected. Skipping notifications.")


if __name__ == "__main__":
    main()
