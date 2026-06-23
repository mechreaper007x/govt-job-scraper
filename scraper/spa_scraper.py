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
