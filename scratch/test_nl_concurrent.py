"""Concurrent NL test — validates SLD-level locking prevents server overload."""
import os, sys, threading
os.environ['SCALE_CRAWL'] = '1'
sys.path.insert(0, '.')

from scraper.crawler import GovJobCrawler, SERVER_DOWN
from scraper.config import ORGS_CONFIG
from scraper.domain_seeder import generate_domains

seeded = generate_domains()
for k, v in seeded.items():
    if k not in ORGS_CONFIG:
        v['resolve_career'] = True
        ORGS_CONFIG[k] = v

c = GovJobCrawler()
results = {}
lock = threading.Lock()

def test(key):
    logs = []
    r = c._scrape_org(key, log_list=logs)
    with lock:
        if r is SERVER_DOWN:
            results[key] = 'SERVER_DOWN'
        elif r is None:
            results[key] = 'Fetch Error'
        else:
            results[key] = f'Success({len(r)})'

# Run ALL NL orgs concurrently — this is the scenario that was causing timeouts
nl_orgs = [k for k in ORGS_CONFIG if k.startswith('nl_') or k in ('nlpsc', 'nlssc')]
print(f'Testing {len(nl_orgs)} NL orgs concurrently: {nl_orgs}')
threads = [threading.Thread(target=test, args=(k,)) for k in nl_orgs]
for t in threads:
    t.start()
for t in threads:
    t.join()

for k, v in sorted(results.items()):
    print(f'  {k}: {v}')

fetch_errors = sum(1 for v in results.values() if v == 'Fetch Error')
print(f'Fetch Errors: {fetch_errors}')
print('PASS' if fetch_errors == 0 else 'FAIL')
