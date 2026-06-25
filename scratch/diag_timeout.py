"""Diagnostic: what does ReadTimeout look like in our session?"""
import os, sys
os.environ["SCALE_CRAWL"] = "1"
sys.path.insert(0, ".")

from scraper.crawler import GovJobCrawler, SERVER_DOWN
from scraper.config import ORGS_CONFIG
from scraper.domain_seeder import generate_domains
import requests.exceptions as rex

seeded = generate_domains()
for k, v in seeded.items():
    if k not in ORGS_CONFIG:
        v["resolve_career"] = True
        ORGS_CONFIG[k] = v

c = GovJobCrawler()

# Test with a short timeout to force ReadTimeout quickly
try:
    r = c.session.get("https://kpsc.kar.nic.in/", timeout=5)
except Exception as exc:
    print(f"Exception type: {type(exc).__name__}")
    print(f"Exception MRO: {[t.__name__ for t in type(exc).__mro__]}")
    print(f"str(exc)[:120]: {str(exc)[:120]}")
    print()
    err_str = str(exc)
    sigs = ["readtimeout", "read timed out", "connecttimeouterror", "max retries exceeded", "read timeout"]
    for s in sigs:
        print(f'  "{s}" in err_str.lower(): {s in err_str.lower()}')
    print()
    print(f"  isinstance ReadTimeout: {isinstance(exc, rex.ReadTimeout)}")
    print(f"  isinstance Timeout:     {isinstance(exc, rex.Timeout)}")
    print(f"  isinstance ConnError:   {isinstance(exc, rex.ConnectionError)}")
