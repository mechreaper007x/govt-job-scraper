# run_all_orgs.py
import scraper.dns_resolver
import argparse
import sys
import os
import io
import contextlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from scraper.domain_seeder import generate_domains, flush_career_url_cache
from scraper.crawler import GovJobCrawler, SERVER_DOWN
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

    keys = sorted([
        k for k in ORGS_CONFIG.keys()
        if k != "drdo_spa" and "duplicate_of" not in ORGS_CONFIG.get(k, {})
    ])
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
    server_down_count = 0
    total_postings = 0
    total_relevant = 0
    failures = []
    server_down_list = []
    scraped_data = {}

    def scrape_worker(index, key):
        nonlocal success_count, fail_count, server_down_count, total_postings, total_relevant
        name = ORGS_CONFIG[key]["name"]
        
        # Truncate name for printing
        short_name = name[:40] + ".." if len(name) > 42 else name
        
        try:
            worker_logs = []
            postings = crawler._scrape_org(key, log_list=worker_logs)

            if postings is SERVER_DOWN:
                # Transient network failure: server unreachable/slow right now.
                # Preserve previous state (don't update diff), don't count as failure.
                status = "Server Down"
                cnt = 0
                rel_cnt = 0
                with lock:
                    server_down_count += 1
                    scraped_data[key] = postings
                err_msg = "".join(worker_logs).strip() or "Network unreachable"
                with failures_lock:
                    server_down_list.append((name, key, err_msg))
            elif postings is None:
                # Code/parsing error — genuine failure worth investigating.
                status = "Fetch Error"
                cnt = 0
                rel_cnt = 0
                with lock:
                    fail_count += 1
                    scraped_data[key] = None
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
                    scraped_data[key] = postings
        except Exception as e:
            status = f"Error"
            cnt = 0
            rel_cnt = 0
            with lock:
                fail_count += 1
                scraped_data[key] = None
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

    # Persist career URL cache once after all workers finish (avoids per-URL I/O contention)
    flush_career_url_cache(crawler.session)

    print("-" * 105, file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)
    print(" CRAWL SUMMARY", file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)
    print(f" Successful Orgs: {success_count}", file=sys.__stdout__)
    print(f" Server Down:     {server_down_count}  (transient — retry later)", file=sys.__stdout__)
    print(f" Fetch Errors:    {fail_count}  (code/parse errors, needs fixing)", file=sys.__stdout__)
    print(f" Total Postings:  {total_postings}", file=sys.__stdout__)
    print(f" CS/IT Relevant:  {total_relevant}", file=sys.__stdout__)
    print("=" * 105, file=sys.__stdout__)

    # Save scraped jobs to json
    from scraper.export import save_jobs_json
    save_jobs_json(scraped_data, filepath="scraped_jobs.json")

    # Generate all_relevant_jobs.md
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
    # Sort relevant_jobs by org name to make it look organized
    relevant_jobs.sort(key=lambda x: (x["org"].lower(), x["title"].lower()))
    
    md_path = "all_relevant_jobs.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# All Relevant CS/IT Government Job Postings\n\n")
        f.write(f"**Total Relevant Postings:** {len(relevant_jobs)}\n\n")
        f.write("| # | Organization | Title | Date | Link |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        
        for idx, j in enumerate(relevant_jobs, 1):
            f.write(f"| {idx} | {j['org']} | {j['title']} | {j['date']} | [Link]({j['url']}) |\n")
    print(f"Updated all_relevant_jobs.md with {len(relevant_jobs)} relevant CS/IT jobs.", file=sys.__stdout__)

    if failures:
        print("\n" + "=" * 105, file=sys.__stdout__)
        print(" FETCH ERROR REPORT  (code/parsing failures — these need fixing)", file=sys.__stdout__)
        print("=" * 105, file=sys.__stdout__)
        for name, key, err in sorted(failures):
            clean_err = err.replace("\n", " | ")
            print(f"- {name} ({key}): {clean_err}", file=sys.__stdout__)
        print("=" * 105, file=sys.__stdout__)

    if server_down_list:
        print("\n" + "=" * 105, file=sys.__stdout__)
        print(" SERVER DOWN REPORT  (transient network failures — will retry on next run)", file=sys.__stdout__)
        print("=" * 105, file=sys.__stdout__)
        for name, key, err in sorted(server_down_list):
            # Only show first line of error to keep report compact
            first_line = err.split("|")[0].strip()[:100]
            print(f"- {name} ({key}): {first_line}", file=sys.__stdout__)
        print("=" * 105, file=sys.__stdout__)

if __name__ == "__main__":
    main()
