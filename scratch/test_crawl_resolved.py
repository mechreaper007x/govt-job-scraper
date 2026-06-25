import sys
sys.path.insert(0, r"c:\Users\Savyasachi Mishra\Desktop\Job scraper")

# Import the patched modules
import scraper.dns_resolver
from scraper.crawler import GovJobCrawler
from scraper.config import ORGS_CONFIG
from scraper.domain_seeder import generate_domains

def main():
    # Generate and merge all domains into config
    seeded = generate_domains()
    for k, v in seeded.items():
        if k not in ORGS_CONFIG:
            v["resolve_career"] = True
            ORGS_CONFIG[k] = v

    crawler = GovJobCrawler()
    
    test_keys = ["iiitbh", "iiitdwd", "iiitu", "iiti", "jntuh", "jntua", "jntuk"]
    
    print(f"{'Key':<15} | {'Organization Name':<45} | {'Result':<10} | {'Count':<5}")
    print("-" * 85)
    
    for key in test_keys:
        if key in ORGS_CONFIG:
            name = ORGS_CONFIG[key]["name"]
            try:
                res = crawler._scrape_org(key)
                status = "Success" if res is not None else "Failed"
                count = len(res) if res is not None else 0
                print(f"{key:<15} | {name[:45]:<45} | {status:<10} | {count:<5}")
            except Exception as e:
                print(f"{key:<15} | {name[:45]:<45} | Error      | {str(e)[:25]}")
        else:
            print(f"{key:<15} | NOT IN CONFIG                                 | -          | -")

if __name__ == "__main__":
    main()
