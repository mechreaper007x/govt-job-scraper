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

Tune these lists as you see real output — they're a starting point, not
a finished classifier.
"""

INCLUDE_KEYWORDS = [
    # core CS/IT terms
    "computer science", "computer engineering", " cse", "cse ",
    "information technology", " it ", "i.t.",
    "software", "programmer", "programming",
    "full stack", "fullstack", "web develop", "app develop",
    # data / AI
    "data science", "data analytics", "data analyst",
    "artificial intelligence", "machine learning", "ai/ml", " ai ", " ml ",
    "deep learning", "nlp", "computer vision",
    # security / infra
    "cyber security", "cybersecurity", "network security", "information security",
    "devops", "cloud computing", "cloud engineer",
    "database", "dbms", "system administrator", "sysadmin",
    "blockchain", "quantum computing", "high performance computing", " hpc",
    # explicit combined-discipline phrasing seen in ISRO/NIC-style postings
    "and computer science", "computer science engineering",
]

EXCLUDE_KEYWORDS = [
    # other engineering branches, when standing alone
    "civil engineering", "civil works", "mechanical engineering",
    "electrical engineering", "chemical engineering", "metallurgy",
    "instrumentation engineering", "architecture",
    # non-engineering / support roles
    "driver", "havildar", "fireman", "cook", "catering",
    "nurse", "nursing", "pharmacist", "medical officer", "radiographer",
    "lab technician", "stenographer", "draughtsman", "library assistant",
    "security officer", "office attendant", "peon",
    "multi tasking staff", " mts ",
    # pure science branches common in ISRO/BARC/DRDO postings
    "geology", "geophysics", "agriculture", "physical sciences",
    "life sciences", "ordnance", "ammunition",
    # administrative, legal, hr, and financial roles
    "legal", "law ", "law officer", "finance", "accounts", "audit", "marketing",
    "administrative officer", " admin ", "admin officer", "human resource", " hr ",
]


def classify(title: str) -> str:
    """Return 'relevant', 'excluded', or 'uncertain' for a posting title."""
    t = f" {title.lower()} "  # pad so word-boundary-ish substrings match cleanly

    has_include = any(kw in t for kw in INCLUDE_KEYWORDS)
    has_exclude = any(kw in t for kw in EXCLUDE_KEYWORDS)

    if has_include:
        # CSE signal present — relevant even if another discipline is
        # also mentioned (e.g. combined "Electronics, Mechanical and
        # Computer Science" postings are real CSE opportunities too)
        return "relevant"
    if has_exclude:
        return "excluded"
    return "uncertain"


def annotate(listings: list[dict]) -> list[dict]:
    """
    Attach a 'relevance' key to each listing dict (expects each listing
    to already have a 'title' key from the parser). Returns the same
    list, mutated in place, for convenience.
    """
    for item in listings:
        item["relevance"] = classify(item.get("title", ""))
    return listings
