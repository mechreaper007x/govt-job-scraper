# config.py
# Configuration for the Indian Government Job Scraper

DEFAULT_HEADERS = {
    "User-Agent": "Government Job Tracker Script (personal/non-commercial monitoring; contact: savyasachimishra@example.com)"
}

ORGS_CONFIG = {
    # ── Core MeitY / Science & Tech ────────────────────────────────────────────
    "cdac": {
        "name": "C-DAC (Centre for Development of Advanced Computing)",
        "url": "https://www.cdac.in/index.aspx?id=current_jobs"
    },
    "nielit": {
        "name": "NIELIT (National Institute of Electronics & IT)",
        "url": "https://www.nielit.gov.in/form?formName=Recruitments&center=HQ",
        "special": "api"  # uses JSON API, not static HTML scraping
    },
    "stpi": {
        "name": "STPI (Software Technology Parks of India)",
        "url": "https://www.stpi.in/careers"
    },
    "nic": {
        "name": "NIC (National Informatics Centre)",
        "url": "https://recruitment.nic.in/index_new.php"
    },
    "cdot": {
        "name": "C-DOT (Centre for Development of Telematics)",
        "url": "https://www.cdot.in/cdotweb/web/current_openings.php?lang=en"
    },
    "certin": {
        "name": "CERT-In (Indian Computer Emergency Response Team)",
        "url": "https://www.cert-in.org.in/s2cMainServlet?pageid=VLNLISTRE"
    },
    # ── Defence / Strategic ────────────────────────────────────────────────────
    "drdo": {
        "name": "DRDO (Defence Research and Development Organisation)",
        "url": "https://www.drdo.gov.in/drdo/en/offerings/vacancies"
    },
    "bel": {
        "name": "BEL (Bharat Electronics Limited)",
        "url": "https://bel-india.in/job-notifications/"
    },
    "barc": {
        "name": "BARC (Bhabha Atomic Research Centre)",
        "url": "https://www.barc.gov.in/rss_barc.xml"
    },
    # ── Space / Aeronautics ─────────────────────────────────────────────────────
    "isro": {
        "name": "ISRO (Indian Space Research Organisation)",
        "url": "https://www.isro.gov.in/ViewAllOpportunities.html"
    },
    "hal": {
        "name": "HAL (Hindustan Aeronautics Limited)",
        "url": "https://hal-india.co.in/backend/wp-json/hal/v1/career",
        "special": "hal_api"  # Angular SPA; career data served via custom POST WP REST API
    },
    # ── Electronics / Manufacturing PSUs ──────────────────────────────────────
    "ecil": {
        "name": "ECIL (Electronics Corporation of India Ltd)",
        "url": "https://www.ecil.co.in/jobopenings"
    },
    # ── Railway IT ─────────────────────────────────────────────────────────────
    "cris": {
        "name": "CRIS (Centre for Railway Information Systems)",
        "url": "https://www.cris.org.in/loadpage?page=indexcareer"
    },
    # ── Telecom ────────────────────────────────────────────────────────────────
    "bsnl": {
        "name": "BSNL (Bharat Sanchar Nigam Ltd)",
        "url": "https://externalexam.bsnl.co.in/"
    },
    # ── Aggregators ────────────────────────────────────────────────────────────
    "employment_news": {
        "name": "Employment News (Ministry of I&B)",
        "url": "https://employmentnews.gov.in/NewEmp/AllJobs.aspx?k=All"
    },
    # ── State PSC ──────────────────────────────────────────────────────────────
    "uppsc": {
        "name": "UPPSC (Uttar Pradesh Public Service Commission)",
        "url": "https://uppsc.up.nic.in/"
    }
}

# Orgs to run in the main GitHub Actions workflow
MAIN_ORGS = [
    "cdac", "nielit", "stpi", "nic", "cdot", "certin",
    "drdo", "bel", "barc", "isro", "hal", "ecil", "cris",
    "bsnl", "employment_news"
]
UPPSC_ORGS = ["uppsc"]
