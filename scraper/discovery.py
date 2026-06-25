"""
scraper/discovery.py

Lightweight URL discovery layer for government job portals.

For each registered org, the discovery engine:
  1. Checks /sitemap.xml (if reachable) for job-related URLs
  2. Crawls each configured homepage (depth 1) extracting same-domain links
  3. Scores candidate URLs by how strongly they match career/job/recruitment patterns

Output: discovered candidate URLs that can be reviewed and added to ORGS_CONFIG.

Designed to be polite — single session, delays between fetches, respects
connection timeouts, skips binary/content downloads.
"""

import re
import sys
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from scraper.config import DISCOVERY_CONFIG, DEFAULT_HEADERS

# Ensure stdout can handle UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _same_domain(url_a, url_b):
    """Return True if both URLs share the same netloc."""
    try:
        return urlparse(url_a).netloc == urlparse(url_b).netloc
    except Exception:
        return False


def _score_link(url_text, link_text, patterns):
    """
    Score a (url, link_text) pair against the org's career-related regex patterns.

    Returns a score 0-100:
      - +40 if any pattern matches the URL path
      - +30 if any pattern matches the link text
      - +30 if the padded link text contains common job-related English/Hindi keywords
      - -20 penalty if URL contains "tender", "grievance", "rti", "contact"
        (these are common govt site sections unrelated to jobs)
    """
    score = 0
    url_lower = url_text.lower()
    link_lower = link_text.lower()
    # Pad link text so word-boundary-ish substrings match cleanly
    # (like classify() does in filters.py)
    padded = f" {link_lower} "

    for pattern in patterns:
        if re.search(pattern, url_lower):
            score += 40
            break

    for pattern in patterns:
        if re.search(pattern, link_lower):
            score += 30
            break

    # Bonus keywords in padded link text
    bonus = [
        "apply", "openings", "positions", "current", "notification",
        "advertisement", "advt", "engagement", "hiring",
        "naukri", "bharti", "recruitment", "vacancy", "vacancies",
    ]
    for kw in bonus:
        if kw in padded:
            score += 20
            break

    # Negative signals in URL or padded text
    penalty = ["tender", "grievance", "rti", "contact us", "feedback", "sitemap"]
    for kw in penalty:
        if kw in url_lower or kw in padded:
            score -= 20
            break

    return max(0, score)


def _extract_title(soup):
    """Extract page title from BeautifulSoup object."""
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def _is_html(r):
    """Return True if response looks like HTML content."""
    ct = (r.headers.get("Content-Type", "") or "").lower()
    return "text/html" in ct or "application/xhtml" in ct


def _skip_url(url):
    """Return True if URL should be skipped (binary, anchor-only, etc.)."""
    skip_exts = (
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
        ".mp3", ".mp4", ".avi", ".mov",
    )
    path = urlparse(url).path.lower()
    if path.endswith(skip_exts):
        return True
    # Skip hash-only fragments
    if url.startswith("#"):
        return True
    return False


# ─── Sitemap parser ──────────────────────────────────────────────────────────


def _parse_sitemap(xml_text, patterns):
    """
    Extract URLs from XML sitemap that match the org's patterns.

    Handles both standard sitemap and sitemap index (nested sitemaps).
    Since we only fetch the top-level sitemap, we just extract direct URLs.

    Uses 'xml' parser (lxml) if available; falls back to 'html.parser' which
    handles most sitemap XML adequately for tag-based extraction.
    """
    results = []
    try:
        soup = BeautifulSoup(xml_text, "xml")
    except Exception:
        # lxml not installed; fall back to html.parser
        soup = BeautifulSoup(xml_text, "html.parser")

    # Standard sitemap: <url><loc>...</loc></url>
    for loc in soup.find_all("loc"):
        url = loc.get_text(strip=True)
        if not url:
            continue
        link_text = url.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
        score = _score_link(url, link_text, patterns)
        if score > 0:
            results.append({
                "url": url,
                "source": "sitemap",
                "score": score,
                "title": link_text,
            })

    return results


# ─── Homepage crawler ─────────────────────────────────────────────────────────


def _crawl_homepage(homepage_url, patterns, session, visited):
    """
    Fetch homepage, extract all same-domain anchor links, score them, and
    return discovered candidates.
    """
    candidates = []

    try:
        import os
        is_scale = os.environ.get("SCALE_CRAWL") == "1"
        timeout = 5 if is_scale else 15
        r = session.get(homepage_url, headers=DEFAULT_HEADERS, timeout=timeout)
        r.raise_for_status()
        if not _is_html(r):
            return candidates
    except Exception as exc:
        print(f"  [discovery] {homepage_url} - fetch error: {exc}", file=sys.stderr)
        return candidates

    soup = BeautifulSoup(r.text, "html.parser")
    page_title = _extract_title(soup)

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        absolute_url = urljoin(homepage_url, href)
        # Remove trailing slash for dedup
        absolute_url = absolute_url.rstrip("/")

        if absolute_url in visited:
            continue
        visited.add(absolute_url)

        if not _same_domain(absolute_url, homepage_url):
            continue
        if _skip_url(absolute_url):
            continue

        link_text = a_tag.get_text(strip=True)
        score = _score_link(absolute_url, link_text, patterns)

        if score > 0:
            candidates.append({
                "url": absolute_url,
                "source": f"homepage ({page_title})",
                "score": score,
                "title": link_text or absolute_url.rsplit("/", 1)[-1],
            })

    return candidates


# ─── Main discovery function ──────────────────────────────────────────────────


def discover_org(key, session, visited=None):
    """
    Discover job-related URLs for a single org key.

    Steps:
      1. Fetch /sitemap.xml (adds candidates from sitemap entries)
      2. Crawl each configured homepage (depth 1 — direct links only)

    Returns a deduplicated list of candidate dicts sorted by score descending.
    Each candidate: {url, source, score, title}
    """
    if key not in DISCOVERY_CONFIG:
        return []

    cfg = DISCOVERY_CONFIG[key]
    homepages = cfg.get("homepages", [])
    patterns = cfg.get("patterns", [])
    candidates = []
    seen_urls = set()

    if visited is None:
        visited = set()

    # Step 1: check sitemap
    for hp in homepages:
        sitemap_url = urljoin(hp, "/sitemap.xml")
        try:
            import os
            is_scale = os.environ.get("SCALE_CRAWL") == "1"
            timeout = 5 if is_scale else 10
            r = session.get(sitemap_url, headers=DEFAULT_HEADERS, timeout=timeout)
            if r.status_code == 200 and "xml" in (r.headers.get("Content-Type", "") or "").lower():
                sitemap_candidates = _parse_sitemap(r.text, patterns)
                for c in sitemap_candidates:
                    u = c["url"].rstrip("/")
                    if u not in seen_urls:
                        seen_urls.add(u)
                        visited.add(u)
                        candidates.append(c)
        except Exception:
            pass  # no sitemap — fine

        # Polite pause after sitemap check
        time.sleep(1)

    # Step 2: crawl each homepage
    for hp in homepages:
        hp_candidates = _crawl_homepage(hp, patterns, session, visited)
        for c in hp_candidates:
            u = c["url"].rstrip("/")
            if u not in seen_urls:
                seen_urls.add(u)
                candidates.append(c)

        # Polite pause between pages
        time.sleep(2)

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)

    return candidates


def discover_all(session, orgs=None):
    """
    Run discovery across all (or specified) orgs in DISCOVERY_CONFIG.

    Returns dict: org_key -> list of discovered candidates.
    """
    if orgs is None:
        orgs = list(DISCOVERY_CONFIG.keys())

    results = {}
    visited = set()

    for idx, key in enumerate(orgs):
        org_name = DISCOVERY_CONFIG[key].get("name", key)
        print(f"\nDiscovering URLs for {org_name} ({key})...")

        if idx > 0:
            time.sleep(3)  # polite delay between orgs

        try:
            candidates = discover_org(key, session, visited)
            results[key] = candidates
            if candidates:
                print(f"  Found {len(candidates)} candidate URLs:")
                for c in candidates[:8]:
                    print(f"    [{c['score']:>3}] {c['title'][:60]:<60} => {c['url'][:80]}")
                if len(candidates) > 8:
                    print(f"    ... and {len(candidates) - 8} more")
            else:
                print(f"  No new job-related URLs discovered.")
        except Exception as exc:
            print(f"  Discovery error: {exc}", file=sys.stderr)
            results[key] = []

    return results
