"""
Re-test server-down orgs with short per-request timeouts.
Classifies each as: transient (recovered), still-down, or code-error.
"""
import sys
import io
import time
import requests
from urllib3.exceptions import ConnectTimeoutError

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

import scraper.dns_resolver
from scraper.domain_seeder import generate_domains
from scraper.config import ORGS_CONFIG, DEFAULT_HEADERS
from scraper.crawler import GovJobCrawler, SERVER_DOWN

# Generate seeded domains and merge
seeded = generate_domains()
for k, v in seeded.items():
    if k not in ORGS_CONFIG:
        ORGS_CONFIG[k] = v

# Server-down names from the full crawl
SERVER_DOWN_NAMES = [
    "Angul District Portal", "BANKOFBARODA", "BR PSC", "CG Staff Selection Board",
    "CGPSC", "DBTINDIA", "DD Police Recruitment", "FINMIN",
    "GA Coop Department", "GA PSC", "GA Socialwelfare Department", "GA Urban Department",
    "JH Staff Selection Board", "JH Tourism Department", "JK Road Transport Corp",
    "KA PSC", "KA Staff Selection Board", "KL Police Recruitment",
    "Lakhimpur District Portal", "MAHABANK", "MCC KA Municipal Corporation",
    "MH Industries Department", "MP Tribal Department", "NITJSR",
    "NL Tourism Department", "OD Science Department", "PB Transport Department",
    "PY Road Transport Corp", "RINL", "VUDA Municipal Corporation",
    "WB Fisheries Department", "WBGB",
]

def find_keys(names):
    """Match names to org keys."""
    result = []
    for name in names:
        found = False
        for k, v in ORGS_CONFIG.items():
            if v.get("name", "") == name:
                result.append((name, k))
                found = True
                break
        if not found:
            name_lower = name.lower()
            for k, v in ORGS_CONFIG.items():
                if name_lower in v.get("name", "").lower():
                    result.append((name, k))
                    found = True
                    break
        if not found:
            print(f"  NOT FOUND: {name}")
    return result


def quick_check(url, timeout=8):
    """Quick HTTP HEAD/GET to check if site is reachable."""
    try:
        r = requests.get(url, timeout=timeout, verify=False,
                         headers=DEFAULT_HEADERS, allow_redirects=True)
        return r.status_code, None
    except requests.exceptions.Timeout:
        return None, "Timeout"
    except requests.exceptions.ConnectionError as e:
        err = str(e)[:100]
        return None, f"ConnectionError: {err}"
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:80]}"


def main():
    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    names = SERVER_DOWN_NAMES

    # Find keys
    pairs = find_keys(names)
    print(f"Testing {len(pairs)} server-down orgs (batch {batch})...")
    print("=" * 90)

    crawler = GovJobCrawler()
    transient_ok = []
    still_down = []
    code_error = []

    for i, (name, key) in enumerate(pairs):
        url = ORGS_CONFIG[key].get("url", "N/A")
        print(f"\n[{i+1}/{len(pairs)}] {name} ({key})")
        print(f"  URL: {url}")

        # Quick HTTP check first (2s timeout)
        status, err = quick_check(url, timeout=5)
        if status is not None:
            print(f"  HTTP check: {status}")
        else:
            print(f"  HTTP check: FAIL - {err}")

        # Now do full scrape
        try:
            logs = []
            postings = crawler._scrape_org(key, log_list=logs)
            log_text = "".join(logs).strip()

            if postings is SERVER_DOWN:
                print(f"  Scrape: STILL SERVER DOWN")
                # Extract the error from logs
                for line in log_text.split("\n"):
                    if "ERROR" in line or "error" in line.lower():
                        print(f"  Error: {line[:150]}")
                still_down.append((name, key, url, err or "server-down"))
            elif postings is None:
                print(f"  Scrape: CODE ERROR")
                print(f"  Logs: {log_text[:150]}")
                code_error.append((name, key, url, log_text[:150]))
            else:
                cnt = len(postings)
                print(f"  Scrape: OK! {cnt} listings")
                transient_ok.append((name, key, url, cnt))
        except Exception as e:
            print(f"  Scrape: CRASHED - {e}")
            code_error.append((name, key, url, str(e)[:150]))

        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 90)
    print("CLASSIFICATION SUMMARY")
    print("=" * 90)

    print(f"\n✅ TRANSIENT (recovered on retry): {len(transient_ok)}")
    for name, key, url, cnt in transient_ok:
        print(f"   {name} ({key}) - {cnt} listings")

    print(f"\n❌ STILL DOWN (persistent): {len(still_down)}")
    for name, key, url, reason in still_down:
        print(f"   {name} ({key})")
        print(f"     URL: {url}")
        print(f"     Reason: {reason}")

    print(f"\n⚠️  CODE ERRORS: {len(code_error)}")
    for name, key, url, err in code_error:
        print(f"   {name} ({key})")
        print(f"     URL: {url}")
        print(f"     Error: {err}")


if __name__ == "__main__":
    main()
