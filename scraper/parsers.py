# parsers.py
# Target page structure parsers for job portal change detection
# Last reviewed and tested on: 2026-06-21

import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def parse_cdac(html_content):
    """
    Parses CDAC current openings page.
    URL: https://www.cdac.in/index.aspx?id=current_jobs
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    # CDAC headings of interest
    target_headers = ["Current Openings", "Rolling Advertisements", "Notifications"]
    
    headers = soup.find_all('h3')
    for h in headers:
        text = h.get_text(strip=True)
        # Match case-insensitively or via substrings
        matched_section = None
        for sec in target_headers:
            if sec.lower() in text.lower():
                matched_section = sec
                break
                
        if matched_section:
            # Iterate through sibling elements until the next h3 heading
            curr = h.find_next_sibling()
            while curr and curr.name != 'h3':
                if curr.name == 'p':
                    a_tags = curr.find_all('a')
                    for a_tag in a_tags:
                        title = a_tag.get_text(strip=True)
                        href = a_tag.get('href', '')
                        if title and href:
                            link = urljoin("https://www.cdac.in/", href)
                            # Exclude generic pagination or print page links
                            if "print_page" in link or "custom" in link:
                                continue
                            postings.append({
                                "title": f"[{matched_section}] {title}",
                                "link": link,
                                "date": ""
                            })
                curr = curr.find_next_sibling()
    return postings

def parse_bel(html_content):
    """
    Parses BEL job notifications page.
    URL: https://bel-india.in/job-notifications/
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    boxes = soup.find_all(class_='career-result-box')
    for box in boxes:
        h2 = box.find('h2')
        if not h2:
            continue
        title = h2.get_text(strip=True)
        
        # Last Date
        date_div = box.find(class_='jon-lastdate')
        date_str = ""
        if date_div:
            date_str = date_div.get_text(strip=True).replace("Last Date to Apply:", "").strip()
            
        # Extract first ad link as direct link, or fallback to careers page
        link = "https://bel-india.in/job-notifications/"
        ad_div = box.find(class_='advertisements')
        if ad_div:
            a_tag = ad_div.find('a')
            if a_tag and a_tag.get('href'):
                link = urljoin("https://bel-india.in/", a_tag.get('href'))
                
        postings.append({
            "title": title,
            "link": link,
            "date": date_str
        })
    return postings

def parse_drdo(html_content):
    """
    Parses DRDO vacancies page.
    URL: https://www.drdo.gov.in/drdo/en/offerings/vacancies
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Locate all 'View More' links to target vacancy blocks
    view_mores = []
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text(strip=True).lower()
        if 'view more' in text or '/vacancies/' in href:
            view_mores.append(a)

    for a in view_mores:
        parent = a.parent
        found_container = None
        # Climb up to 5 levels to locate the card container containing advertisement metadata
        for _ in range(5):
            if parent:
                parent_text = parent.get_text()
                if "Advertisement No" in parent_text or "Published Date" in parent_text:
                    found_container = parent
                    break
                parent = parent.parent
                
        if found_container:
            title = ""
            heading = found_container.find(['h2', 'h3', 'h4', 'h5', 'h6'])
            if heading:
                title = heading.get_text(strip=True)
            else:
                for link_tag in found_container.find_all('a'):
                    if link_tag != a and link_tag.get_text(strip=True):
                        title = link_tag.get_text(strip=True)
                        break
            if not title:
                text_blocks = [t.strip() for t in found_container.get_text().splitlines() if t.strip()]
                if text_blocks:
                    title = text_blocks[0]
                    
            # Parse published date
            pub_date = ""
            container_text = found_container.get_text()
            date_match = re.search(r'Published Date\s*(\d{2}/\d{2}/\d{4})', container_text, re.IGNORECASE)
            if date_match:
                pub_date = date_match.group(1)
                
            link = urljoin("https://www.drdo.gov.in/", a.get('href', ''))
            
            postings.append({
                "title": title,
                "link": link,
                "date": pub_date
            })
            
    # De-duplicate entries mapped to same View More link
    seen_links = set()
    deduped_postings = []
    for post in postings:
        if post["link"] not in seen_links:
            seen_links.add(post["link"])
            deduped_postings.append(post)
            
    return deduped_postings

def parse_isro(html_content):
    """
    Parses ISRO view all opportunities page.
    URL: https://www.isro.gov.in/ViewAllOpportunities.html
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 5:
                loc = tds[0].get_text(strip=True)
                post = tds[1].get_text(strip=True)
                adv = tds[2].get_text(strip=True)
                open_date = tds[3].get_text(strip=True)
                close_date = tds[4].get_text(strip=True)
                
                # Check button click location for absolute link
                link = "https://www.isro.gov.in/ViewAllOpportunities.html"
                if len(tds) >= 6:
                    button = tds[5].find('button')
                    if button and button.get('onclick'):
                        onclick = button.get('onclick')
                        match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                        if match:
                            link = urljoin("https://www.isro.gov.in/", match.group(1))
                
                title = f"{post} at {loc} (Advt: {adv})"
                postings.append({
                    "title": title,
                    "link": link,
                    "date": open_date
                })
    return postings

def parse_barc(content):
    """
    Parses BARC RSS feed (xml) or HTML table (fallback).
    URL: https://www.barc.gov.in/rss_barc.xml or careers/recruitment.html
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
            # Only track Vacancy / Recruitment / Result items
            if 'vacancies' in category or 'results' in category or 'recruitment' in category:
                title = entry.title
                # Clean up any inline HTML markup inside title (e.g. <br /> or <a> tags)
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
        # Fallback html table parser
        postings = []
        soup = BeautifulSoup(content_str, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 4:
                    adv = tds[0].get_text(strip=True)
                    title_text = tds[1].get_text(strip=True)
                    last_date = tds[2].get_text(strip=True)
                    
                    link = "https://www.barc.gov.in/careers/recruitment.html"
                    a_tag = tds[3].find('a')
                    if a_tag and a_tag.get('href'):
                        link = urljoin("https://www.barc.gov.in/careers/", a_tag.get('href'))
                        
                    title = f"{title_text} (Advt: {adv})"
                    postings.append({
                        "title": title,
                        "link": link,
                        "date": last_date
                    })
        return postings

def parse_bsnl(html_content):
    """
    Parses BSNL external exam portal.
    URL: https://externalexam.bsnl.co.in/
    """
    postings = []
    # If the standard inactive text is present, return empty
    if "Currently BSNL is not conducting any External Recruitment" in html_content:
        return postings
        
    soup = BeautifulSoup(html_content, 'html.parser')
    for a in soup.find_all('a'):
        title = a.get_text(strip=True)
        href = a.get('href')
        if title and href:
            if href.startswith('mailto:') or href.startswith('javascript:') or href == '#':
                continue
            link = urljoin("https://externalexam.bsnl.co.in/", href)
            postings.append({
                "title": title,
                "link": link,
                "date": ""
            })
    return postings

def parse_uppsc(html_content):
    """
    Parses UPPSC home page marquee listings.
    URL: https://uppsc.up.nic.in/
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    # Marquee container containing recent announcements
    container = soup.find(id='ctl00_MainContent_Div_Whats_New') or soup.find(id='marquee2')
    if not container:
        container = soup.find('marquee')
        
    if container:
        lis = container.find_all('li')
        for li in lis:
            a_tag = li.find('a')
            if a_tag:
                title = a_tag.get('title', '').strip()
                if not title:
                    title = a_tag.get_text(strip=True)
                # Clean up title whitespace
                title = re.sub(r'\s+', ' ', title).strip()
                
                href = a_tag.get('href', '').strip()
                link = urljoin("https://uppsc.up.nic.in/", href)
                
                date_str = ""
                span = li.find('span')
                if span:
                    date_str = span.get_text(strip=True)
                    
                postings.append({
                    "title": title,
                    "link": link,
                    "date": date_str
                })
    return postings

def parse_certin(html_content):
    """
    Parses CERT-In recruitment page.
    URL: https://www.cert-in.org.in/s2cMainServlet?pageid=VLNLISTRE
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    container = soup.find(id="print_content")
    if not container:
        container = soup
        
    for a in container.find_all('a'):
        href = a.get('href', '').strip()
        if not href or href.startswith('javascript:') or href == '#':
            continue
            
        title = a.get_text(separator=' ', strip=True)
        if not title:
            title = " ".join(a.stripped_strings)
            
        title = re.sub(r'\s+', ' ', title).strip()
        if not title:
            continue
            
        link = urljoin("https://www.cert-in.org.in/", href)
        
        postings.append({
            "title": title,
            "link": link,
            "date": ""
        })
        
    # De-duplicate entries
    seen_links = set()
    deduped_postings = []
    for post in postings:
        if post["link"] not in seen_links:
            seen_links.add(post["link"])
            deduped_postings.append(post)
            
    return deduped_postings

def parse_employment_news(html_content):
    """
    Parses Employment News (MIB) page.
    URL: https://employmentnews.gov.in/NewEmp/AllJobs.aspx?k=All
    """
    soup = BeautifulSoup(html_content, "html.parser")
    listings = []

    table = soup.find("table")
    if not table:
        return listings

    rows = table.find_all("tr")[1:]  # skip header row
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

def parse_cdot(html_content):
    """
    Parses C-DOT current openings page.
    URL: https://www.cdot.in/cdotweb/web/current_openings.php?lang=en
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='openings') or soup.find('table')
    if table:
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all(['td', 'th'])
            if len(tds) >= 5:
                header_text = tds[0].get_text(strip=True).lower()
                if 's_no' in header_text or 's.no' in header_text:
                    continue
                    
                post = tds[1].get_text(strip=True)
                opening_date = tds[2].get_text(strip=True)
                closing_date = tds[3].get_text(strip=True)
                
                link = "https://www.cdot.in/cdotweb/web/current_openings.php?lang=en"
                ad_cell = tds[4]
                a_tag = ad_cell.find('a')
                if a_tag and a_tag.get('href'):
                    link = urljoin("https://www.cdot.in/cdotweb/web/", a_tag.get('href'))
                
                if post:
                    postings.append({
                        "title": post,
                        "link": link,
                        "date": closing_date
                    })
    return postings


def fetch_nielit_center(session, center_id, headers):
    """
    Internal helper – fetches recruitment listings for a single NIELIT center.
    Returns a list of posting dicts.
    
    Endpoint discovered by capturing XHR traffic from the React SPA at:
    https://www.nielit.gov.in/form?formName=Recruitments&center=HQ
    
    The key `table_ID` value is the string "NIELITMainRecruitments" (NOT a numeric ID).
    Each result record has: contentId, blogName, title (HTML), eventDate, eventExpiryDate.
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
    # result is [[...records...], {metadata_dict}]
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

        # Strip HTML tags from title to get clean text
        # Also extract any direct link from the title HTML for per-item URLs
        perma_link = ""
        if title_html:
            title_soup = BeautifulSoup(title_html, 'html.parser')
            # Try to extract a direct link from the title HTML first
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
            # Fall back to blogName (url-slugged form), humanise it
            title = blog_name.replace('-', ' ').strip()
        else:
            continue

        if not title:
            continue

        # Canonical link: the React SPA URL for this center's recruitment page
        # Prefer the direct link extracted from title HTML when available
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
    Fetches NIELIT (National Institute of Electronics & IT) recruitment listings
    across all major center IDs via the internal JSON API.

    URL (SPA entry point): https://www.nielit.gov.in/form?formName=Recruitments&center=HQ
    API Endpoint: POST https://www.nielit.gov.in/api/getOptions

    Unlike other parsers this does NOT take html_content — it drives its own
    HTTP session to hit the JSON backend directly. The `session` arg is optional;
    if None, a new requests.Session is created (without SSL patch). In main.py
    the project's shared RobustAdapter session should be passed in.
    """
    import ssl as _ssl
    from urllib3.poolmanager import PoolManager
    from requests.adapters import HTTPAdapter

    if session is None:
        # Fallback: create a bare session (no SSL patch)
        session = requests.Session()

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.nielit.gov.in",
        "Referer": "https://www.nielit.gov.in/form?formName=Recruitments&center=HQ",
    }

    # Monitor the main HQ + major regional centers.
    # Full center list from /api/getOptions table_ID=913 has ~44 entries; we track HQ
    # and key IT-heavy centres to keep run time reasonable.
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


def parse_ecil(html_content):
    """
    Parses ECIL (Electronics Corporation of India Ltd) job openings page.
    URL: https://www.ecil.co.in/jobopenings
    Structure: Single HTML table with headers:
      S.No | Advt No | Short Description | Documents | Links
    Documents column contains PDF links (Advertisement, Application Form, Annexure).
    
    Note: Uses the 'Short Description' column (index 2) for the title, not
    the 'S.No' column (index 0) which contains row numbers like "1", "2".
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')

    # Try table first
    table = soup.find('table')
    if table:
        # Find header row to map column indices
        header_row = table.find('tr')
        col_map = {}
        if header_row:
            headers = header_row.find_all(['th', 'td'])
            for i, h in enumerate(headers):
                text = h.get_text(strip=True).lower()
                col_map[text] = i

        # Determine title column: prefer 'short description', then 'description',
        # then fall back to column 2. Skip S.No (column 0).
        title_idx = col_map.get('short description',
                     col_map.get('description',
                     col_map.get('post',
                     col_map.get('title', 2))))  # fallback to index 2

        for row in table.find_all('tr')[1:]:  # skip header
            tds = row.find_all('td')
            if len(tds) < max(title_idx + 1, 2):
                continue

            title = tds[title_idx].get_text(strip=True) if len(tds) > title_idx else ""
            if not title or title.lower() in ('s.no', 'sr.no', 'sno', 'sl.no', 'description', 'title', 'post', ''):
                continue
            # Skip rows where title is a single digit (S.No column fallback)
            if title.isdigit() and len(title) <= 2:
                continue

            # Find link – could be in any td
            link = "https://www.ecil.co.in/index.php/career-at-ecil"
            for td in tds:
                a = td.find('a')
                if a and a.get('href'):
                    href = a.get('href')
                    if not href.startswith('javascript'):
                        link = urljoin("https://www.ecil.co.in/", href)
                        break
            # Date usually in last or second-last td
            date_str = tds[-1].get_text(strip=True) if len(tds) > 1 else ""
            postings.append({"title": title, "link": link, "date": date_str})
        return postings

    # Fallback: scan all links in main content area
    main = soup.find(class_=re.compile(r'article|content|main|body', re.I)) or soup
    for a in main.find_all('a'):
        href = a.get('href', '')
        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        if href.startswith('javascript:') or href == '#':
            continue
        link = urljoin("https://www.ecil.co.in/", href)
        postings.append({"title": title, "link": link, "date": ""})

    # De-duplicate
    seen = set()
    deduped = []
    for p in postings:
        if p['link'] not in seen:
            seen.add(p['link'])
            deduped.append(p)
    return deduped


def parse_stpi(html_content):
    """
    Parses STPI (Software Technology Parks of India) careers page.
    URL: https://www.stpi.in/careers
    Structure: One or more HTML tables with headers:
      Sr.No. | Job Title | Description | Last Date to Apply | Link | Related Documents
    Each table typically has 2 data rows (one per listing), split across many
    identical tables in the DOM (Drupal pagination artefact).
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')

    seen_titles = set()
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if not rows:
            continue

        # Detect header row to find column positions
        first_cells = [td.get_text(strip=True).lower() for td in rows[0].find_all(['th', 'td'])]
        if 'job title' not in first_cells:
            continue  # Not a job listing table

        try:
            job_title_idx = first_cells.index('job title')
        except ValueError:
            job_title_idx = 1
        try:
            last_date_idx = first_cells.index('last date to apply')
        except ValueError:
            last_date_idx = 3
        try:
            related_docs_idx = first_cells.index('related documents')
        except ValueError:
            related_docs_idx = 5
        try:
            link_idx = first_cells.index('link')
        except ValueError:
            link_idx = 4

        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) <= max(job_title_idx, last_date_idx):
                continue

            title = cells[job_title_idx].get_text(strip=True)
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            date_str = cells[last_date_idx].get_text(strip=True) if len(cells) > last_date_idx else ""

            # Prefer the Related Documents (PDF) link; fall back to Link cell, then any href
            link = "https://www.stpi.in/careers"
            for col_idx in [related_docs_idx, link_idx]:
                if len(cells) > col_idx:
                    a = cells[col_idx].find('a')
                    if a and a.get('href') and not a['href'].startswith('javascript'):
                        link = urljoin("https://www.stpi.in/", a['href'])
                        break
            else:
                for cell in cells:
                    a = cell.find('a')
                    if a and a.get('href') and not a['href'].startswith('javascript'):
                        link = urljoin("https://www.stpi.in/", a['href'])
                        break

            postings.append({"title": title, "link": link, "date": date_str})

    return postings


def parse_nic(html_content):
    """
    Parses NIC (National Informatics Centre) recruitment page.
    URL: https://recruitment.nic.in/index_new.php
    Structure: Old frameset-based PHP page with HTML tables listing
    recruitment notices and PDF links. Targeted for deduplication by link.
    Known postings: Scientist-B/C/D, Scientific/Technical Assistant-A, etc.
    Note: The main nic.in/jobs-in-nic/ redirects to nic.gov.in homepage;
    recruitment.nic.in/ uses a frameset — the actual content is index_new.php.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')

    for a in soup.find_all('a'):
        href = a.get('href', '').strip()
        if not href or href.startswith('mailto:') or href.startswith('javascript:') or href == '#':
            continue

        link = urljoin("https://recruitment.nic.in/", href)

        # Get the parent table-cell text to use as the announcement title
        parent = a.parent
        for _ in range(3):
            if parent and parent.name in ['td', 'li', 'p', 'div']:
                break
            if parent:
                parent = parent.parent

        parent_text = parent.get_text(separator=' ', strip=True) if parent else ""
        link_text = a.get_text(separator=' ', strip=True)
        parent_text = re.sub(r'\s+', ' ', parent_text).strip()
        link_text = re.sub(r'\s+', ' ', link_text).strip()

        # If the link text is a generic phrase, use the richer parent text instead
        generic_phrases = ['click here', 'apply online', 'apply now', 'view details', 'here']
        if len(link_text) > 20 and not any(g in link_text.lower() for g in generic_phrases):
            title = link_text
        else:
            title = parent_text

        # Clean up trailing generic phrases and punctuation
        title = re.sub(r'\s*(click here|apply online|view details|here)\s*', ' ', title, flags=re.I)
        title = re.sub(r'[\s,\.\-\|]+$', '', title).strip()

        if len(title) < 5:
            continue

        postings.append({"title": title, "link": link, "date": ""})

    seen = set()
    deduped = []
    for p in postings:
        if p['link'] not in seen:
            seen.add(p['link'])
            deduped.append(p)
    return deduped


def parse_hal(html_content):
    """
    Parses HAL (Hindustan Aeronautics Limited) current openings.
    The main website (hal-india.co.in) is an Angular SPA — static HTML has no
    job content. The WordPress backend exposes a custom REST API:

    POST https://hal-india.co.in/backend/wp-json/hal/v1/career
    Body: {} (empty JSON)

    The response is a JSON object shaped like:
      {"banner-img": "...", "career": [<item>, ...]}

    Each career item has:
      - id, division_id, division
      - title: the job title
      - floated_date: publication date (DD-MM-YYYY)
      - activeupto: closing/deadline date (DD-MM-YYYY)
    The listing payload does NOT include a per-item URL — the Angular SPA
    routes to detail pages client-side by item id.

    This function receives the raw JSON text from main.py.
    """
    import json
    postings = []

    try:
        raw = json.loads(html_content)
    except (json.JSONDecodeError, TypeError):
        return postings

    # Normalize to a list of items
    items = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        # Try common wrapper keys
        for key in ("data", "results", "posts", "jobs", "careers", "career", "items", "list"):
            if key in raw and isinstance(raw[key], list):
                items = raw[key]
                break
        # If still empty but it looks like a single career item, wrap it
        if not items and "post_title" in raw:
            items = [raw]

    HAL_BASE = "https://hal-india.co.in/"
    HAL_CAREER_PAGE = "https://hal-india.co.in/career"

    for item in items:
        if not isinstance(item, dict):
            continue

        # Extract title
        title = ""
        for title_key in ("title", "post_title", "job_title", "name", "position"):
            val = item.get(title_key, "")
            if isinstance(val, dict):
                val = val.get("rendered", "") or val.get("value", "")
            if val and isinstance(val, str) and len(val) > 3:
                # Strip HTML entities
                from html import unescape
                title = re.sub(r'<[^>]+>', '', unescape(str(val))).strip()
                title = re.sub(r'\s+', ' ', title).strip()
                break

        if not title:
            continue

        # Extract link. The career listing payload does not include a per-item
        # URL — the Angular SPA routes to detail pages by ID client-side.
        # Prefer any explicit link field if present; otherwise construct a
        # deep link using the item's unique id.
        link = HAL_CAREER_PAGE
        # Check for explicit link fields first
        for link_key in ("link", "file_link", "pdf_link", "url", "apply_link", "detail_link"):
            val = item.get(link_key, "")
            if val and isinstance(val, str) and len(val) > 5:
                if val.startswith("http"):
                    link = val
                else:
                    link = urljoin(HAL_BASE, val)
                break
        else:
            # No explicit link found — construct a per-item link using the id
            item_id = item.get("id")
            if item_id:
                link = f"{HAL_CAREER_PAGE}?id={item_id}"

        # Extract date. HAL uses `activeupto` (closing/deadline date) and
        # `floated_date` (publication date); prefer `activeupto` since it's
        # the deadline the applicant cares about.
        date_str = ""
        for date_key in ("activeupto", "last_date", "closing_date", "end_date", "floated_date", "post_date", "date"):
            val = item.get(date_key, "")
            if val and isinstance(val, str) and val.strip():
                date_str = val.strip()[:10]  # keep YYYY-MM-DD or DD-MM-YYYY prefix
                break

        postings.append({"title": title, "link": link, "date": date_str})

    return postings


def parse_cris(html_content):
    """
    Parses CRIS (Centre for Railway Information Systems) career page.
    URL: https://www.cris.org.in/loadpage?page=indexcareer
    Structure: Large HTML page listing hundreds of vacancy notices as anchor
    links to PDFs, grouped by section: Gazetted, Non-Gazetted, Project
    Assistants, Project Officers, Software Professionals.
    Each <a> points to a PDF at /PDF/<category>/<filename>.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE = "https://www.cris.org.in"
    base_url = f"{BASE}/loadpage?page=indexcareer"

    seen = set()
    for a in soup.find_all('a'):
        href = a.get('href', '').strip()
        if not href or href.startswith('javascript:') or href.startswith('mailto:') or href == '#':
            continue
        # Only track PDF vacancy notices (not nav/social/other links)
        if '/PDF/' not in href and 'vacancy' not in href.lower() and 'recruit' not in href.lower():
            continue

        link = urljoin(BASE + "/", href)
        if link in seen:
            continue
        seen.add(link)

        # Build title from anchor text, cleaned up
        title = a.get_text(separator=' ', strip=True)
        title = re.sub(r'\s+', ' ', title).strip()

        # If title is suspiciously short, climb to parent cell for richer context
        if len(title) < 15:
            parent = a.parent
            for _ in range(3):
                if parent and parent.name in ['td', 'li', 'p']:
                    break
                if parent:
                    parent = parent.parent
            if parent:
                parent_text = re.sub(r'\s+', ' ', parent.get_text(separator=' ', strip=True)).strip()
                if len(parent_text) > len(title):
                    title = parent_text

        # Strip trailing noise
        title = re.sub(r'[\s,\.\-]+$', '', title).strip()
        if len(title) < 8:
            continue

        postings.append({"title": title, "link": link, "date": ""})

    return postings


def parse_ncs(session=None):
    """
    Fetches government job listings from the National Career Service (NCS) beta portal.
    API: POST https://betacloud.ncs.gov.in/api/v1/job-posts/search

    Uses employerType=Government filter. The API has no apply links and no dates,
    so this serves as a change-detection source — alerts when new govt jobs appear.
    Link points to the NCS search page since per-item URLs aren't available.
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
    page_size = 100  # max page size for fewer API calls
    max_pages = 5    # limit to 500 jobs per run (avoids rate limiting)
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

            total_elements = inner.get("totalElements", 0)
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
                # jobLocations can be strings or dicts; handle both
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
                if location and org:
                    title_full += f" ({location})"
                elif location:
                    title_full += f" ({location})"

                # No dates available from API
                date_str = ""

                all_postings.append({
                    "title": title_full,
                    "link": NCS_SEARCH_URL,  # generic — no per-item URLs
                    "date": date_str,
                })

            page += 1

            # Stop if we've reached the last page (total_pages may be None)
            if total_pages and page >= total_pages:
                break

        except Exception as exc:
            import sys
            print(f"  [NCS] page {page} fetch error: {exc}", file=sys.stderr)
            break

    return all_postings


def parse_ongc(html_content):
    """
    Parses ONGC recruitment notices page.
    URL: https://ongcindia.com/web/eng/career/recruitment-notice
    Structure: HTML page with grouped links to recruitment notices and PDFs.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE = "https://ongcindia.com"
    seen = set()

    for a in soup.find_all('a'):
        href = a.get('href', '').strip()
        if not href or href.startswith('javascript:') or href.startswith('mailto:') or href == '#':
            continue

        title = a.get_text(separator=' ', strip=True)
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) < 5:
            continue

        link = urljoin(BASE + "/", href)
        if link in seen:
            continue
        seen.add(link)

        # Filter to recruitment-related links only
        link_lower = link.lower()
        title_lower = title.lower()
        # Only track links that point to actual PDFs, notifications, or specific recruitment pages
        # Exclude generic nav links like "Why Work With ONGC", "Recruitment Policy", etc.
        generic_titles = ['why work', 'recruitment policy', 'recruitment notices', 'our vision',
                          'about us', 'contact', 'home', 'site map', 'feedback', 'photo gallery']
        if any(g in title_lower for g in generic_titles):
            continue
        if any(kw in link_lower for kw in ['recruit', 'vacanc', 'notification', 'engagement']):
            # Also require the link to point to a PDF or a specific notification page
            if any(ext in link_lower for ext in ['.pdf', 'notification', 'recruit', 'vacanc', 'engagement']):
                postings.append({"title": title, "link": link, "date": ""})

    return postings


def parse_sail(html_content):
    """
    Parses SAIL careers page.
    URL: https://www.sail.co.in/careers
    Structure: HTML page with links to recruitment notifications.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE = "https://www.sail.co.in"
    seen = set()

    # Try table rows first
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 2:
                title_cell = tds[0]
                a_tag = title_cell.find('a')
                if a_tag and a_tag.get('href'):
                    title = a_tag.get_text(strip=True)
                    href = a_tag['href']
                    if title and len(title) > 5:
                        link = urljoin(BASE + "/", href)
                        date_str = tds[-1].get_text(strip=True) if len(tds) > 1 else ""
                        if link not in seen:
                            seen.add(link)
                            postings.append({"title": title, "link": link, "date": date_str})

    # Fallback: scan all links
    if not postings:
        for a in soup.find_all('a'):
            href = a.get('href', '').strip()
            if not href or href.startswith('javascript:') or href == '#':
                continue
            title = a.get_text(strip=True)
            if len(title) < 8:
                continue
            link = urljoin(BASE + "/", href)
            if link in seen:
                continue
            link_lower = link.lower()
            title_lower = title.lower()
            if any(kw in link_lower or kw in title_lower
                   for kw in ['recruit', 'vacanc', 'notification', 'career', 'engagement']):
                seen.add(link)
                postings.append({"title": title, "link": link, "date": ""})

    return postings


def parse_ntpc(html_content):
    """
    Parses NTPC careers portal.
    URL: https://careers.ntpc.co.in/
    Structure: Dynamic portal — may return HTML with job listings or a login page.
    Fallback: extracts any recruitment links from the page.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE = "https://careers.ntpc.co.in"
    seen = set()

    # If page has job listing cards or table rows
    for card in soup.find_all(['tr', 'div', 'li']):
        a_tag = card.find('a')
        if not a_tag or not a_tag.get('href'):
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag['href']
        if len(title) < 8:
            continue
        if href.startswith('javascript:') or href == '#':
            continue
        link = urljoin(BASE + "/", href)
        if link in seen:
            continue
        seen.add(link)
        date_str = ""
        date_span = card.find('span', class_=re.compile(r'date|time', re.I))
        if date_span:
            date_str = date_span.get_text(strip=True)
        postings.append({"title": title, "link": link, "date": date_str})

    return postings


def parse_aai(html_content):
    """
    Parses AAI (Airports Authority of India) recruitment page.
    URL: https://www.aai.aero/en/careers/recruitment
    Structure: HTML table with columns for Exam Name, Post Date, Links, Results.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE = "https://www.aai.aero"
    seen = set()

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        # Detect header row
        first_row_cells = [td.get_text(strip=True).lower() for td in rows[0].find_all(['th', 'td'])]
        if not any(kw in ' '.join(first_row_cells) for kw in ['exam', 'recruit', 'post', 'vacanc', 'notification']):
            continue

        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # Title is usually the first cell
            title = cells[0].get_text(strip=True)
            if len(title) < 5:
                continue
            if title in seen:
                continue
            seen.add(title)

            # Find link in any cell
            link = BASE + "/en/careers/recruitment"
            for cell in cells:
                a = cell.find('a')
                if a and a.get('href') and not a['href'].startswith('javascript'):
                    link = urljoin(BASE + "/", a['href'])
                    break

            date_str = ""
            if len(cells) >= 2:
                date_str = cells[1].get_text(strip=True)

            postings.append({"title": title, "link": link, "date": date_str})

    # Fallback: scan links
    if not postings:
        for a in soup.find_all('a'):
            href = a.get('href', '').strip()
            if not href or href.startswith('javascript:') or href == '#':
                continue
            title = a.get_text(strip=True)
            if len(title) < 8:
                continue
            link = urljoin(BASE + "/", href)
            if link in seen:
                continue
            link_lower = link.lower()
            if any(kw in link_lower or kw in title.lower()
                   for kw in ['recruit', 'vacanc', 'notification', 'career']):
                seen.add(link)
                postings.append({"title": title, "link": link, "date": ""})

    return postings


def parse_rrb(html_content):
    """
    Parses Indian Railways (RRB) notifications.
    URL: https://www.rrbapply.gov.in/
    Structure: SPA portal — static HTML may have no content.
    Fallback: extracts CEN (Centralised Employment Notice) links from any
    available text on the page. Also checks the static Indian Railways
    board page for recruitment links.
    """
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE_RRB = "https://www.rrbapply.gov.in"
    seen = set()

    for a in soup.find_all('a'):
        href = a.get('href', '').strip()
        if not href or href.startswith('javascript:') or href.startswith('mailto:') or href == '#':
            continue
        title = a.get_text(separator=' ', strip=True)
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) < 5:
            continue

        # Resolve link — could be relative to rrbapply or indianrailways
        if href.startswith('http'):
            link = href
        elif href.startswith('/'):
            # Determine base from context
            link = urljoin(BASE_RRB + "/", href)
        else:
            link = urljoin(BASE_RRB + "/", href)

        if link in seen:
            continue
        seen.add(link)

        title_lower = title.lower()
        link_lower = link.lower()
        if any(kw in title_lower or kw in link_lower
               for kw in ['cen', 'recruit', 'vacanc', 'notification', 'apply', 'railway', 'group']):
            date_str = ""
            # Look for date in nearby text
            parent = a.parent
            if parent:
                parent_text = parent.get_text()
                date_match = re.search(r'(\d{2}[./-]\d{2}[./-]\d{4})', parent_text)
                if date_match:
                    date_str = date_match.group(1)
            postings.append({"title": title, "link": link, "date": date_str})

    return postings


def test_parsers():

    """
    Utility testing routine to pull live websites and check parsing yields.
    """
    import sys
    import ssl
    import io
    from requests.adapters import HTTPAdapter
    from urllib3.poolmanager import PoolManager
    from scraper.config import ORGS_CONFIG, DEFAULT_HEADERS
    from scraper.filters import classify

    # Ensure console can handle Unicode output (Windows cp1252 workaround)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    elif hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
    
    class LegacyAdapter(HTTPAdapter):
        def init_poolmanager(self, connections, maxsize, block=False):
            ctx = ssl.create_default_context()
            ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            self.poolmanager = PoolManager(
                num_pools=connections, maxsize=maxsize, block=block, ssl_context=ctx
            )
            
    session = requests.Session()
    session.mount('https://', LegacyAdapter())
    
    print("Starting Live Parsers Verification Test...")
    errors = 0
    for key, val in ORGS_CONFIG.items():
        print(f"\nTargeting: {val['name']} ({val['url']})...")
        try:
            # Special handling for orgs that don't use simple GET + HTML parse
            if key == "nielit":
                # NIELIT uses a JSON API session, not static HTML
                results = parse_nielit(session=session)
                print(f"  Postings Found: {len(results)}")
            elif key == "hal":
                # HAL endpoint requires POST with browser-like headers
                hal_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Referer": "https://hal-india.co.in/",
                    "Origin": "https://hal-india.co.in",
                }
                r = session.post(val['url'], headers=hal_headers, json={}, timeout=30)
                r.raise_for_status()
                print(f"  Status Code: {r.status_code}")
                results = parse_hal(r.text)
                print(f"  Postings Found: {len(results)}")
            else:
                r = session.get(val['url'], headers=DEFAULT_HEADERS, timeout=15)
                r.raise_for_status()
                
                # Map parser functions dynamically
                parser_fn = getattr(sys.modules[__name__], f"parse_{key}")
                # NIC uses windows-1251 charset; pass bytes to avoid decode errors
                results = parser_fn(r.content if key in ('barc', 'nic') else r.text)
                
                print(f"  Status Code: {r.status_code}")
                print(f"  Postings Found: {len(results)}")
            
            if results:
                # Count by relevance
                relevant_cnt = 0
                uncertain_cnt = 0
                excluded_cnt = 0
                for item in results:
                    rel = classify(item["title"])
                    if rel == "relevant":
                        relevant_cnt += 1
                    elif rel == "uncertain":
                        uncertain_cnt += 1
                    else:
                        excluded_cnt += 1
                print(f"  Relevance Breakdown: relevant={relevant_cnt}, uncertain={uncertain_cnt}, excluded={excluded_cnt}")
                # Windows console encoding handled globally via sys.stdout.reconfigure above
                print(f"  First Posting Sample: {results[0]}")
            else:
                print("  WARNING: Scraped 0 postings. Check selector status.")
        except Exception as e:
            print(f"  ERROR parsing {val['name']}: {e}")
            errors += 1
            
    print("\n-------------------------------------------")
    print(f"Verification Test Complete. Failures encountered: {errors}")
    if errors > 0:
        sys.exit(1)

if __name__ == "__main__":
    test_parsers()
