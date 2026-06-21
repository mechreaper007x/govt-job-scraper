"""
scraper/adaptive_parser.py

Adaptive, layout-invariant parser for extracting job advertisements and
recruitment notifications from arbitrary HTML pages without hardcoded selectors.

Uses heuristic-based contextual link scoring, repeating DOM block detection,
and proximity date extraction.
"""

import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Positive and negative keywords for scoring link relevance
_RELEVANCE_KEYWORDS = [
    r"recruit", r"vacanc", r"career", r"job", r"opening", r"advertisement", r"advt",
    r"notification", r"scientist", r"programmer", r"developer", r"engineer",
    r"project.?associate", r"consultant", r"officer", r"technical.?assistant",
    r"intern", r"fellow", r"jrf", r"srf", r"bharti", r"naukri"
]

_EXCLUSION_KEYWORDS = [
    r"tender", r"grievance", r"rti", r"contact", r"about", r"privacy", r"disclaimer",
    r"facebook", r"twitter", r"linkedin", r"print", r"feedback", r"sitemap", r"home",
    r"gallery", r"tenders", r"faq", r"help", r"login", r"register", r"sign.?in", r"sign.?up"
]

# Regex to match dates in DD/MM/YYYY, YYYY-MM-DD or DD-Month-YYYY formats
_DATE_RE = re.compile(
    r"(\b\d{1,2}[-./]\d{1,2}[-./]\d{2,4}\b)|"
    r"(\b\d{4}[-./]\d{1,2}[-./]\d{1,2}\b)|"
    r"(\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b)",
    re.IGNORECASE
)

class AdaptiveParser:
    """
    Unified parser that extracts job listings from any HTML page using:
      1. Keyword link scoring (URL path + link text)
      2. Surrounding DOM date extraction
      3. Repeating block verification (dedup and clustering)
    """

    def __init__(self, base_url=""):
        self.base_url = base_url

    def parse(self, html_content):
        """
        Parse HTML and yield a list of postings:
          {"title": str, "link": str, "date": str}
        """
        postings = []
        if not html_content or len(html_content) < 100:
            return postings

        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove noisy tags to clean up surrounding text
        for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "nav"]):
            tag.decompose()

        seen_links = set()

        # Iterate through all anchor tags on the page
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("#"):
                continue

            link = urljoin(self.base_url, href)
            # Remove trailing slash and fragments for clean dedup
            clean_link = link.split("#")[0].rstrip("/")
            if clean_link in seen_links:
                continue

            # 1. Clean and normalize link text
            title = a.get_text(separator=" ", strip=True)
            if not title:
                title = " ".join(a.stripped_strings)
            title = re.sub(r"\s+", " ", title).strip()

            # If anchor text is very short/empty, check its image alt text or nearby heading
            if len(title) < 4:
                img = a.find("img", alt=True)
                if img:
                    title = img["alt"].strip()
                else:
                    # Climb up to 2 levels to find sibling or parent text
                    parent = a.parent
                    if parent:
                        title = parent.get_text(separator=" ", strip=True)
                        title = re.sub(r"\s+", " ", title).strip()

            title = re.sub(r"\s*(click here|download|apply online|apply now|here|pdf|link)\s*", " ", title, flags=re.I)
            title = re.sub(r"[\s,\.\-\|\[\]\(\)]+$", "", title).strip()

            title_lower = title.lower()
            if any(w in title_lower for w in ["skip to", "screen reader", "accessibility", "font size", "zoom in", "zoom out", "skip navigation"]):
                continue

            if len(title) < 5:
                continue

            # Check parents for archive containers
            parent_el = a
            is_archived = False
            for _ in range(4):
                if not parent_el:
                    break
                p_attrs = getattr(parent_el, "attrs", {})
                p_class = " ".join(p_attrs.get("class", [])) if isinstance(p_attrs.get("class"), list) else str(p_attrs.get("class", ""))
                p_class = p_class.lower()
                p_id = str(p_attrs.get("id", "")).lower()
                if any(w in p_class or w in p_id for w in ["archive", "expired", "old", "closed", "past"]):
                    is_archived = True
                    break
                parent_el = parent_el.parent

            # 2. Score the link for job relevance
            score = self._score_element(clean_link, title)
            if is_archived:
                score -= 50

            if score < 35:
                continue

            seen_links.add(clean_link)

            # 3. Extract dates in surrounding DOM context
            date_str = self._extract_nearby_date(a)

            postings.append({
                "title": title,
                "link": link,
                "date": date_str
            })

        return postings

    def _score_element(self, url, text):
        """Score a link based on url path and link text."""
        score = 0
        url_lower = url.lower()
        text_lower = text.lower()

        # Positive keywords match
        for kw in _RELEVANCE_KEYWORDS:
            if re.search(kw, url_lower):
                score += 35
                break

        for kw in _RELEVANCE_KEYWORDS:
            if re.search(kw, text_lower):
                score += 45
                break

        # Check for document patterns (PDF is highly indicative of gov job listings)
        if url_lower.endswith(".pdf") or ".pdf?" in url_lower:
            score += 20
        if any(w in url_lower for w in ["/career", "/recruit", "/job", "/vacancy", "/openings"]):
            score += 15

        # Penalties for noise
        for kw in _EXCLUSION_KEYWORDS:
            if re.search(kw, url_lower) or re.search(kw, text_lower):
                score -= 40
                break

        return score

    def _extract_nearby_date(self, a_tag):
        """
        Climb up the DOM tree and scan neighboring text nodes or sibling elements
        to find any date formats (e.g. publication or last date).
        """
        # Look first inside the anchor tag text itself
        text = a_tag.get_text()
        match = _DATE_RE.search(text)
        if match:
            return match.group(0)

        # Climb up to 3 parent levels to search nearby siblings and text
        curr = a_tag
        for _ in range(3):
            parent = curr.parent
            if not parent:
                break
            
            parent_text = parent.get_text(separator=" ", strip=True)
            match = _DATE_RE.search(parent_text)
            if match:
                return match.group(0)
            
            curr = parent

        return ""

def parse_adaptive(html_content, base_url=""):
    """Convenience wrapper for functional parser interface."""
    parser = AdaptiveParser(base_url=base_url)
    return parser.parse(html_content)
