"""
scraper/page_classifier.py

Zero-dependency, offline ML page classifier.
Scores an HTML page (raw text/bytes) for likelihood of containing
job/recruitment listings, using hand-engineered structural features
combined with a lightweight logistic scorer.

Score range: 0.0 (definitely not a jobs page) to 1.0 (definitely a jobs page)
Threshold for "has jobs": >= 0.40
"""

import re
import math

# Date patterns common in Indian govt job pages
_DATE_RE = re.compile(
    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    r'|\b(\d{4}-\d{2}-\d{2})\b'
    r'|\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4})\b',
    re.IGNORECASE
)

_JOB_KW_RE = re.compile(
    r'\b(recruitment|vacancy|vacancies|application|apply|post|posts|'
    r'appointment|engage|opening|career|careers|'
    r'last\s+date|closing\s+date|walk.?in|notification|'
    r'advt|advertisement|eligible|eligibility)\b',
    re.IGNORECASE
)

_TABLE_ROW_RE = re.compile(r'<tr[\s>]', re.IGNORECASE)
_LIST_ITEM_RE = re.compile(r'<li[\s>]', re.IGNORECASE)
_PDF_LINK_RE = re.compile(r'href=["\'][^"\']*\.pdf["\']', re.IGNORECASE)
_LINK_RE = re.compile(r'<a[\s>]', re.IGNORECASE)
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'\s+')

_ANTI_KW_RE = re.compile(
    r'\b(tender|e-tender|etender|bid|auction|quotation|rfp|eoi|procurement|'
    r'press\s+release|annual\s+report|budget|policy|login|sign\s+in|captcha)\b',
    re.IGNORECASE
)

_WEIGHTS = [
    ("date_density",        2.5,      5.0),
    ("job_kw_density",      3.0,      6.0),
    ("anti_kw_count",      -1.5,      8.0),
    ("table_rows",          0.05,    30.0),
    ("list_items",          0.02,    50.0),
    ("pdf_links",           1.2,     10.0),
    ("link_density",       -0.03,    20.0),
    ("structured_ratio",    0.8,      3.0),
]

_BIAS = -2.0


def extract_features(html: str) -> dict:
    html = html[:100_000]
    text = _HTML_TAG_RE.sub(' ', html)
    text = _WHITESPACE_RE.sub(' ', text)
    text_len = max(len(text), 1)

    date_count = len(_DATE_RE.findall(text))
    date_density = date_count / (text_len / 1000)

    job_kw_count = len(_JOB_KW_RE.findall(text))
    job_kw_density = job_kw_count / (text_len / 1000)

    anti_kw_count = len(_ANTI_KW_RE.findall(text))
    table_rows = len(_TABLE_ROW_RE.findall(html))
    list_items = len(_LIST_ITEM_RE.findall(html))
    pdf_links = len(_PDF_LINK_RE.findall(html))
    total_links = len(_LINK_RE.findall(html))
    link_density = total_links / (text_len / 1000)
    structured_ratio = (table_rows + list_items) / max(total_links, 1)

    return {
        "date_density":     date_density,
        "job_kw_density":   job_kw_density,
        "anti_kw_count":    anti_kw_count,
        "table_rows":       table_rows,
        "list_items":       list_items,
        "pdf_links":        pdf_links,
        "link_density":     link_density,
        "structured_ratio": structured_ratio,
    }


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        e = math.exp(x)
        return e / (1.0 + e)


def score_page(html: str) -> float:
    if not html or len(html) < 200:
        return 0.0
    features = extract_features(html)
    logit = _BIAS
    for feat_name, weight, clip_max in _WEIGHTS:
        val = min(features.get(feat_name, 0.0), clip_max)
        logit += weight * val
    return _sigmoid(logit)


def is_jobs_page(html: str, threshold: float = 0.40) -> bool:
    return score_page(html) >= threshold
