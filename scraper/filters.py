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
import json
import math
import logging

# Suppress pypdf dictionary warning logs and requests dependency warnings
import warnings
warnings.filterwarnings("ignore", module="pypdf")
warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
warnings.filterwarnings("ignore", category=UserWarning, module="requests")
logging.getLogger("pypdf").setLevel(logging.ERROR)

# ─── Keyword lists & Regexes ────────────────────────────────────────────────

CORE_CS_KEYWORDS = [
    # core CS/IT terms
    "computer science", "computer engineering", "cse",
    "information technology", "i.t.", "software", "programmer", "programming",
    "full stack", "fullstack", "web develop", "app develop",
    "web designer", "application developer",
    # data / AI
    "data science", "data analytics", "data analyst", "data engineer",
    "data engineering", "data scientist", "data analytic",
    "artificial intelligence", "machine learning", "ai/ml",
    "deep learning", "nlp", "computer vision",
    # security / infra
    "cyber security", "cybersecurity", "network security", "information security",
    "devops", "cloud computing", "cloud engineer", "cloud",
    "database", "dbms", "system administrator", "sysadmin",
    "system analyst", "network engineer",
    "blockchain", "quantum computing", "high performance computing", "hpc",
    # IT infrastructure & architecture
    "data centre", "data center", "enterprise architecture",
    # specific technologies
    "laravel", "php", "oracle"
]

OTHER_CS_KEYWORDS = [
    "architect",
    # IT professional roles
    "it officer", "information officer", "it resource", "it professional",
    "it support", "it manager", "it associate", "it consultant", "it specialist",
    "it executive", "developer", "ai", "data"
]

GENERIC_TECH_KEYWORDS = [
    "project engineer", "project associate",
    "project scientist", "project staff", "project technician",
    "senior project", "project support",
    "project assistant", "project officer", "project consultant",
    "senior consultant",
    # Scientist grades at NIC, DRDO, ISRO
    "scientist/engineer", "scientist b", "scientist-b",
    "scientist c", "scientist-c", "scientist d", "scientist-d",
    "scientist 'sc'", "scientist 'sd'", "scientist",
    # Research roles relevant for CSE
    "junior research fellow", "junior research fellowship", "jrf",
    "research associate", "research scientist", "research fellow",
    # CDAC-specific roles
    "adjunct scientist", "adjunct engineer",
    # General technical roles
    "technical assistant", "technical consultant",
    "system engineer", "systems engineer", "technical officer",
    "scientific officer",
    # Telecom / PSU technical roles
    "junior telecom officer", "jto",
    # Scientific assistant roles (BARC, ISRO style)
    "scientific assistant",
]

EXCLUDE_KEYWORDS = [
    # other engineering branches
    "civil", "mechanical", "electrical", "electronics",
    "telecommunication", "telecom", "instrumentation", "chemical", "metallurgy",
    "geology", "geophysics", "agriculture", "physical sciences",
    "life sciences", "ordnance", "ammunition", "architecture",
    "biotechnology", "biotech", "biology", "chemistry", "physics", "toxicology", "geothermal", "environmental",
    "materials science", "manufacturing", "mathematics", "maths", "cfd", "fluid dynamics", "coal", "gasification", "beneficiation",
    # non-engineering / support roles & trades
    "driver", "havildar", "fireman", "cook", "catering", "canteen",
    "nurse", "nursing", "pharmacist", "medical", "radiographer", "radiography",
    "pathology", "doctor", "doctors", "physiotherapy", "physiotherapist",
    "lab technician", "stenographer", "draughtsman", "draftsman", "library",
    "dental", "prosthodontics", "surveyor",
    "security officer", "office attendant", "peon",
    "multi tasking", "mts", "trade apprentice", "iti apprentice",
    "technician b", "technician-b", "technician a", "technician-a",
    "clerk", "typist", "receptionist", "probationary officer", "probationary officers",
    "fishery", "fisheries", "horticulture", "veterinary", "animal husbandry",
    "agm (security)", "dgm (security)",
    # administrative, legal, hr, and financial roles
    "legal", "law", "finance", "accounts", "audit", "marketing",
    "administrative officer", "admin officer", "human resource", "hr",
    "personal assistant", "private secretary", "administration", "administrative",
    "office assistant", "accounts assistant", "administrative assistant",
    "admin assistant", "clerical assistant", "canteen assistant",
    "nursing assistant", "dental assistant", "hostel assistant",
    "care assistant", "shop assistant", "pa/ps", "pa / ps", "cfo", "registrar", "purchase", "store",
    "stores", "materials management", "section officer", "child development", "land acquisition", 
    "forest clearance", "public information officer", "tourist information officer", "information officer",
    "private developer", "land developer", "housing developer", "real estate developer",
    "corporate relations", "recruitment data",
    # physical security
    "internal security", "national security", "homeland security", "security guard", "security agency", "security force",
    # management / executive roles (not CSE-specific)
    "chairman", "controller", "managing director", "director", "cvo", "vigilance",
    "grievance", "gst", "nodal",
    # project management (non-CSE) - project engineer/scientist are kept in GENERIC_TECH above
    "project manager",
    # teaching / academic non-research
    "guest faculty", "teacher", "professor", "principal", "lecturer",
    # language / translation
    "translator", "translation", "hindi", "rajbhasha",
    # Tenders / Tenders junk (non-active postings)
    "tender", "bid", "procurement", "auction", "lease", "patta", "deed", "expression of interest", 
    "eoi", "rfp", "quotation", "quotations", "roadmap", "study", "policy", "strategy", "guidelines", 
    "conference", "workshop", "symposium", "seminar", "concludes", "brochure", "tips", "awareness", 
    "how to", "instruction", "instructions", "banner", "logo",
    # Exam / Results junk (non-active postings)
    "syllabus", "corrigendum", "result", "selection list", "select list",
    "marks", "answer key", "admit card", "screening status", "exam date",
    "shortlisted", "careers", "vacancies", "internship", "annexure", "data entry",
    "circulars", "notifications", "committee", "complaints", "grievance", 
    "grievances", "nodal", "officer list", "officers list", "contact us", 
    "about us", "feedback", "menu",
    # Results & Selection list additions
    "provisionally selected", "selected candidates", "selected candidate", 
    "allotment letter", "successful candidates", "joining status", "joining date",
    "reporting date", "verification date", "list of candidates", "candidate list",
    "marks list", "score card", "interview schedule", "interview dates",
    "venue for interview", "shortlisted candidates", "final result", "written test",
    # General navigation & introduction text exclusions
    "welcome to", "ongoing recruitment", "ongoing recruitments", "ongoing exam",
    "offer of admission", "admission list", "admission notice", "admission process",
    # Advisory / notification-style postings that are not job openings
    "notification for engagement", "notification of engagement",
    "engagement of advisor", "engagement of sr. advisor", "engagement of senior advisor",
    "advisor (secretarial)", "advisor (survey)", "advisor (mining)",
    "advisor (land", "advisor (personnel)", "advisor (security)"
]

def _build_boundary_regex(keywords):
    patterns = []
    for kw in keywords:
        # Normalize and escape
        escaped = re.escape(kw.strip())
        escaped = escaped.replace('\\ ', '\\s+')
        # Wrap in word boundary if it starts/ends with alphanumeric
        pattern = escaped
        if kw.strip()[0].isalnum():
            pattern = r'\b' + pattern
        if kw.strip()[-1].isalnum():
            pattern = pattern + r'\b'
        patterns.append(pattern)
    return re.compile('|'.join(patterns), re.IGNORECASE)

CORE_CS_RE = _build_boundary_regex(CORE_CS_KEYWORDS)
OTHER_CS_RE = _build_boundary_regex(OTHER_CS_KEYWORDS)
GENERIC_TECH_RE = _build_boundary_regex(GENERIC_TECH_KEYWORDS)
EXCLUDE_RE = _build_boundary_regex(EXCLUDE_KEYWORDS)


# ─── Dual TF-IDF Title Similarity Classifier ────────────────────────────────
class TFIDFSimilarityClassifier:
    """
    Lightweight, zero-dependency TF-IDF Cosine Similarity engine.
    Compares job titles against CS/IT reference profiles and exclusion profiles.
    """
    def __init__(self):
        # CS/IT Vocabulary Profile — deliberately narrow to avoid false positives
        self.cse_vocab = {
            "computer", "software", "developer", "programmer", "php", "laravel",
            "python", "java", "database", "cyber", "devops", "mca", "cse"
        }
        # Exclusion Vocabulary Profile (Other fields, support roles)
        self.exclude_vocab = {
            "civil", "mechanical", "electrical", "chemical", "nurse",
            "medical", "doctor", "pharmacist", "driver", "clerk", "typist",
            "stenographer", "accountant", "accounts", "audit", "legal",
            "law", "hr", "admin", "helper", "cook", "apprentice",
            "surgeon", "physician", "radiologist", "hospital", "medic",
            "medics", "dentist", "geology", "geophysicist", "geophysics",
            "chemistry", "physics", "forester", "forestry",
            "biotechnology", "biotech", "biology", "toxicology", "draftsman"
        }
        
    def _tokenize(self, text):
        return [w.strip() for w in re.split(r"[^a-zA-Z]", text.lower()) if len(w.strip()) > 1]

    def _compute_tf(self, tokens):
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        return tf

    def calculate_similarity(self, title, profile_vocab):
        tokens = self._tokenize(title)
        if not tokens:
            return 0.0
            
        tf = self._compute_tf(tokens)
        
        # Calculate term overlap and simple dot product
        dot_product = 0.0
        for token, freq in tf.items():
            if token in profile_vocab:
                # Give higher weight to rare/selective terms if matched
                dot_product += freq * 1.0
                
        # Normalize against the query vector length only (avoiding dilution by vocabulary profile size)
        vec_len = sum(val ** 2 for val in tf.values()) ** 0.5
        
        if vec_len == 0:
            return 0.0
            
        return dot_product / vec_len

    def classify_title(self, title):
        cse_sim = self.calculate_similarity(title, self.cse_vocab)
        excl_sim = self.calculate_similarity(title, self.exclude_vocab)
        return cse_sim, excl_sim

# Instantiate the similarity classifier
title_similarity_classifier = TFIDFSimilarityClassifier()


# ─── Dual TF-IDF Weighted Word Embedding Cosine Similarity Classifier ───────
class TFIDFEmbeddingClassifier:
    """
    Combines TF-IDF weights with Stanford GloVe 50d word embeddings.
    Computes TF-IDF weighted average vectors for job titles and measures
    cosine similarity against CS and Exclude class profiles.
    """
    def __init__(self, embeddings_path=None):
        self.embeddings = {}
        self.loaded = False
        
        if embeddings_path is None:
            embeddings_path = os.path.join(os.path.dirname(__file__), "word_embeddings.json")
            
        if os.path.exists(embeddings_path):
            try:
                with open(embeddings_path, "r", encoding="utf-8") as f:
                    self.embeddings = json.load(f)
                self.loaded = True
            except Exception:
                pass
                
        # Vocabulary profiles (from TF-IDF vocab profiles)
        self.cse_vocab = {
            "computer", "software", "developer", "programmer", "php", "laravel",
            "python", "java", "database", "cyber", "devops", "mca", "cse"
        }
        self.exclude_vocab = {
            "civil", "mechanical", "electrical", "chemical", "nurse",
            "medical", "doctor", "pharmacist", "driver", "clerk", "typist",
            "stenographer", "accountant", "accounts", "audit", "legal",
            "law", "hr", "admin", "helper", "cook", "apprentice",
            "surgeon", "physician", "radiologist", "hospital", "medic",
            "medics", "dentist", "geology", "geophysicist", "geophysics",
            "chemistry", "physics", "forester", "forestry",
            "biotechnology", "biotech", "biology", "toxicology", "draftsman"
        }
        
        # Precompute target centroids (profile vectors)
        self.cs_centroid = self._compute_profile_centroid(self.cse_vocab)
        self.exclude_centroid = self._compute_profile_centroid(self.exclude_vocab)

    def _tokenize(self, text):
        return [w.strip() for w in re.split(r"[^a-zA-Z]", text.lower()) if len(w.strip()) > 1]

    def _compute_profile_centroid(self, vocab_set):
        if not self.loaded:
            return None
        centroid = [0.0] * 50
        count = 0
        for word in vocab_set:
            if word in self.embeddings:
                vec = self.embeddings[word]
                for d in range(50):
                    centroid[d] += vec[d]
                count += 1
        if count > 0:
            centroid = [x / count for x in centroid]
        return centroid

    def _cosine_similarity(self, v1, v2):
        if not v1 or not v2:
            return 0.0
        dot = sum(x*y for x, y in zip(v1, v2))
        norm1 = math.sqrt(sum(x*x for x in v1))
        norm2 = math.sqrt(sum(x*x for x in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def classify_title(self, title):
        if not self.loaded or not self.cs_centroid or not self.exclude_centroid:
            return 0.0, 0.0
            
        tokens = self._tokenize(title)
        if not tokens:
            return 0.0, 0.0
            
        # Compute local TF (term frequency)
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
            
        # Compute TF-IDF weighted title vector
        title_vec = [0.0] * 50
        total_weight = 0.0
        for token, freq in tf.items():
            if token in self.embeddings:
                vec = self.embeddings[token]
                weight = freq * (2.0 if (token in self.cse_vocab or token in self.exclude_vocab) else 1.0)
                for d in range(50):
                    title_vec[d] += vec[d] * weight
                total_weight += weight
                
        if total_weight == 0:
            return 0.0, 0.0
            
        title_vec = [x / total_weight for x in title_vec]
        
        # Calculate similarity against profiles
        cs_sim = self._cosine_similarity(title_vec, self.cs_centroid)
        exclude_sim = self._cosine_similarity(title_vec, self.exclude_centroid)
        return cs_sim, exclude_sim

# Instantiate the embedding classifier
tfidf_embedding_classifier = TFIDFEmbeddingClassifier()


# ─── Zero-Dependency Naive Bayes Classifier ─────────────────────────────────
class NaiveBayesClassifier:
    """
    Zero-dependency Multinomial Naive Bayes classifier for job titles.
    Loads pre-trained prior and likelihood parameters from a JSON weights file.
    """
    def __init__(self, weights_path=None):
        self.priors = {}
        self.oov = {}
        self.weights = {}
        self.loaded = False
        
        if weights_path is None:
            weights_path = os.path.join(os.path.dirname(__file__), "model_weights.json")
            
        if os.path.exists(weights_path):
            try:
                with open(weights_path, "r", encoding="utf-8") as f:
                    model = json.load(f)
                self.priors = model["priors"]
                self.oov = model["oov"]
                self.weights = model["weights"]
                self.loaded = True
            except Exception:
                pass

    def _tokenize(self, text):
        words = [w.strip() for w in re.split(r"[^a-zA-Z0-9]", text.lower()) if len(w.strip()) > 1]
        features = list(words)
        for i in range(len(words) - 1):
            features.append(f"{words[i]}_{words[i+1]}")
        return features

    def predict(self, title):
        if not self.loaded:
            return None, None
            
        features = self._tokenize(title)
        
        score_relevant = self.priors["relevant"]
        score_excluded = self.priors["excluded"]
        
        for feat in features:
            if feat in self.weights:
                score_relevant += self.weights[feat]["relevant"]
                score_excluded += self.weights[feat]["excluded"]
                
        return score_relevant, score_excluded

# Instantiate the Naive Bayes classifier
naive_bayes_classifier = NaiveBayesClassifier()


# ─── Layer 2: Per-org context rules ─────────────────────────────────────────
#
# These orgs are *primarily* CS/IT organizations.
# When their posting title is "uncertain" (no discipline signal),
# we apply domain-specific heuristics to decide relevance.

# Orgs where most non-excluded postings are CS-relevant by default.
# Reasoning: CDAC = CS org, NIC = IT, CRIS = Railway IT, STPI = Software parks,
# C-DOT = Telematics, CERT-In = Cybersecurity.
# IITs, IIITs, NITs: premier tech institutes where most project/research
# postings (JRF, SRF, RA, Project Associate) are CS-relevant by default.
CS_FIRST_ORGS = {
    # Core CS/IT organizations
    "cdac", "nic", "cris", "stpi", "cdot", "certin",
    # IITs
    "iitb", "iitbbs", "iitbhilai", "iitbhu", "iitd", "iitdh", "iitg",
    "iitgn", "iitgoa", "iith", "iiti", "iitism", "iitj", "iitjammu",
    "iitk", "iitkgp", "iitm", "iitmandi", "iitp", "iitpkd", "iitr",
    "iitrpr", "iittp",
    # IIITs
    "iiitb", "iiitbh", "iiitbhopal", "iiitd", "iiitdwd", "iiitg",
    "iiith", "iiitk", "iiitkalyani", "iiitkottayam", "iiitl", "iiitm",
    "iiitnagpur", "iiitp", "iiitranchi", "iiits", "iiitsurat", "iiitu",
    "iiitvadodara",
    # NITs
    "nitc", "nitdelhi", "nitdgp", "nitgoa", "nith", "nitj", "nitjsr",
    "nitk", "nitkkr", "nitm", "nitmanipur", "nitmz", "nitnagaland",
    "nitp", "nitpy", "nitrkl", "nitrr", "nits", "nitsikkim", "nitsri",
    "nitt", "nituk", "nitw",

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
    "uppsc": [
        # UPPSC archived/completed recruitments — exclude notices for concluded exams
        ("notice regarding advt. no. a-4/e-1/2025", "excluded"),
        ("notice regarding advt. no. d-2/e-1/2024", "excluded"),
        ("fill online details for advt", "excluded"),
        ("assistant architect", "excluded"),
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
    "trade", "helper", "labour", "biotechnology", "biotech",
    "biology", "chemistry", "physics", "agriculture", "forest",
    "geology", "animalhusbandry", "veterinary",
    "mech", "prod", "production",
]

# Regex to match department/academic pages that look like CS/IT but aren't job postings.
# E.g. "Computer Science & Engineering" (department page), "B.Tech. Computer Science"
_DEPT_PAGE_RE = re.compile(
    r'^\s*(?:department\s+of\s+)?computer\s+(?:science|engineering)(?:\s+(?:&|and)\s+(?:computer\s+)?engineering)?\s*$'
    r'|^\s*b\.?tech\.?\s+computer\s+science\s+and\s+engineering\s*$'
    r'|^\s*computer\s+science\s+(?:&|and)\s+eng(?:ineering|g)?\s*$',
    re.IGNORECASE
)

# Regex for noisy portal/utility page titles
_NOISE_TITLE_RE = re.compile(
    r'^\s*(?:online\s+)?(?:recruitment\s+)?portal\s*$'
    r'|^\s*(?:online\s+)?payment\s*$'
    r'|^\s*application\s+(?:form|format)\s*$'
    r'|^\s*search\s+application\s*$'
    r'|^\s*new\s+application\s+form\s*$',
    re.IGNORECASE
)




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
    Download and scan a linked PDF for discipline keywords using proximity scoring
    and keyword checks to determine CS/IT eligibility.
    Returns 'relevant', 'excluded', or None (if inconclusive).
    """
    if not url or not session:
        return None

    # Scan PDFs or URLs that are likely to stream/return PDFs
    url_lower = url.lower()
    is_pdf_like = (
        url_lower.endswith(".pdf") or 
        "pdf" in url_lower or 
        "fileviewer" in url_lower or 
        "document" in url_lower or 
        "download" in url_lower or
        "viewer" in url_lower
    )
    if not is_pdf_like:
        return None

    text = _extract_pdf_text(url, session)
    if not text or len(text) < 50:
        return None

    text_lower = text.lower()

    # Extra CS/IT keywords to check
    extra_cs_kws = ["mca", "b.tech cs", "b.tech it", "b.e. cs", "b.e. it", "copa"]
    all_cs_kws = PDF_CS_KEYWORDS + extra_cs_kws

    # 1. Broad keyword count
    cs_hits = [kw for kw in all_cs_kws if kw in text_lower]
    non_cs_hits = [kw for kw in PDF_NON_CS_KEYWORDS if kw in text_lower]

    # If CS/IT keywords are completely absent, we can safely exclude
    if not cs_hits:
        return "excluded"

    # 2. Extract sections of text surrounding qualification keywords (proximity check)
    qual_patterns = [r"\bqualification\b", r"\beligibility\b", r"\beducation\b", r"\bdiscipline\b", r"\bdegree\b"]
    qual_sections = []
    for pattern in qual_patterns:
        for m in re.finditer(pattern, text_lower):
            start = max(0, m.start() - 250)
            end = min(len(text_lower), m.end() + 250)
            qual_sections.append(text_lower[start:end])

    # Count keywords inside the qualification context blocks (with extra weight)
    qual_cs_score = 0
    qual_non_cs_score = 0
    if qual_sections:
        combined_quals = " ".join(qual_sections)
        qual_cs_score = sum(2 for kw in all_cs_kws if kw in combined_quals)
        qual_non_cs_score = sum(2 for kw in PDF_NON_CS_KEYWORDS if kw in combined_quals)

    # 3. Combine scores
    total_cs_score = len(cs_hits) + qual_cs_score
    total_non_cs_score = len(non_cs_hits) + qual_non_cs_score

    if total_cs_score == 0:
        return "excluded"
    elif total_cs_score > total_non_cs_score:
        return "relevant"
    else:
        return "excluded"


# ─── Main classify function ─────────────────────────────────────────────────

def classify(title, link="", org_key="", session=None, use_ml=True):
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

    # Exclude extremely short titles that are likely noise (like page numbers, file sizes, or menu links)
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
    if len(clean_title) < 4:
        return "excluded"

    # Exclude department/academic page names that are not job postings
    if _DEPT_PAGE_RE.match(clean_title):
        return "excluded"



    # Exclude noisy portal/utility page titles
    if _NOISE_TITLE_RE.match(clean_title):
        return "excluded"

    # Exclude social media share links and generic portal content
    if any(noise in t for noise in [
        "speech given by honourable", "state profile", "learning in telangana",
        "why work at ", "online recruitment portal",
        "notice 3_application in draft", "notice 2_application in draft",
        "notice 3_application count", "notice 2_application count",
    ]):
        return "excluded"
    
    # Exclude patterns like (1.23 MB) or 1.23 MB or KB notices
    if re.search(r'\b\d+(\.\d+)?\s*(mb|kb)\b', t):
        return "excluded"
        
    # Exclude common single-word menu items and organizational navigation links
    if clean_title.lower() in (
        "careers", "vacancies", "internship", "downloads", "home", "archive", 
        "about us", "contact us", "life at ongc", "employee welfare", 
        "employee engagement", "skill development", "mentoring", 
        "mount everest expedition", "live your passion", "recruitment methodology", 
        "high growth curve", "intern with us", "forms", "recruitment notices", 
        "results", "audio-visuals", "audiovisuals", "work with us", "why join", "about", 
        "employee corner", "sitemap", "disclaimer", "terms of use", 
        "privacy policy", "help", "faq", "faqs", "gallery", "feedback", 
        "last →", "first ←", "next →", "previous ←", "apprenticeship opportunities",
        "last", "first", "next", "previous", "application"
        # Exact-match generic links & actions
        "apply online", "apply now", "click here", "read more", "view details", 
        "download pdf", "view all", "ongoing recruitments", "welcome", "welcome to ibps",
        "other ongoing recruitments", "other ongoing recruitments view all",
        "career",
        # Exact-match banking services and utilities
        "net banking", "internet banking", "online banking", "retail banking", 
        "corporate banking", "mobile banking", "personal banking", "business banking", 
        "savings account", "online account", "account opening", "open account", 
        "online account opening", "credit cards", "debit cards", "loans", "deposits",
        "wealth management", "mutual funds", "insurance", "demat", "forex",
        "remittance", "payments", "cards", "services", "products", "investor relations",
        # Results & Selection list exact matches
        "letter to successful candidates", "successful candidates", "allotment letter",
        # Portal utility pages and generic navigation
        "online payment", "preview application", "search application and transaction no",
        "new application form", "nic user manual", "question paper",
        # Department / academic pages (not job postings)
        "b.tech. computer science and engineering",
        # Generic department names without recruitment context
        "application",
    ):
        return "excluded"



    # Clean the title of organization name noise to avoid matching CS terms in organization names
    title_clean = re.sub(r'\bnielit\b', '', title, flags=re.IGNORECASE)
    title_clean = re.sub(r'national\s+institute\s+of\s+electronics\s+(&|and)\s+information\s+technology', '', title_clean, flags=re.IGNORECASE)

    # ── Layer 0: Per-org overrides (highest priority — org-specific rules win over generic keywords) ──
    if org_key:
        overrides = ORG_OVERRIDES.get(org_key, [])
        for pattern, classification in overrides:
            if pattern in t:
                return classification

    # ── Layer 1: Title keyword matching with regex ──
    # 1. Exclude wins first (so result/marks notices are pruned even if they contain CS terms)
    if EXCLUDE_RE.search(title_clean):
        return "excluded"

    # 2. Core CS wins next
    if CORE_CS_RE.search(title_clean):
        return "relevant"

    # 3. Other CS wins next
    if OTHER_CS_RE.search(title_clean):
        return "relevant"

    # ── Layer 1.2: URL-based absolute exclusion ──
    if link:
        url_lower = link.lower()
        non_cs_url_hits = sum(1 for kw in NON_CS_URL_KEYWORDS if kw in url_lower)
        if non_cs_url_hits >= 1 and not CORE_CS_RE.search(title_clean):
            return "excluded"

    is_bank = org_key.startswith("bank_") or org_key in ("ibps", "sbi", "rbi", "nabard", "sebi", "sidbi", "nhb")

    # Pre-calculate similarity scores (used by ML safeguards)
    cse_sim, excl_sim = title_similarity_classifier.classify_title(title_clean)
    has_generic = bool(GENERIC_TECH_RE.search(title_clean))
    
    emb_cs_sim, emb_excl_sim = 0.0, 0.0
    if use_ml and tfidf_embedding_classifier.loaded:
        emb_cs_sim, emb_excl_sim = tfidf_embedding_classifier.classify_title(title_clean)

    # ── Layer 1.5: Naive Bayes Machine Learning Classifier ──
    if use_ml and naive_bayes_classifier.loaded:
        nb_rel, nb_excl = naive_bayes_classifier.predict(title_clean)
        if nb_rel is not None and nb_excl is not None:
            if nb_rel > nb_excl + 2.0:
                # Safeguard: Naive Bayes can only mark relevant if there's some CS signal
                # either in TF-IDF vocab, strong embedding match with margin, or generic tech keyword
                has_emb_match = (emb_cs_sim >= 0.55 and emb_cs_sim > emb_excl_sim + 0.12)
                if cse_sim > 0.0 or has_emb_match or has_generic:
                    return "relevant"
            elif nb_excl > nb_rel + 2.0:
                if not is_bank:
                    return "excluded"

    # ── Layer 1.6: TF-IDF Cosine Similarity for synonyms ──
    if cse_sim >= 0.25 and cse_sim > excl_sim:
        return "relevant"
    elif excl_sim >= 0.25 and excl_sim > cse_sim:
        if not is_bank:
            return "excluded"

    # ── Pre-check: Generic tech keywords for CS-first orgs ──
    # Do this BEFORE embedding layer so that ambiguous words like "engineer"
    # in GloVe space (shared with civil/mech) don't wrongly exclude them.
    if has_generic and org_key in CS_FIRST_ORGS:
        return "relevant"

    # ── Layer 1.7: TF-IDF Weighted Word Embedding Cosine Similarity ──
    if use_ml and tfidf_embedding_classifier.loaded:
        # Cosine similarity threshold of 0.55 and margin of 0.12.
        # NOTE: Do NOT let embeddings exclude generic-tech titles (scientist, engineer, etc.)
        # — those are intentionally ambiguous and must reach Layer 2 org-context rules.
        if emb_cs_sim >= 0.55 and emb_cs_sim > emb_excl_sim + 0.12:
            return "relevant"
        elif emb_excl_sim >= 0.55 and emb_excl_sim > emb_cs_sim + 0.12 and not has_generic:
            if not is_bank:
                return "excluded"

    # 4. Generic tech keywords next (for non-CS-first orgs, fall through to Layer 2)
    # (has_generic already computed above; used again in fallback below)

    # ── Layer 2a: Per-org context rules ────────────────────────────────────
    if org_key:
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
        if non_cs_url_hits >= 1 and not CORE_CS_RE.search(title_clean):
            return "excluded"

    # ── Layer 3: PDF content extraction ────────────────────────────────────
    # Scan PDF if explicitly requested OR as a final fallback to resolve "uncertain" postings
    if session and link:
        is_pdf_like = (
            link.lower().endswith(".pdf") or 
            "pdf" in link.lower() or 
            "download" in link.lower() or 
            "file" in link.lower() or
            "viewer" in link.lower()
        )
        is_force_scan = os.environ.get("SCRAPER_PDF_SCAN") == "1"
        if is_force_scan or is_pdf_like:
            pdf_result = _classify_by_pdf(link, session)
            if pdf_result:
                return pdf_result

    # Fallback: if it matched a generic keyword and didn't trigger any exclusion,
    # it is relevant by default.
    if has_generic:
        return "relevant"

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
