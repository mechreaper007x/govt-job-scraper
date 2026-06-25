# run_all_orgs.py
import scraper.dns_resolver
import argparse
import sys
import os
import io
import contextlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper.domain_seeder import generate_domains
from scraper.crawler import GovJobCrawler
from scraper.config import ORGS_CONFIG

def main():
    import os
    os.environ["SCALE_CRAWL"] = "1"
    
    parser = argparse.ArgumentParser(description="Run scraper for all 2,300+ organizations and display results in tabular form")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of organizations to crawl")
    parser.add_argument("--offset", type=int, default=0, help="Offset for starting crawl")
    parser.add_argument("--workers", type=int, default=20, help="Number of concurrent scraper workers")
    args = parser.parse_args()

    # Generate all domains
    seeded = generate_domains()
    # Merge into ORGS_CONFIG
    for k, v in seeded.items():
        if k not in ORGS_CONFIG:
            v["resolve_career"] = True
            ORGS_CONFIG[k] = v

    keys = sorted(list(seeded.keys()))
    start = args.offset
    end = (start + args.limit) if args.limit is not None else len(keys)
    target_keys = keys[start:end]

    print("=" * 105, file=sys.__stdout__)
    print(f" Crawling {len(target_keys)} organization(s) (Range: {start} to {end} out of {len(keys)})", file=sys.__stdout__)
    print(f" Concurrency: {args.workers} workers", file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)

    # Table format
    fmt = "| {:<5} | {:<42} | {:<16} | {:<12} | {:<8} |"
    header = fmt.format("Num", "Organization Name", "Status/Result", "Total Posts", "CS/IT")
    print(header, file=sys.__stdout__)
    print("-" * 105, file=sys.__stdout__)

    crawler = GovJobCrawler()
    lock = threading.Lock()
    failures_lock = threading.Lock()
    
    success_count = 0
    fail_count = 0
    total_postings = 0
    total_relevant = 0
    failures = []

    def scrape_worker(index, key):
        nonlocal success_count, fail_count, total_postings, total_relevant
        name = ORGS_CONFIG[key]["name"]
        
        # Truncate name for printing
        short_name = name[:40] + ".." if len(name) > 42 else name
        
        try:
            worker_logs = []
            postings = crawler._scrape_org(key, log_list=worker_logs)
                
            if postings is None:
                status = "Fetch Error"
                cnt = 0
                rel_cnt = 0
                with lock:
                    fail_count += 1
                err_msg = "".join(worker_logs).strip() or "Unknown Fetch Error"
                with failures_lock:
                    failures.append((name, key, err_msg))
            else:
                status = "Success"
                cnt = len(postings)
                rel_cnt = sum(1 for p in postings if p.get("relevance") == "relevant")
                with lock:
                    success_count += 1
                    total_postings += cnt
                    total_relevant += rel_cnt
        except Exception as e:
            status = f"Error"
            cnt = 0
            rel_cnt = 0
            with lock:
                fail_count += 1
            with failures_lock:
                failures.append((name, key, f"Crashed: {e}"))
                
        # Print row directly to raw stdout stream to bypass global redirection
        row = fmt.format(index + 1, short_name, status, cnt, rel_cnt)
        with lock:
            print(row, file=sys.__stdout__)

    # Run in ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(scrape_worker, i + start, key): key for i, key in enumerate(target_keys)}
        for future in as_completed(futures):
            pass

    print("-" * 105, file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)
    print(" CRAWL SUMMARY", file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)
    print(f" Successful Orgs: {success_count}", file=sys.__stdout__)
    print(f" Failed Orgs:     {fail_count}", file=sys.__stdout__)
    print(f" Total Postings:  {total_postings}", file=sys.__stdout__)
    print(f" CS/IT Relevant:  {total_relevant}", file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)

    if failures:
        print("\n" + "=" * 105, file=sys.__stdout__)
        print(" DETAILED FAILURE REPORT", file=sys.__stdout__)
        print("=" * 105, file=sys.__stdout__)
        for name, key, err in sorted(failures):
            clean_err = err.replace("\n", " | ")
            print(f"- {name} ({key}): {clean_err}", file=sys.__stdout__)
        print("=" * 105, file=sys.__stdout__)

if __name__ == "__main__":
    main()
