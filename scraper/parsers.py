# parsers.py
# Unified adaptive scraper routing & special API/SPA parsers
# Last reviewed and tested on: 2026-06-22

import re
import json
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from scraper.config import ORGS_CONFIG
from scraper.adaptive_parser import parse_adaptive

def _parse_via_adaptive(key, html_content):
    """Route standard HTML content through the unified layout-invariant AdaptiveParser."""
    url = ORGS_CONFIG.get(key, {}).get("url", "")
    return parse_adaptive(html_content, base_url=url)

# ─── Special API-based and Custom Document Parsers ───────────────────────────

def fetch_nielit_center(session, center_id, headers):
    """
    Internal helper – fetches recruitment listings for a single NIELIT center.
    Returns a list of posting dicts.
    """
    BASE = "https://www.nielit.gov.in"
    api_url = f"{BASE}/api/getOptions"
    payload = {
        "getOptionsJson": {
            "comp_no": "",
            "FormName": "Recruitments",
            "table_ID": "NIELITMainRecruitments",
            "formupdateid": "1101",
            "language": "en",
            "center": center_id
        }
    }
    try:
        r = session.post(api_url, headers=headers, json=payload, timeout=20, verify=False)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        import sys
        print(f"  [NIELIT] center={center_id} fetch error: {exc}", file=sys.stderr)
        return []

    records = data.get("result", [])
    if not isinstance(records, list) or not records:
        return []
    if isinstance(records[0], list):
        records = records[0]
    elif isinstance(records[0], dict) and "contentId" not in records[0]:
        return []

    postings = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        content_id = rec.get("contentId", "")
        blog_name = rec.get("blogName", "")
        title_html = rec.get("title", "")
        event_date = rec.get("eventDate", "")
        expiry_date = rec.get("eventExpiryDate", "")

        perma_link = ""
        if title_html:
            title_soup = BeautifulSoup(title_html, 'html.parser')
            a_in_title = title_soup.find('a')
            if a_in_title and a_in_title.get('href'):
                href_val = a_in_title['href']
                if href_val.startswith('http'):
                    perma_link = href_val
                else:
                    perma_link = urljoin(BASE, href_val)
            title = title_soup.get_text(separator=' ', strip=True)
            title = re.sub(r'\s+', ' ', title).strip()
        elif blog_name:
            title = blog_name.replace('-', ' ').strip()
        else:
            continue

        if not title:
            continue

        if perma_link:
            link = perma_link
        elif center_id == "HQ":
            link = f"{BASE}/form?formName=Recruitments&center=HQ"
        else:
            link = f"{BASE}/Recruitments/{center_id}"

        postings.append({
            "title": f"[NIELIT-{center_id}] {title}",
            "link": link,
            "date": expiry_date or event_date,
        })
    return postings

def parse_nielit(session=None):
    """
    Fetches NIELIT recruitment listings across major center IDs via internal JSON API.
    """
    if session is None:
        session = requests.Session()

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.nielit.gov.in",
        "Referer": "https://www.nielit.gov.in/form?formName=Recruitments&center=HQ",
    }

    CENTERS = ["HQ", "DEL", "CLT", "GHY", "KOL", "MAS", "BBS", "HYD"]
    all_postings = []
    seen_titles = set()
    for center_id in CENTERS:
        center_posts = fetch_nielit_center(session, center_id, HEADERS)
        for post in center_posts:
            key = (post["title"], post["link"])
            if key not in seen_titles:
                seen_titles.add(key)
                all_postings.append(post)

    return all_postings

def parse_ncs(session=None):
    """
    Fetches government job listings from the National Career Service (NCS) beta portal API.
    """
    if session is None:
        session = requests.Session()

    BASE = "https://betacloud.ncs.gov.in"
    API_URL = f"{BASE}/api/v1/job-posts/search"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": BASE,
        "Referer": f"{BASE}/",
    }

    all_postings = []
    seen_ids = set()
    page = 0
    page_size = 100
    max_pages = 5
    NCS_SEARCH_URL = "https://betacloud.ncs.gov.in/job-listing?employerType=Government"

    while page < max_pages:
        payload = {
            "employerType": "Government",
            "page": page,
            "size": page_size,
        }
        try:
            r = session.post(API_URL, json=payload, headers=HEADERS, timeout=20)
            r.raise_for_status()
            data = r.json()
            inner = data.get("data", {})
            items = inner.get("content", [])

            if not items:
                break

            total_pages = inner.get("totalPages", 0)

            for item in items:
                if not isinstance(item, dict):
                    continue

                job_id = item.get("id", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = item.get("jobTitle", "")
                if not title:
                    continue

                org = item.get("organizationName", "") or item.get("companyName", "") or ""
                location = ""
                locs = item.get("jobLocations", [])
                if locs and isinstance(locs, list):
                    loc_strs = []
                    for loc in locs[:3]:
                        if isinstance(loc, dict):
                            loc_str = loc.get("city", "") or loc.get("name", "") or ""
                        else:
                            loc_str = str(loc)
                        if loc_str:
                            loc_strs.append(loc_str)
                    location = ", ".join(loc_strs)

                title_full = title
                if org:
                    title_full = f"{org} — {title}"
                if location:
                    title_full += f" ({location})"

                all_postings.append({
                    "title": title_full,
                    "link": NCS_SEARCH_URL,
                    "date": "",
                })

            page += 1
            if total_pages and page >= total_pages:
                break
        except Exception as exc:
            import sys
            print(f"  [NCS] page {page} fetch error: {exc}", file=sys.stderr)
            break

    return all_postings

def parse_hal(html_content):
    """
    Parses HAL (Hindustan Aeronautics Limited) current openings REST API JSON response.
    """
    postings = []
    try:
        raw = json.loads(html_content)
    except (json.JSONDecodeError, TypeError):
        return postings

    items = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        for key in ("data", "results", "posts", "jobs", "careers", "career", "items", "list"):
            if key in raw and isinstance(raw[key], list):
                items = raw[key]
                break
        if not items and "post_title" in raw:
            items = [raw]

    HAL_BASE = "https://hal-india.co.in/"
    HAL_CAREER_PAGE = "https://hal-india.co.in/career"

    for item in items:
        if not isinstance(item, dict):
            continue

        title = ""
        for title_key in ("title", "post_title", "job_title", "name", "position"):
            val = item.get(title_key, "")
            if isinstance(val, dict):
                val = val.get("rendered", "") or val.get("value", "")
            if val and isinstance(val, str) and len(val) > 3:
                from html import unescape
                title = re.sub(r'<[^>]+>', '', unescape(str(val))).strip()
                title = re.sub(r'\s+', ' ', title).strip()
                break

        if not title:
            continue

        link = HAL_CAREER_PAGE
        for link_key in ("link", "file_link", "pdf_link", "url", "apply_link", "detail_link"):
            val = item.get(link_key, "")
            if val and isinstance(val, str) and len(val) > 5:
                if val.startswith("http"):
                    link = val
                else:
                    link = urljoin(HAL_BASE, val)
                break
        else:
            item_id = item.get("id")
            if item_id:
                link = f"{HAL_CAREER_PAGE}?id={item_id}"

        date_str = ""
        for date_key in ("activeupto", "last_date", "closing_date", "end_date", "floated_date", "post_date", "date"):
            val = item.get(date_key, "")
            if val and isinstance(val, str) and val.strip():
                date_str = val.strip()[:10]
                break

        postings.append({"title": title, "link": link, "date": date_str})

    return postings

def parse_barc(content):
    """
    Parses BARC RSS feed (xml) or HTML table (fallback).
    """
    is_xml = False
    if isinstance(content, bytes):
        is_xml = b"<?xml" in content or b"<rss" in content
        content_str = content.decode('utf-8', errors='ignore')
    else:
        is_xml = "<?xml" in content or "<rss" in content
        content_str = content

    if is_xml:
        import feedparser
        feed = feedparser.parse(content_str)
        postings = []
        for entry in feed.entries:
            category = getattr(entry, 'category', '').lower()
            if 'vacancies' in category or 'results' in category or 'recruitment' in category:
                title = entry.title
                title = BeautifulSoup(title, 'html.parser').get_text(strip=True)
                if title.startswith("Recruitment :"):
                    title = title.replace("Recruitment :", "").strip()
                elif title.startswith("Results:"):
                    title = title.replace("Results:", "").strip()
                link = entry.link
                pub_date = getattr(entry, 'published', '')
                postings.append({
                    "title": title,
                    "link": link,
                    "date": pub_date
                })
        return postings
    else:
        # Fallback to adaptive parsing for the HTML variant
        return parse_adaptive(content_str, base_url="https://www.barc.gov.in/careers/recruitment.html")

def parse_employment_news(html_content):
    """
    Parses Employment News (MIB) page custom job grid.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    listings = []

    table = soup.find("table")
    if not table:
        return listings

    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        issued_date, org, post, method, last_date = (c.get_text(strip=True) for c in cells[:5])
        if not org or not post:
            continue
        listings.append({
            "title": f"{org} — {post}",
            "link": "https://employmentnews.gov.in/NewEmp/AllJobs.aspx?k=All",
            "method": method,
            "issued_date": issued_date,
            "last_date": last_date,
            "date": last_date,
        })

    return listings

# ─── Standard Parsers Routed to Adaptive Engine ──────────────────────────────

def parse_cdac(html_content): return _parse_via_adaptive("cdac", html_content)
def parse_bel(html_content): return _parse_via_adaptive("bel", html_content)
def parse_drdo(html_content): return _parse_via_adaptive("drdo", html_content)
def parse_isro(html_content): return _parse_via_adaptive("isro", html_content)
def parse_bsnl(html_content): return _parse_via_adaptive("bsnl", html_content)
def parse_certin(html_content): return _parse_via_adaptive("certin", html_content)
def parse_cdot(html_content): return _parse_via_adaptive("cdot", html_content)
def parse_uppsc(html_content): return _parse_via_adaptive("uppsc", html_content)
def parse_ecil(html_content): return _parse_via_adaptive("ecil", html_content)
def parse_stpi(html_content): return _parse_via_adaptive("stpi", html_content)
def parse_nic(html_content): return _parse_via_adaptive("nic", html_content)
def parse_cris(html_content): return _parse_via_adaptive("cris", html_content)
def parse_ongc(html_content): return _parse_via_adaptive("ongc", html_content)
def parse_sail(html_content): return _parse_via_adaptive("sail", html_content)
def parse_ntpc(html_content): return _parse_via_adaptive("ntpc", html_content)
def parse_aai(html_content): return _parse_via_adaptive("aai", html_content)
def parse_rrb(html_content): return _parse_via_adaptive("rrb", html_content)
def parse_sameer(html_content): return _parse_via_adaptive("sameer", html_content)
def parse_ernet(html_content): return _parse_via_adaptive("ernet", html_content)
def parse_uidai(html_content): return _parse_via_adaptive("uidai", html_content)
def parse_pgcil(html_content): return _parse_via_adaptive("pgcil", html_content)
def parse_iocl(html_content): return _parse_via_adaptive("iocl", html_content)
def parse_bhel(html_content): return _parse_via_adaptive("bhel", html_content)
def parse_coal_india(html_content): return _parse_via_adaptive("coal_india", html_content)
def parse_railtel(html_content): return _parse_via_adaptive("railtel", html_content)
def parse_becil(html_content): return _parse_via_adaptive("becil", html_content)
def parse_sebi(html_content): return _parse_via_adaptive("sebi", html_content)
def parse_sidbi(html_content): return _parse_via_adaptive("sidbi", html_content)
def parse_sjvn(html_content): return _parse_via_adaptive("sjvn", html_content)
def parse_tcil(html_content): return _parse_via_adaptive("tcil", html_content)
def parse_dic(html_content): return _parse_via_adaptive("dic", html_content)
def parse_npcil(html_content): return _parse_via_adaptive("npcil", html_content)
def parse_rites(html_content): return _parse_via_adaptive("rites", html_content)
def parse_dfccil(html_content): return _parse_via_adaptive("dfccil", html_content)
def parse_scl(html_content): return _parse_via_adaptive("scl", html_content)
def parse_csir_4pi(html_content): return _parse_via_adaptive("csir_4pi", html_content)
def parse_igcar(html_content): return _parse_via_adaptive("igcar", html_content)
def parse_rrcat(html_content): return _parse_via_adaptive("rrcat", html_content)
def parse_bpcl(html_content): return _parse_via_adaptive("bpcl", html_content)
def parse_pfc(html_content): return _parse_via_adaptive("pfc", html_content)
def parse_rec(html_content): return _parse_via_adaptive("rec", html_content)
def parse_iti(html_content): return _parse_via_adaptive("iti", html_content)
def parse_cel(html_content): return _parse_via_adaptive("cel", html_content)
def parse_nhpc(html_content): return _parse_via_adaptive("nhpc", html_content)
def parse_grid_india(html_content): return _parse_via_adaptive("grid_india", html_content)
def parse_hpcl(html_content): return _parse_via_adaptive("hpcl", html_content)
def parse_rbi(html_content): return _parse_via_adaptive("rbi", html_content)
def parse_negd(html_content): return _parse_via_adaptive("negd", html_content)
def parse_nixi(html_content): return _parse_via_adaptive("nixi", html_content)
def parse_bisag_n(html_content): return _parse_via_adaptive("bisag_n", html_content)
def parse_upsc(html_content): return _parse_via_adaptive("upsc", html_content)
def parse_ssc(html_content): return _parse_via_adaptive("ssc", html_content)
def parse_irctc(html_content): return _parse_via_adaptive("irctc", html_content)
def parse_eil(html_content): return _parse_via_adaptive("eil", html_content)
def parse_mpsc(html_content): return _parse_via_adaptive("mpsc", html_content)
def parse_gpsc(html_content): return _parse_via_adaptive("gpsc", html_content)
def parse_keralapsc(html_content): return _parse_via_adaptive("keralapsc", html_content)
def parse_rpsc(html_content): return _parse_via_adaptive("rpsc", html_content)
def parse_tnpsc(html_content): return _parse_via_adaptive("tnpsc", html_content)
def parse_opsc(html_content): return _parse_via_adaptive("opsc", html_content)
def parse_wbpsc(html_content): return _parse_via_adaptive("wbpsc", html_content)
def parse_appsc(html_content): return _parse_via_adaptive("appsc", html_content)
def parse_mppsc(html_content): return _parse_via_adaptive("mppsc", html_content)
def parse_hpsc(html_content): return _parse_via_adaptive("hpsc", html_content)
def parse_ppsc(html_content): return _parse_via_adaptive("ppsc", html_content)
def parse_ukpsc(html_content): return _parse_via_adaptive("ukpsc", html_content)
def parse_cgpsc(html_content): return _parse_via_adaptive("cgpsc", html_content)
def parse_jpsc(html_content): return _parse_via_adaptive("jpsc", html_content)
def parse_ibps(html_content): return _parse_via_adaptive("ibps", html_content)
def parse_sbi(html_content): return _parse_via_adaptive("sbi", html_content)
def parse_nabard(html_content): return _parse_via_adaptive("nabard", html_content)
def parse_nhb(html_content): return _parse_via_adaptive("nhb", html_content)
def parse_gail(html_content): return _parse_via_adaptive("gail", html_content)
def parse_oil(html_content): return _parse_via_adaptive("oil", html_content)
def parse_nalco(html_content): return _parse_via_adaptive("nalco", html_content)
def parse_mdl(html_content): return _parse_via_adaptive("mdl", html_content)
def parse_dsssb(html_content): return _parse_via_adaptive("dsssb", html_content)
def parse_rsmssb(html_content): return _parse_via_adaptive("rsmssb", html_content)
def parse_hssc(html_content): return _parse_via_adaptive("hssc", html_content)

def test_parsers():
    """Utility testing routine to pull live websites and check parsing yields."""
    import sys
    import io
    from scraper.crawler import GovJobCrawler
    
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    elif hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
    
    print("Starting Live Parsers Verification Test...")
    crawler = GovJobCrawler()
    errors = 0
    success = 0
    
    for key, val in ORGS_CONFIG.items():
        print(f"\nTargeting: {val['name']} ({key})...")
        try:
            postings = crawler._scrape_org(key)
            if postings is None:
                print(f"  ERROR: Scrape returned None.")
                errors += 1
            else:
                success += 1
                print(f"  Postings Found (non-excluded): {len(postings)}")
                if postings:
                    relevant_cnt = sum(1 for p in postings if p.get("relevance") == "relevant")
                    uncertain_cnt = sum(1 for p in postings if p.get("relevance") == "uncertain")
                    print(f"  Relevance Breakdown: relevant={relevant_cnt}, uncertain={uncertain_cnt}")
                    print(f"  First Posting Sample: {postings[0]}")
        except Exception as e:
            print(f"  ERROR parsing {val['name']}: {e}")
            errors += 1
            
    print("\n-------------------------------------------")
    print(f"Verification Test Complete. Success: {success}, Failures: {errors}")
    if errors > 0:
        sys.exit(1)

if __name__ == "__main__":
    test_parsers()
