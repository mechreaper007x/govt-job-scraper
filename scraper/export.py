"""
scraper/export.py

Exports scraped job data to a structured JSON file after every run.

Schema:
{
    "generated_at": "<ISO timestamp>",
    "summary": {
        "total":       <int>,   # all postings across all orgs
        "relevant":    <int>,
        "uncertain":   <int>,
        "excluded":    <int>,
        "orgs_scraped": <int>,  # orgs that returned data (not None)
        "orgs_failed":  <int>,
    },
    "orgs": {
        "<org_key>": {
            "name":   "Org Full Name",
            "url":    "https://...",
            "status": "ok" | "failed",
            "jobs": [
                {
                    "title": "...",
                    "link":  "...",
                    "date":  "...",
                    "tier":  "relevant" | "uncertain" | "excluded"
                }
            ]
        }
    }
}

Notes:
- "excluded" tier jobs ARE included — they are marked but not silently dropped.
- Orgs that failed (returned None) appear with status="failed" and an empty jobs list.
- The file is written atomically: JSON is assembled in memory first, then written.
"""

import json
import os
from datetime import datetime

from scraper.config import ORGS_CONFIG, CURATED_ORG_KEYS
from scraper.date_utils import normalize_date


def build_jobs_payload(scraped_data):
    """
    Convert the raw scraper output into the export schema dict.

    Args:
        scraped_data: dict of {org_key -> list[posting_dict] | None}
                      as returned by GovJobCrawler.run_scrape().

    Returns:
        dict conforming to the export schema (ready for json.dump).
    """
    total = relevant = uncertain = excluded = orgs_ok = orgs_failed = 0
    orgs_out = {}

    for org_key, postings in scraped_data.items():
        cfg = ORGS_CONFIG.get(org_key, {})
        name = cfg.get("name", org_key.upper())
        url  = cfg.get("url", "")
        category = "main" if org_key in CURATED_ORG_KEYS else "other"

        if postings is None or not isinstance(postings, list):
            # Org scrape failed — include so the consumer knows it was attempted
            orgs_out[org_key] = {
                "name":     name,
                "url":      url,
                "status":   "failed",
                "category": category,
                "jobs":     [],
            }
            orgs_failed += 1
            continue

        orgs_ok += 1
        jobs_out = []
        for post in postings:
            tier = post.get("relevance", "uncertain")
            jobs_out.append({
                "title":      post.get("title", ""),
                "link":       post.get("link", ""),
                "apply_link": post.get("apply_link", ""),
                "pdf_link":   post.get("pdf_link", ""),
                "date":       post.get("date", ""),
                "date_iso":   post.get("date_iso", "") or normalize_date(post.get("date", "")),
                "tier":       tier,
            })
            total += 1
            if tier == "relevant":
                relevant += 1
            elif tier == "uncertain":
                uncertain += 1
            elif tier == "excluded":
                excluded += 1

        orgs_out[org_key] = {
            "name":     name,
            "url":      url,
            "status":   "ok",
            "category": category,
            "jobs":     jobs_out,
        }

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total":        total,
            "relevant":     relevant,
            "uncertain":    uncertain,
            "excluded":     excluded,
            "orgs_scraped": orgs_ok,
            "orgs_failed":  orgs_failed,
        },
        "orgs": orgs_out,
    }


def save_jobs_json(scraped_data, filepath="scraped_jobs.json"):
    """
    Build the export payload and write it to *filepath* as pretty-printed JSON.

    Args:
        scraped_data: dict of {org_key -> list[posting_dict] | None}
                      as returned by GovJobCrawler.run_scrape().
        filepath:     Output path (default: scraped_jobs.json in CWD).

    Returns:
        str: Absolute path of the file that was written.
    """
    payload  = build_jobs_payload(scraped_data)
    abs_path = os.path.abspath(filepath)

    with open(abs_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    s = payload["summary"]
    print(
        f"Export → {abs_path}  "
        f"({s['total']} jobs: {s['relevant']} relevant, "
        f"{s['uncertain']} uncertain, {s['excluded']} excluded | "
        f"{s['orgs_scraped']} orgs ok, {s['orgs_failed']} failed)"
    )
    return abs_path
