"""
scraper/filters.py

Classifies a posting title into one of three relevance tiers for a CSE
(Computer Science Engineering) branch:

    "relevant"  -> title clearly mentions CS/IT/Software/Data/AI/Cyber etc.
    "excluded"  -> title clearly mentions a non-CSE-only discipline
                   (civil, mechanical, driver, nursing, etc.) and has
                   no CSE signal alongside it
    "uncertain" -> title gives no discipline signal either way
                   (common for CDAC/BEL "Project Engineer" style titles
                   where the real discipline is only in the linked PDF)

Design intent: never silently drop a posting that *might* be CSE-relevant.
"excluded" should only fire when we're confident, everything else surfaces
in notifications (relevant normally, uncertain with a flag) so a vague
title never costs you a real opportunity.

Accuracy strategy (3-layer approach):
    Layer 1: Title keyword matching (existing, fast, no network)
    Layer 2: Per-org context + URL pattern matching (fast, no network)
    Layer 3: PDF content extraction (slow, network + parsing, optional)
"""

import re
import sys
import os
import io
import hashlib

# ─── Keyword lists (unchanged) ──────────────────────────────────────────────

INCLUDE_KEYWORDS = [
    # core CS/IT terms
    "computer science", "computer engineering", " cse", "cse ",
    "information technology",    "it/", "i.t.",
    "software", "programmer", "programming",
    "full stack", "fullstack", "web develop", "app develop",
    "web designer", "application developer",
    # data / AI
    "data science", "data analytics", "data analyst",
    "artificial intelligence", "machine learning", "ai/ml", " ai ", " ml ",
    "deep learning", "nlp", "computer vision",
    # security / infra
    "cyber security", "cybersecurity", "network security", "information security",
    "devops", "cloud computing", "cloud engineer", "cloud ",
    "database", "dbms", "system administrator", "sysadmin",
    "system analyst", "network engineer",
    "blockchain", "quantum computing", "high performance computing", " hpc",
    # IT infrastructure & architecture
    "data centre", "data center", "enterprise architecture",
    "architect",
    # explicit combined-discipline phrasing seen in ISRO/NIC-style postings
    "and computer science", "computer science engineering",
    # PSU IT project roles (CDAC, DRDO, ISRO style)
    "project engineer", "project manager", "project associate",
    "project scientist", "project staff", "project technician",
    "senior project", "project support",
    "project assistant", "project officer", "project consultant",
    "senior consultant",
    # Scientist grades at NIC, DRDO, ISRO
    "scientist/engineer", "scientist b", "scientist-b",
    "scientist c", "scientist-c", "scientist d", "scientist-d",
    "scientist 'sc'", "scientist 'sd'",
    # Research roles relevant for CSE
    "junior research fellow", "junior research fellowship", " jrf",
    "research associate", "research scientist", "research fellow",
    "scientist ",
    # CDAC-specific roles
    "adjunct scientist", "adjunct engineer",
    # General technical roles
    "technical assistant", "technical consultant",
    "it officer", "information officer", "it resource", "it professional",
    "it support", "it manager", "it associate", "it consultant", "it specialist",
    "it executive", "system engineer", "systems engineer", "technical officer",
    "scientific officer",
    # Telecom / PSU technical roles
    "junior telecom officer", " jto",
    # Scientific assistant roles (BARC, ISRO style)
    "scientific assistant",
]

EXCLUDE_KEYWORDS = [
    # other engineering branches, when standing alone
    "civil engineering", "civil works", "mechanical engineering",
    "electrical engineering", "chemical engineering", "metallurgy",
    "instrumentation engineering", "architecture",
    # non-engineering / support roles & trades
    "driver", "havildar", "fireman", "cook", "catering",
    "nurse", "nursing", "pharmacist", "medical officer", "radiographer",
    "lab technician", "stenographer", "draughtsman", "library assistant",
    "security officer", "office attendant", "peon",
    "multi tasking staff", " mts ",
    "trade apprentice", "iti apprentice", "technician b", "technician-b",
    "technician a", "technician-a", "clerk", "typist", "receptionist",
    # pure science branches common in ISRO/BARC/DRDO postings
    "geology", "geophysics", "agriculture", "physical sciences",
    "life sciences", "ordnance", "ammunition",
    # administrative, legal, hr, and financial roles
    "legal", "law ", "law officer", "finance", "accounts", "audit", "marketing",
    "administrative officer", " admin ", "admin officer", "human resource", " hr ",
    "personal assistant", "private secretary", "administration", "administrative",
    "assistant",  # safe because specific include matches (scientific assistant etc.) are checked first
    # management / executive roles (not CSE-specific)
    "chairman", "controller", "managing director",
    # teaching / academic non-research
    "guest faculty", "teacher", "professor", "principal", "lecturer",
    # language / translation
    "translator", "translation officer", "translation", "hindi", "rajbhasha",
]


# ─── Layer 2: Per-org context rules ─────────────────────────────────────────
#
# These orgs are *primarily* CS/IT organizations.
# When their posting title is "uncertain" (no discipline signal),
# we apply domain-specific heuristics to decide relevance.

# Orgs where most non-excluded postings are CS-relevant by default.
# Reasoning: CDAC = CS org, NIC = IT, CRIS = Railway IT, STPI = Software parks,
# C-DOT = Telematics, CERT-In = Cybersecurity.
CS_FIRST_ORGS = {
    "cdac", "nic", "cris", "stpi", "cdot", "certin",
}

# Per-org title patterns that override the default classification.
# Format: org_key -> list of (pattern, classification) tuples.
# Patterns are checked against padded lowercase title.
# These handle exceptions to the org-wide default rules.
ORG_OVERRIDES = {
    "barc": [
        # BARC medical/dental/physics programs → excluded
        ("diploma in radiological physics", "excluded"),
        ("compassionate appointment", "excluded"),
        ("rmo", "excluded"),
        ("locum ", "excluded"),
        ("work assistant", "excluded"),
        ("dental technician", "excluded"),
        ("hospital administrator", "excluded"),
        ("hospital", "excluded"),
        ("dialysis", "excluded"),
        ("radiological physics", "excluded"),
        ("casualty", "excluded"),
        ("radiologist", "excluded"),
    ],
    "hal": [
        # HAL medical consultants → excluded
        ("endodontist", "excluded"),
        ("radiologist", "excluded"),
        ("orthopedician", "excluded"),
        ("zonal doctors", "excluded"),
        ("doctors", "excluded"),
        ("visiting consultant", "excluded"),
        # HAL ITI apprentices → excluded (industrial training, not IT)
        ("iti ", "excluded"),
        ("trade apprentice", "excluded"),
        ("diploma/ engineering", "excluded"),
    ],
    "isro": [
        # ISRO non-CS roles
        ("registrar", "excluded"),
        ("director", "excluded"),  # senior admin, not CS
        ("deputy director", "excluded"),
        ("librarian", "excluded"),
    ],
    "ncs": [
        # NCS non-CS roles
        ("office executive", "excluded"),
        ("office assistant", "excluded"),
        ("supervisor", "excluded"),
        ("founding member", "excluded"),
        ("banking", "excluded"),
        ("bank ", "excluded"),
    ],
    "employment_news": [
        # Employment News non-CS roles
        ("office assistant", "excluded"),
        ("disaster management", "excluded"),
        ("consultant & office", "excluded"),
        ("ndma", "excluded"),
        ("power training", "excluded"),
        ("community based", "excluded"),
        ("mitigation", "excluded"),
        ("flood", "excluded"),
        ("biological", "excluded"),
        ("public health", "excluded"),
    ],
    "ecil": [
        # ECIL entries that are clearly non-CS
        ("trade apprentice", "excluded"),
    ],
    "drdo": [
        # DRDO non-CS roles
        ("internship", "excluded"),
        ("apprentice", "excluded"),
    ],
}


# ─── Layer 2: URL-aware classification ──────────────────────────────────────
#
# Check the link URL path for discipline signals.
# Useful for CRIS (PDFs in /SoftwareProfessional/ vs /Civil/), etc.

# URL path patterns that strongly suggest CS/IT
CS_URL_KEYWORDS = [
    "software", "cse", "computer", "it/", "cyber", "network",
    "data", "cloud", "devops", "developer", "programming",
    "scientist", "technical",
]

# URL path patterns that strongly suggest non-CS
NON_CS_URL_KEYWORDS = [
    "civil", "mechanical", "electrical", "chemical",
    "medical", "dentist", "nursing", "dental",
    "trade", "helper", "labour",
]


# ─── Layer 3: PDF content extraction ────────────────────────────────────────
#
# When layers 1+2 result in "uncertain", optionally download and scan
# the linked PDF for discipline keywords.  Controlled by env var
# SCRAPER_PDF_SCAN=1 (off by default to avoid slowing down runs).

PDF_CS_KEYWORDS = [
    "computer science", "computer engineering", "cse", "information technology",
    "software", "data science", "machine learning", "artificial intelligence",
    "cyber security", "network", "database", "cloud", "devops",
    "programmer", "programming", "python", "java", "react", "angular",
    "project engineer", "scientific assistant", "scientist",
    "data analytics", "data analyst", "web develop", "full stack",
]

PDF_NON_CS_KEYWORDS = [
    "civil engineering", "mechanical engineering", "electrical engineering",
    "chemical engineering", "metallurgy", "geology", "geophysics",
    "agriculture", "life sciences", "physical sciences",
    "medical", "nursing", "pharmacy", "radiological",
    "ordnance", "ammunition", "driver", "cook", "fireman",
    "stenographer", "draughtsman", "librarian",
]

# PDF scan cache to avoid re-downloading same PDFs
_PDF_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".pdf_cache")
_PDF_CACHE_MAX = 200  # max cached PDFs


def _get_pdf_cache_path(url):
    """Return a filesystem path for a cached PDF."""
    os.makedirs(_PDF_CACHE_DIR, exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    return os.path.join(_PDF_CACHE_DIR, f"{url_hash}.txt")


def _extract_pdf_text(url, session, max_chars=5000):
    """
    Download a PDF and extract its text content.
    Returns extracted text or empty string on failure.
    Caches results to avoid re-downloading.
    """
    cache_path = _get_pdf_cache_path(url)

    # Check cache first
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars)
        except Exception:
            pass

    try:
        import pypdf
        r = session.get(url, timeout=20, stream=True)
        r.raise_for_status()

        # Only download if PDF
        ct = r.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
            return ""

        # Read PDF bytes
        pdf_bytes = r.content[:5 * 1024 * 1024]  # limit to 5MB

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for i, page in enumerate(reader.pages):
            if i >= 3:  # only first 3 pages
                break
            text += page.extract_text() or ""

        text = text[:max_chars]

        # Cache result
        try:
            if os.path.exists(_PDF_CACHE_DIR):
                files = os.listdir(_PDF_CACHE_DIR)
                if len(files) > _PDF_CACHE_MAX:
                    # Remove oldest files
                    files.sort(key=lambda f: os.path.getmtime(os.path.join(_PDF_CACHE_DIR, f)))
                    for old_file in files[:len(files) - _PDF_CACHE_MAX]:
                        os.remove(os.path.join(_PDF_CACHE_DIR, old_file))
            with open(cache_path, "w", encoding="utf-8", errors="ignore") as f:
                f.write(text)
        except Exception:
            pass

        return text

    except Exception:
        return ""


def _classify_by_pdf(url, session):
    """
    Download and scan a linked PDF for discipline keywords.
    Returns 'relevant', 'excluded', or None (if inconclusive).
    """
    if not url or not session:
        return None

    # Only scan PDFs
    if not (url.lower().endswith(".pdf") or "pdf" in url.lower()):
        return None

    text = _extract_pdf_text(url, session)
    if not text or len(text) < 50:
        return None

    text_lower = text.lower()

    cs_score = sum(1 for kw in PDF_CS_KEYWORDS if kw in text_lower)
    non_cs_score = sum(1 for kw in PDF_NON_CS_KEYWORDS if kw in text_lower)

    if cs_score >= 2 and cs_score > non_cs_score:
        return "relevant"
    elif non_cs_score >= 2 and non_cs_score > cs_score:
        return "excluded"

    return None


# ─── Main classify function ─────────────────────────────────────────────────

def classify(title, link="", org_key="", session=None):
    """
    Classify a posting title as 'relevant', 'excluded', or 'uncertain'
    using a 3-layer approach:

    Layer 1: Title keyword matching (fast, no network)
    Layer 2: Per-org context + URL patterns (fast, no network)
    Layer 3: PDF content extraction (optional, network + parsing)

    Parameters:
        title: posting title string
        link: URL of the posting (optional, for URL-aware and PDF classification)
        org_key: org key string (optional, for per-org context rules)
        session: requests.Session (optional, for PDF content extraction)
    """
    t = f" {title.lower()} "  # pad so word-boundary-ish substrings match cleanly

    # ── Filter out past years (e.g. 2025 and older) to remove expired historical archives ──
    # Current year is 2026.
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", t)]
    if link:
        years += [int(y) for y in re.findall(r"\b(20\d{2})\b", link.lower())]
    if years and max(years) < 2026:
        if max(years) <= 2025:
            return "excluded"

    # ── Layer 1: Title keyword matching ────────────────────────────────────
    has_include = any(kw in t for kw in INCLUDE_KEYWORDS)
    has_exclude = any(kw in t for kw in EXCLUDE_KEYWORDS)

    if has_include:
        return "relevant"
    if has_exclude:
        return "excluded"

    # ── Layer 2a: Per-org context rules ────────────────────────────────────
    if org_key:
        # Check per-org override rules first
        overrides = ORG_OVERRIDES.get(org_key, [])
        for pattern, classification in overrides:
            if pattern in t:
                return classification

        # For CS-first orgs, non-excluded uncertain titles → relevant
        if org_key in CS_FIRST_ORGS:
            return "relevant"

    # ── Layer 2b: URL-aware classification ─────────────────────────────────
    if link:
        url_lower = link.lower()
        cs_url_hits = sum(1 for kw in CS_URL_KEYWORDS if kw in url_lower)
        non_cs_url_hits = sum(1 for kw in NON_CS_URL_KEYWORDS if kw in url_lower)

        if cs_url_hits >= 2:
            return "relevant"
        if non_cs_url_hits >= 2:
            return "excluded"

    # ── Layer 3: PDF content extraction (optional) ─────────────────────────
    if session and link and os.environ.get("SCRAPER_PDF_SCAN") == "1":
        pdf_result = _classify_by_pdf(link, session)
        if pdf_result:
            return pdf_result

    return "uncertain"


def annotate(listings, org_key="", session=None):
    """
    Attach a 'relevance' key to each listing dict (expects each listing
    to already have a 'title' key from the parser). Returns the same
    list, mutated in place, for convenience.

    Parameters:
        listings: list of posting dicts with at least 'title' key
        org_key: org key string (optional, for per-org context rules)
        session: requests.Session (optional, for PDF content extraction)
    """
    for item in listings:
        # Filter out postings that explicitly have old dates (e.g. year <= 2025)
        date_str = item.get("date", "")
        is_old = False
        if date_str:
            years = [int(y) for y in re.findall(r"\b(20\d{2})\b", date_str)]
            if years and max(years) <= 2025:
                is_old = True

        if is_old:
            item["relevance"] = "excluded"
        else:
            item["relevance"] = classify(
                item.get("title", ""),
                link=item.get("link", ""),
                org_key=org_key,
                session=session,
            )
    return listings
