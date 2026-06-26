# scratch/test_job_classification.py
import json
import os
import sys
import re

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.filters import classify
from scraper.config import ORGS_CONFIG
from scraper.domain_seeder import generate_domains

def main():
    json_path = "scraped_jobs.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Initialize dynamic org configs
    seeded = generate_domains()
    for k, v in seeded.items():
        if k not in ORGS_CONFIG:
            ORGS_CONFIG[k] = v

    total_scraped = 0
    relevant_count = 0
    excluded_count = 0
    uncertain_count = 0
    
    relevant_jobs = []
    
    for org_key, org_info in data.get("orgs", {}).items():
        org_name = org_info.get("name", org_key)
        for job in org_info.get("jobs", []):
            total_scraped += 1
            title = job.get("title", "")
            link = job.get("link", "")
            
            res = classify(title, link=link, org_key=org_key)
            
            if res == "relevant":
                relevant_count += 1
                relevant_jobs.append((org_name, title, link))
            elif res == "excluded":
                excluded_count += 1
            else:
                uncertain_count += 1

    print("\n==================================================")
    print(" CLASSIFICATION RUN SUMMARY WITH HYBRID EMBEDDINGS")
    print("==================================================")
    print(f" Total Postings Scraped: {total_scraped}")
    print(f" Relevant CS/IT:        {relevant_count}")
    print(f" Excluded:              {excluded_count}")
    print(f" Uncertain:             {uncertain_count}")
    print("==================================================")

    # Print the relevant listings
    print("\nCURATED RELEVANT LISTINGS:")
    for idx, (org, title, link) in enumerate(relevant_jobs, 1):
        safe_title = title.encode("ascii", errors="replace").decode("ascii")
        safe_org = org.encode("ascii", errors="replace").decode("ascii")
        print(f" {idx:2d}. {safe_org} | {safe_title}")

if __name__ == "__main__":
    main()
