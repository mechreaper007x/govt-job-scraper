"""
scraper/spa_scraper.py

Playwright-based SPA scraper for government job portals that require
JavaScript rendering (e.g., rrbapply.gov.in, rrbapply.gov.in).

Uses Playwright's async API with headless Chromium to:
  1. Navigate to the target URL
  2. Wait for JavaScript to render dynamic content
  3. Extract HTML after rendering for standard parsers

Extension point for future SPAs like DRDO portals, BEL TCS iON drives, etc.
"""

import asyncio
import sys
import re
import atexit
import threading
from datetime import datetime


# ─── Playwright lazy imports ─────────────────────────────────────────────────
# Playwright is an optional dependency — only imported when SPA scraping is used.
# This avoids forcing all users to install Playwright + Chromium.

_thread_local = threading.local()
_all_instances = []
_instances_lock = threading.Lock()
_playwright_semaphore = threading.Semaphore(2)
_atexit_registered = False

# Compiled regex for blocking unnecessary resources (images, fonts)
_BLOCKED_RESOURCES = re.compile(r"\.(png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$")

# Compiled regex for RRB card/container detection
_RRB_CARD_RE = re.compile(r'card|cen|notification|recruit|job|listing', re.I)

# Stealth configuration is instantiated on the fly to remain thread-safe


def _ensure_playwright():
    """Lazy-import and initialize Playwright per-thread if not already done.

    Thread-safe storage ensures each concurrent thread gets its own Playwright
    and browser instances, avoiding greenlet cross-thread switching errors.
    """
    global _atexit_registered

    # Check if this thread already has a browser and it is still connected
    browser = getattr(_thread_local, "browser", None)
    if browser is not None:
        try:
            if browser.is_connected:
                return browser
        except Exception:
            pass

    # Initialize Playwright and Browser for the current thread
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        _thread_local.playwright = pw
        _thread_local.browser = browser

        with _instances_lock:
            _all_instances.append((pw, browser))
            if not _atexit_registered:
                atexit.register(close_playwright)
                _atexit_registered = True

        return browser
    except ImportError:
        raise ImportError(
            "Playwright is required for SPA scraping. Install with:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )


def close_playwright():
    """Shut down all Playwright and browser instances across all threads.

    Call at program exit.
    """
    global _all_instances
    with _instances_lock:
        for pw, browser in _all_instances:
            try:
                browser.close()
            except Exception:
                pass
            try:
                pw.stop()
            except Exception:
                pass
        _all_instances.clear()


# ─── SPA Page Fetcher ────────────────────────────────────────────────────────


def fetch_spa_page(url, wait_selector=None, timeout_ms=30000, scroll=True):
    """
    Fetch a page using Playwright, wait for JS rendering, return HTML.

    Args:
        url: Target URL to fetch.
        wait_selector: CSS selector to wait for before extracting HTML.
                       If None, waits for 'networkidle' state.
        timeout_ms: Max wait time in milliseconds (default 30s).
        scroll: If True, scroll to bottom to trigger lazy-loaded content.

    Returns:
        str: Rendered HTML content, or empty string on failure.
    """
    with _playwright_semaphore:
        browser = _ensure_playwright()

        try:
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                java_script_enabled=True,
                ignore_https_errors=True,
            )

            page = context.new_page()

            # Apply stealth patches to hide automation fingerprints
            try:
                from playwright_stealth import Stealth
                stealth = Stealth()
                stealth.apply_stealth_sync(page)
            except Exception:
                pass  # stealth is optional — degrade gracefully if not installed

            # Block unnecessary resources to speed up loading
            page.route(_BLOCKED_RESOURCES, lambda route: route.abort())

            # Navigate to the page
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for dynamic content
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                except Exception:
                    # Selector not found — try networkidle as fallback
                    try:
                        page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    except Exception:
                        pass  # Continue with whatever loaded
            else:
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except Exception:
                    pass  # Continue with whatever loaded

            # Scroll to trigger lazy-loaded content
            if scroll:
                _scroll_page(page)

            # Extract rendered HTML
            html = page.content()
            context.close()
            return html

        except Exception as exc:
            print(f"  [SPA] Error fetching {url}: {exc}", file=sys.stderr)
            try:
                context.close()
            except Exception:
                pass
            return ""


def _scroll_page(page):
    """Scroll to bottom of page to trigger lazy-loaded content."""
    try:
        page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    const distance = 300;
                    const timer = setInterval(() => {
                        const scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if (totalHeight >= scrollHeight) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                    // Safety timeout
                    setTimeout(() => { clearInterval(timer); resolve(); }, 5000);
                });
            }
        """)
        # Wait a bit for any triggered lazy loads
        page.wait_for_timeout(1000)
    except Exception:
        pass  # Scroll failure is non-fatal


# ─── RRB-Specific Parser ─────────────────────────────────────────────────────


def parse_rrb_spa(html_content):
    """
    Parse RRB (Indian Railways) SPA content after Playwright rendering.

    rrbapply.gov.in is a React SPA with hash-based routing.
    After rendering, it shows CEN (Centralized Employment Notification) cards
    with job titles, post names, and application dates.

    Falls back to link-based extraction if card structure isn't found.
    """
    from bs4 import BeautifulSoup
    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')

    # Strategy 1: Look for CEN cards/sections (React-rendered content)
    # RRB typically shows cards with CEN number, post name, dates
    for card in soup.find_all(['div', 'section', 'article'], class_=_RRB_CARD_RE):
        title = ""
        link = ""
        date_str = ""

        # Extract title from headings or strong text
        heading = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            title = heading.get_text(strip=True)
        if not title:
            strong = card.find('strong') or card.find('b')
            if strong:
                title = strong.get_text(strip=True)
        if not title:
            # Use first substantial text block
            for p in card.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 10:
                    title = text
                    break

        if not title or len(title) < 5:
            continue

        # Extract link
        a_tag = card.find('a')
        if a_tag and a_tag.get('href'):
            href = a_tag['href']
            if href.startswith('http'):
                link = href
            elif href.startswith('/'):
                link = f"https://rrbapply.gov.in{href}"
            elif href.startswith('#'):
                link = f"https://rrbapply.gov.in/{href}"
            else:
                link = f"https://rrbapply.gov.in/{href}"

        # Extract dates
        date_match = re.search(
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            card.get_text()
        )
        if date_match:
            date_str = date_match.group(1)

        if title:
            postings.append({
                "title": f"[RRB-SPA] {title}",
                "link": link or "https://rrbapply.gov.in/",
                "date": date_str,
            })

    # Strategy 2: If no cards found, scan all links for CEN/recruitment patterns
    if not postings:
        seen = set()
        for a in soup.find_all('a'):
            href = a.get('href', '').strip()
            if not href or href.startswith('javascript:') or href == '#':
                continue

            title = a.get_text(separator=' ', strip=True)
            title = re.sub(r'\s+', ' ', title).strip()
            if len(title) < 5:
                continue

            if href.startswith('http'):
                link = href
            elif href.startswith('/'):
                link = f"https://rrbapply.gov.in{href}"
            else:
                link = f"https://rrbapply.gov.in/{href}"

            if link in seen:
                continue
            seen.add(link)

            title_lower = title.lower()
            link_lower = link.lower()
            if any(kw in title_lower or kw in link_lower
                   for kw in ['cen', 'recruit', 'vacanc', 'notification',
                              'apply', 'group', 'alp', 'technician', 'rrb']):
                postings.append({
                    "title": f"[RRB-SPA] {title}",
                    "link": link,
                    "date": "",
                })

    # Strategy 3: Extract any visible text that mentions CEN numbers
    if not postings:
        text = soup.get_text()
        cen_matches = re.findall(
            r'(CEN\s*\d+/\d{4}[^.\n]{0,200})',
            text, re.IGNORECASE
        )
        for match in cen_matches[:20]:  # Limit to 20
            clean = re.sub(r'\s+', ' ', match).strip()
            if len(clean) > 10:
                postings.append({
                    "title": f"[RRB-SPA] {clean}",
                    "link": "https://rrbapply.gov.in/",
                    "date": "",
                })

    return postings


# ─── DRDO-Specific Parser ────────────────────────────────────────────────────


def parse_drdo_spa(html_content):
    """
    Parse DRDO vacancies page after Playwright rendering.

    URL: https://www.drdo.gov.in/drdo/en/offerings/vacancies
    After Playwright rendering, the page shows vacancy cards with:
      - Headings (h2-h6) for vacancy titles
      - 'View More' links to detail pages
      - Published dates and advertisement numbers

    The static parser (parse_drdo) works on the server-rendered HTML.
    This SPA parser captures content from the JavaScript-rendered layout
    which may include additional vacancies not in the static version.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    BASE = "https://www.drdo.gov.in"
    seen = set()

    # Strategy 1: Find 'View More' links and extract surrounding context
    for a in soup.find_all('a'):
        text = a.get_text(strip=True).lower()
        href = a.get('href', '')

        is_view_more = ('view more' in text) or ('/vacancies/' in href)
        if not is_view_more:
            continue

        # Climb up to find the container with vacancy metadata
        parent = a.parent
        container = None
        for _ in range(6):
            if parent is None:
                break
            parent_text = parent.get_text()
            if ('Advertisement No' in parent_text or
                    'Published Date' in parent_text or
                    'Last Date' in parent_text):
                container = parent
                break
            parent = parent.parent

        if container is None:
            # Fallback: use the nearest heading as title
            container = a.parent

        # Extract title from heading
        title = ""
        heading = container.find(['h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            title = heading.get_text(strip=True)
        if not title:
            # Try first link text that isn't 'View More'
            for link_tag in container.find_all('a'):
                lt = link_tag.get_text(strip=True)
                if lt and lt.lower() != 'view more' and len(lt) > 5:
                    title = lt
                    break
        if not title:
            # Use first text block
            text_blocks = [t.strip() for t in container.get_text().splitlines() if t.strip()]
            if text_blocks:
                title = text_blocks[0]

        if not title or len(title) < 5:
            continue

        # Extract link
        link = urljoin(BASE, href) if href else f"{BASE}/drdo/en/offerings/vacancies"
        if link in seen:
            continue
        seen.add(link)

        # Extract dates
        container_text = container.get_text()
        pub_date = ""
        date_match = re.search(
            r'Published Date\s*(\d{2}/\d{2}/\d{4})',
            container_text, re.IGNORECASE
        )
        if date_match:
            pub_date = date_match.group(1)
        else:
            # Try any date pattern
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', container_text)
            if date_match:
                pub_date = date_match.group(1)

        postings.append({
            "title": f"[DRDO-SPA] {title}",
            "link": link,
            "date": pub_date,
        })

    # Strategy 2: Scan all links for vacancy/recruitment patterns
    if not postings:
        for a in soup.find_all('a'):
            href = a.get('href', '').strip()
            if not href or href.startswith('javascript:') or href == '#':
                continue

            title = a.get_text(separator=' ', strip=True)
            title = re.sub(r'\s+', ' ', title).strip()
            if len(title) < 5:
                continue

            link = urljoin(BASE + "/", href) if not href.startswith('http') else href
            if link in seen:
                continue
            seen.add(link)

            title_lower = title.lower()
            link_lower = link.lower()
            if any(kw in title_lower or kw in link_lower
                   for kw in ['vacanc', 'recruit', 'notification', 'apply',
                              'advertisement', 'engagement']):
                postings.append({
                    "title": f"[DRDO-SPA] {title}",
                    "link": link,
                    "date": "",
                })

    return postings


# ─── IIT Hyderabad (IITH) Parser ──────────────────────────────────────────────


def parse_iith_spa(_html_content="", _base_url=""):
    """
    Parse IIT Hyderabad career page via their JSON API.

    IITH uses a React SPA (careers.iith.ac.in) that fetches job data from:
      https://careers.iith.ac.in/api/v1/jobs/search/?sort=created

    This parser hits the API directly (no Playwright needed) and returns
    structured job listings.
    """
    import requests as _req

    postings = []
    api_url = "https://careers.iith.ac.in/api/v1/jobs/search/?sort=created"

    try:
        r = _req.get(api_url, timeout=15, verify=False)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return postings

    results = data.get("results", [])
    for job in results:
        title = job.get("title", "")
        job_id = job.get("id", "")
        job_type = job.get("job_type", "")
        start_date = job.get("start_date", "")
        end_date = job.get("end_date", "")
        departments = job.get("departments", [])
        # departments is a list of dicts: [{"id": 21, "name": "Physics", "code": "PHY_D"}]
        if isinstance(departments, list) and departments:
            dept = departments[0]
            dept_name = dept.get("name", "") if isinstance(dept, dict) else str(dept)
        else:
            dept_name = ""
        slug = job.get("slug", "")

        if not title:
            continue

        # Build link to the job detail page
        if slug:
            link = f"https://careers.iith.ac.in/jobs/{slug}"
        elif job_id:
            link = f"https://careers.iith.ac.in/jobs/{job_id}"
        else:
            link = "https://careers.iith.ac.in/jobs"

        # Format date
        date_str = end_date or start_date or ""
        if date_str:
            date_str = date_str[:10]  # YYYY-MM-DD

        # Build descriptive title
        full_title = title
        if dept_name and dept_name not in title:
            full_title = f"{title} ({dept_name})"
        if job_type:
            full_title = f"{full_title} [{job_type}]"

        postings.append({
            "title": f"[IITH] {full_title}",
            "link": link,
            "date": date_str,
        })

    return postings


# ─── IIT Bombay (IITB) Parser ───────────────────────────────────────────────


def parse_iitb_spa(html_content, base_url=""):
    """
    Parse IIT Bombay R&D jobs page.

    URL: https://rnd.iitb.ac.in/jobs
    Structure: HTML table with rows containing job titles and PDF links.
    Each row has a link to a PDF advertisement or results document.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    seen = set()

    BASE = "https://rnd.iitb.ac.in"

    # Strategy 1: Parse the table rows
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            # Find the first cell with a link
            for cell in cells:
                a_tag = cell.find('a')
                if not a_tag or not a_tag.get('href'):
                    continue
                title = a_tag.get_text(strip=True)
                href = a_tag['href']
                if len(title) < 5:
                    continue

                link = urljoin(BASE + "/", href) if not href.startswith('http') else href
                if link in seen:
                    continue
                seen.add(link)

                postings.append({
                    "title": f"[IITB] {title}",
                    "link": link,
                    "date": "",
                })

    # Strategy 2: Scan all links for job/recruitment patterns
    if not postings:
        for a in soup.find_all('a'):
            href = a.get('href', '').strip()
            if not href or href.startswith('javascript:') or href == '#':
                continue
            title = a.get_text(strip=True)
            if len(title) < 5:
                continue
            link = urljoin(BASE + "/", href) if not href.startswith('http') else href
            if link in seen:
                continue
            seen.add(link)
            title_lower = title.lower()
            link_lower = link.lower()
            if any(kw in title_lower or kw in link_lower
                   for kw in ['job', 'recruit', 'vacanc', 'advertisement', 'project', 'apply']):
                postings.append({
                    "title": f"[IITB] {title}",
                    "link": link,
                    "date": "",
                })

    return postings


# ─── IIT Madras (IITM) Parser ───────────────────────────────────────────────


def parse_iitm_spa(html_content, base_url=""):
    """
    Parse IIT Madras recruitment page.

    URL: https://recruit.iitm.ac.in/
    Structure: Pages with numbered recruitments (R525, R524, etc.) containing
    links to detailed advertisements, syllabi, shortlists, and results.

    Extracts recruitment notices with their R-number codes and associated
    documents (advertisements, results, etc.).
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    seen = set()
    BASE = "https://recruit.iitm.ac.in"

    # Strategy 1: Find recruitment entries by R-number pattern
    # IITM uses codes like R525, R524, etc. for each recruitment
    r_numbers = {}

    for a in soup.find_all('a'):
        href = a.get('href', '').strip()
        text = a.get_text(strip=True)
        if not href or len(text) < 3:
            continue

        # Check if this link's text or href contains an R-number
        r_match = re.search(r'(R\d{3,4})', text + ' ' + href, re.IGNORECASE)
        if r_match:
            r_code = r_match.group(1).upper()
            if r_code not in r_numbers:
                r_numbers[r_code] = []
            r_numbers[r_code].append((text, href))

    # Build postings from R-number groups
    for r_code, links in sorted(r_numbers.items(), reverse=True):
        # Find the main advertisement link
        advt_link = ""
        advt_title = ""
        for text, href in links:
            text_lower = text.lower()
            if any(kw in text_lower for kw in ['advertisement', 'detailed advt', 'general instruction']):
                advt_title = text
                advt_link = href
                break

        if not advt_link and links:
            advt_title = links[0][0]
            advt_link = links[0][1]

        if advt_link:
            link = urljoin(BASE + "/", advt_link) if not advt_link.startswith('http') else advt_link
            if link not in seen:
                seen.add(link)
                postings.append({
                    "title": f"[IITM] {r_code}: {advt_title}",
                    "link": link,
                    "date": "",
                })

    # Strategy 2: If no R-numbers found, scan for recruitment-related links
    if not postings:
        for a in soup.find_all('a'):
            href = a.get('href', '').strip()
            text = a.get_text(strip=True)
            if not href or len(text) < 5:
                continue
            link = urljoin(BASE + "/", href) if not href.startswith('http') else href
            if link in seen:
                continue
            seen.add(link)
            text_lower = text.lower()
            if any(kw in text_lower for kw in ['recruit', 'advertisement', 'vacanc', 'apply', 'position']):
                postings.append({
                    "title": f"[IITM] {text}",
                    "link": link,
                    "date": "",
                })

    return postings


# ─── Generic SPA Parser ──────────────────────────────────────────────────────


def parse_generic_spa(html_content, base_url="", keywords=None):
    """
    Generic SPA parser that extracts job-related links after JS rendering.

    Used as a fallback when no org-specific parser is available.
    Scans for links matching the provided keywords.

    Args:
        html_content: Rendered HTML from Playwright.
        base_url: Base URL for resolving relative links.
        keywords: List of keywords to match in link text/href.
                  Defaults to common recruitment terms.
    """
    from bs4 import BeautifulSoup
    if keywords is None:
        keywords = ['recruit', 'vacanc', 'career', 'job', 'notification', 'apply']

    postings = []
    soup = BeautifulSoup(html_content, 'html.parser')
    seen = set()

    for a in soup.find_all('a'):
        href = a.get('href', '').strip()
        if not href or href.startswith('javascript:') or href == '#':
            continue

        title = a.get_text(separator=' ', strip=True)
        title = re.sub(r'\s+', ' ', title).strip()
        if len(title) < 5:
            continue

        if href.startswith('http'):
            link = href
        elif href.startswith('/') and base_url:
            from urllib.parse import urljoin
            link = urljoin(base_url, href)
        else:
            link = href

        if link in seen:
            continue
        seen.add(link)

        title_lower = title.lower()
        link_lower = link.lower()
        if any(kw in title_lower or kw in link_lower for kw in keywords):
            postings.append({
                "title": title,
                "link": link,
                "date": "",
            })

    return postings


# Markers that a page is a client-rendered JS app whose real content only
# appears after the browser executes JavaScript. When the static HTML parse
# finds nothing but these markers are present, a headless render is worth the
# (expensive) attempt.
_JS_APP_MARKERS = (
    'id="root"', "id='root'", 'id="app"', "id='app'",
    'ng-app', 'ng-version', 'data-reactroot', '__next_data__',
    'window.__nuxt__', 'vue.js', 'react-dom', 'ng-controller',
)


def looks_like_js_app(html):
    """
    Heuristic: does this static HTML look like an empty shell for a JS app?

    True when the page is small on visible text yet carries framework markers
    (React/Angular/Vue/Next) or a large script-to-content ratio. Used to decide
    whether a zero-result org is worth re-fetching through Playwright.
    """
    if not html:
        return False
    low = html.lower()

    if any(m in low for m in _JS_APP_MARKERS):
        return True

    # Script-heavy, text-light pages are almost always client-rendered.
    script_bytes = sum(len(s) for s in re.findall(r"<script[\s\S]*?</script>", low))
    text_only = re.sub(r"<[^>]+>", " ", low)
    text_only = re.sub(r"\s+", " ", text_only).strip()
    if len(text_only) < 600 and script_bytes > 2000:
        return True

    return False


def render_and_parse_adaptive(url, timeout_ms=25000):
    """
    Render *url* with headless Chromium, then run the standard adaptive parser
    over the resulting DOM. Returns a list of postings (possibly empty).

    This is the generic Playwright fallback used by the crawler for any org
    whose static HTML yielded nothing but looks like a JS app. It reuses the
    same scoring/date logic as the static path, so results are consistent.
    """
    from scraper.adaptive_parser import parse_adaptive

    try:
        html = fetch_spa_page(url, timeout_ms=timeout_ms)
    except Exception:
        return []

    if not html or len(html) < 500:
        return []

    try:
        return parse_adaptive(html, base_url=url)
    except Exception:
        return []
