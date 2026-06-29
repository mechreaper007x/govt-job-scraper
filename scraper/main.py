# main.py
# Thin CLI wrapper that delegates all work to GovJobCrawler.
#
# Usage:
#   python -m scraper.main --main           # scrape all orgs (default)
#   python -m scraper.main --discover       # discover new URLs
#   python -m scraper.main --org cdac       # single org scrape
#   python -m scraper.main --discover --org cdac  # single org discovery

import scraper.dns_resolver
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
        "--report", action="store_true",
        help="Run scrape and generate CS/IT coverage report (signal vs noise)"
    )
    parser.add_argument(
        "--report-json", nargs="?", const="coverage_report.json", default=None,
        metavar="FILE",
        help="Export coverage report to JSON (default: coverage_report.json)"
    )
    parser.add_argument(
        "--report-archive", nargs="?", const="coverage_history.json", default=None,
        metavar="FILE",
        help="Run scrape, generate report, and append to historical archive"
    )
    parser.add_argument(
        "--trend", action="store_true",
        help="Show historical accuracy trends from the coverage archive"
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Watch mode: re-scrape every N minutes and alert on new postings"
    )
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Minutes between watch mode cycles (default: 30)"
    )
    parser.add_argument(
        "--uppsc", action="store_true",
        help="Run UPPSC job scraper"
    )
    parser.add_argument(
        "--org", type=str,
        help="Run a specific organization scraper by key"
    )
    parser.add_argument(
        "--scale-all", action="store_true",
        help="Run the seeder and crawl all 2,500+ discovered portals in batches"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit the number of domains processed in --scale-all mode"
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Starting offset for domains processed in --scale-all mode"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run scraper for all curated organizations in ORGS_CONFIG"
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
    elif args.all:
        target_keys = sorted([k for k in ORGS_CONFIG.keys() if k != "drdo_spa"])
    elif args.scale_all:
        import os
        os.environ["SCALE_CRAWL"] = "1"
        from scraper.domain_seeder import generate_domains
        seeded_domains = generate_domains()
        # Merge seeded_domains into ORGS_CONFIG and mark them for career URL resolution
        for k, v in seeded_domains.items():
            if k not in ORGS_CONFIG:
                v["resolve_career"] = True
                ORGS_CONFIG[k] = v
        all_keys = sorted([
            k for k in ORGS_CONFIG.keys()
            if k != "drdo_spa" and "duplicate_of" not in ORGS_CONFIG.get(k, {})
        ])
        start = args.offset
        end = (start + args.limit) if args.limit is not None else len(all_keys)
        target_keys = all_keys[start:end]
        print(f"Scaling to all portals. Batch range: {start} to {end} (out of {len(all_keys)} total)")
    else:
        target_keys = MAIN_ORGS

    # ── Instantiate crawler and run ────────────────────────────────────────
    crawler = GovJobCrawler()

    if args.discover:
        crawler.run_discovery(orgs=target_keys)
        return  # discovery only, no scrape/diff/notify

    if args.report:
        report = crawler.generate_report(orgs=target_keys)
        crawler.print_report(report)
        return  # report only, no diff/notify

    if args.report_json is not None:
        report = crawler.generate_report(orgs=target_keys)
        crawler.print_report(report)
        crawler.save_report_json(report, path=args.report_json)
        return  # report only, no diff/notify

    if args.report_archive is not None:
        report = crawler.generate_report(orgs=target_keys)
        crawler.print_report(report)
        crawler.archive_report(report, path=args.report_archive)
        return

    if args.trend:
        crawler.print_trend()
        return

    if args.watch:
        crawler.run_watch(orgs=target_keys, interval_minutes=args.interval)
        return  # watch runs indefinitely until Ctrl+C

    # ── Scrape pipeline (single run) ──────────────────────────────────────
    max_workers = 20 if len(target_keys) > 10 else 4
    scraped_data = crawler.run_scrape(orgs=target_keys, max_workers=max_workers)

    # ── Generate all_relevant_jobs.md ─────────────────────────────────────
    try:
        relevant_jobs = []
        for org_key, postings in scraped_data.items():
            if postings and isinstance(postings, list):
                org_name = ORGS_CONFIG.get(org_key, {}).get("name", org_key.upper())
                for post in postings:
                    if post.get("relevance") == "relevant":
                        relevant_jobs.append({
                            "org": org_name,
                            "title": post.get("title", ""),
                            "date": post.get("date", "") or "-",
                            "url": post.get("link", "")
                        })
        relevant_jobs.sort(key=lambda x: (x["org"].lower(), x["title"].lower()))
        with open("all_relevant_jobs.md", "w", encoding="utf-8") as f:
            f.write("# All Relevant CS/IT Government Job Postings\n\n")
            f.write(f"**Total Relevant Postings:** {len(relevant_jobs)}\n\n")
            f.write("| # | Organization | Title | Date | Link |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for idx, j in enumerate(relevant_jobs, 1):
                f.write(f"| {idx} | {j['org']} | {j['title']} | {j['date']} | [Link]({j['url']}) |\n")
        print(f"Generated all_relevant_jobs.md with {len(relevant_jobs)} relevant CS/IT jobs.")
    except Exception as e:
        print(f"Warning: Failed to generate all_relevant_jobs.md ({e})")

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
