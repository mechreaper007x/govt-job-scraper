# scratch/find_maneja.py
import json

with open("scraped_jobs.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for org_key, org_info in data.get("orgs", {}).items():
    for job in org_info.get("jobs", []):
        if "maneja" in job.get("title", "").lower():
            print(f"Org Key: {org_key}")
            print(f"Title: {job.get('title')}")
            print(f"Link: {job.get('link')}")
