"""
scraper/learned_vocab.py

Self-learning Career URL Vocabulary Engine.

Mines career_url_cache.json to build a frequency-ranked vocabulary of
career page path segments, grouped by domain family.

No LLM, no external model. Pure frequency-based statistical learning
from the cache of URLs we already know work.

Provides:
  - generate_candidates(url)  -> ranked list of candidate career URLs
  - record_success(url)       -> update vocabulary when a URL yields jobs
  - domain_family(host)       -> classify host into a domain family
"""

import os
import json
import re
import math
from urllib.parse import urlparse, urljoin
from collections import defaultdict, Counter
from threading import Lock

# ── Hard-wired seed vocabulary (minimum baseline even on empty cache) ─────────
_SEED_PATHS = [
    "recruitment", "recruitments", "career", "careers", "jobs",
    "notice", "notices", "notice_category", "advertisement",
    "advertisements", "vacancies", "vacancy", "openings",
    "current-openings", "job-openings", "opportunities",
    "joinus", "join-us", "work-with-us",
    "notification", "notifications",
]

# ── Domain family classification ─────────────────────────────────────────────
_ACADEMIC_KW  = re.compile(r"iit|nit|iiit|iim|iiser|iisc|niser|tiss|tifr|teri|aiims|pgimer|jipmer", re.I)
_BANKING_KW   = re.compile(r"bank|financial|insurance|nbfc|muthoot|lic\.in|sbi|pnb|canara|boi|bob|cbi\.co", re.I)

def domain_family(host: str) -> str:
    host = host.lower()
    if ".nic.in" in host:
        return "nic.in"
    if ".ac.in" in host or ".edu.in" in host or _ACADEMIC_KW.search(host):
        return "academic"
    if ".gov.in" in host:
        return "gov.in"
    if _BANKING_KW.search(host):
        return "banking"
    if ".co.in" in host or ".com" in host or ".org" in host:
        return "psu"
    return "other"

# ── Vocabulary Engine ─────────────────────────────────────────────────────────
class CareerURLVocabulary:
    """
    Learns which URL path segments are most likely to be career pages,
    broken down by domain family. Updates itself when new successes
    are recorded.
    """
    NOISE = frozenset([
        "index.html", "index.php", "index.asp", "index.aspx",
        "default.aspx", "en", "hi", "home", "page", "pages",
        "web", "static", "common", "content", "more",
        "category", "or", "and", "the", "in", "of",
    ])

    def __init__(self, cache_path=None):
        if cache_path is None:
            cache_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "career_url_cache.json"
            )
        self._cache_path = cache_path
        self._lock = Lock()
        # family -> {path_segment: count}
        self._counts = defaultdict(Counter)
        self._total = defaultdict(int)
        self._load()

    def _load(self):
        if not os.path.exists(self._cache_path):
            return
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            return
        for homepage, career_url in cache.items():
            if career_url != homepage:
                self._ingest_url(homepage, career_url)

    def _ingest_url(self, homepage, career_url):
        """Extract path segments and update family counts."""
        try:
            host = urlparse(homepage).netloc
            fam  = domain_family(host)
            path = urlparse(career_url).path
            parts = [seg.lower() for seg in path.split("/")
                     if seg and seg not in self.NOISE]
            with self._lock:
                for part in parts:
                    self._counts[fam][part] += 1
                    self._total[fam] += 1
        except Exception:
            pass

    def record_success(self, homepage_url, career_url):
        """
        Call this whenever a career URL successfully yielded job postings.
        Feeds back into the vocabulary to reinforce effective patterns.
        """
        self._ingest_url(homepage_url, career_url)

    def score_segment(self, segment, family):
        """
        TF-like score for a path segment in a given domain family.
        Higher = more likely to be a career page.
        """
        segment = segment.lower()
        seed_bonus = 2.0 if segment in _SEED_PATHS else 0.0
        count = self._counts[family].get(segment, 0)
        total = max(self._total[family], 1)
        # log-frequency smoothing
        freq_score = math.log1p(count) / math.log1p(total)
        return freq_score + seed_bonus * 0.1

    def top_segments(self, family, n=15):
        """
        Return the top-n path segments for a given domain family,
        sorted by learned frequency.
        """
        family_counts = self._counts.get(family, Counter())
        all_segs = set(family_counts.keys()) | set(_SEED_PATHS)
        scored = {seg: self.score_segment(seg, family) for seg in all_segs}
        return sorted(scored, key=lambda s: scored[s], reverse=True)[:n]

    def generate_candidates(self, base_url, n=20):
        """
        Generate a ranked list of candidate career URLs for a given base URL.
        Returns list of (url, score) tuples, highest score first.
        """
        parsed = urlparse(base_url)
        scheme = parsed.scheme or "https"
        host   = parsed.netloc
        root   = f"{scheme}://{host}"
        fam    = domain_family(host)

        segments = self.top_segments(fam, n=n * 2)
        candidates = []

        for seg in segments:
            score = self.score_segment(seg, fam)
            candidates.append((f"{root}/{seg}", score))
            candidates.append((f"{root}/{seg}/", score * 0.99))

        # nic.in-specific learned pattern: notice_category/recruitment
        if fam == "nic.in":
            candidates.append((f"{root}/notice_category/recruitment", 2.0))
            candidates.append((f"{root}/notice_category/recruitment/", 2.0))

        # WordPress category pattern
        candidates.append((f"{root}/category/recruitment", 1.5))
        candidates.append((f"{root}/category/recruitments", 1.4))

        # Deduplicate by URL, keep highest score
        seen = set()
        result = []
        for url, score in sorted(candidates, key=lambda x: -x[1]):
            if url not in seen:
                seen.add(url)
                result.append((url, score))

        return result[:n]

    def score_link(self, href, link_text, base_host):
        """
        Score a hyperlink (href + visible text) for likelihood of being a
        career/recruitment page. Used by the crawler's self-exploration.
        """
        href_lower = href.lower()
        text_lower = link_text.lower().strip()
        fam = domain_family(base_host)

        score = 0.0

        # Direct text match for career-related terms
        career_terms = [
            "recruitment", "career", "vacancy", "vacancies", "jobs",
            "openings", "opportunities", "advertisement", "notice",
            "apply", "join us", "join", "work with", "hiring",
        ]
        for term in career_terms:
            if term in text_lower:
                score += 3.0
                break

        # href path segment matching against learned vocab
        path_segs = [s.lower() for s in urlparse(href).path.split("/") if s]
        for seg in path_segs:
            seg_score = self.score_segment(seg, fam)
            score += seg_score * 5.0

        # PDF links are a positive signal
        if href_lower.endswith(".pdf"):
            score += 1.0

        # Negative signals
        nav_terms = ["about", "contact", "login", "faq", "gallery",
                     "media", "tenders", "tender", "procurement", "bid",
                     "circulars", "awards", "events", "news", "press"]
        for neg in nav_terms:
            if neg in text_lower or neg in href_lower:
                score -= 2.0

        return max(score, 0.0)


# ── Module-level singleton ────────────────────────────────────────────────────
_vocab = None
_vocab_lock = Lock()

def get_vocab():
    global _vocab
    if _vocab is None:
        with _vocab_lock:
            if _vocab is None:
                _vocab = CareerURLVocabulary()
    return _vocab
