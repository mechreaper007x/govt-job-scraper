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
        "url": "https://bel-india.in/job-notifications/",
        "note": "Site frequently returns 500 Database Error (server-side). BEL also uses temporary portals on jobapply.in, cdn.digialm.com (TCS iON), and cbexams.com for specific drives, but these are per-drive only and cannot be used for ongoing monitoring."
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
    "ncs": {
        "name": "NCS (National Career Service - Ministry of Labour & Employment)",
        "url": "https://www.ncs.gov.in/",
        "special": "ncs_api"  # uses internal JSON API (POST /api/v1/job-posts/search)
    },
    # ── State PSC ──────────────────────────────────────────────────────────────
    "uppsc": {
        "name": "UPPSC (Uttar Pradesh Public Service Commission)",
        "url": "https://uppsc.up.nic.in/"
    },
    # ── Oil & Gas PSUs ─────────────────────────────────────────────────────
    "ongc": {
        "name": "ONGC (Oil and Natural Gas Corporation)",
        "url": "https://ongcindia.com/web/eng/career/recruitment-notice"
    },
    # ── Steel / Heavy Manufacturing PSUs ───────────────────────────────────
    "sail": {
        "name": "SAIL (Steel Authority of India)",
        "url": "https://www.sail.co.in/careers"
    },
    # ── Power PSUs ─────────────────────────────────────────────────────────
    "ntpc": {
        "name": "NTPC (National Thermal Power Corporation)",
        "url": "https://www.ntpc.co.in/page/career-opportunities"
    },
    # ── Aviation / Infrastructure ──────────────────────────────────────────
    "aai": {
        "name": "AAI (Airports Authority of India)",
        "url": "https://www.aai.aero/en/careers/recruitment"
    },
    # ── Indian Railways ────────────────────────────────────────────────────
    "rrb": {
        "name": "Indian Railways (RRB)",
        "url": "https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,554",
        "note": "Static board page with recruitment links — rrbapply.gov.in is SPA and not scrapable"
    }
}

# Orgs to run in the main GitHub Actions workflow
MAIN_ORGS = [
    "cdac", "nielit", "stpi", "nic", "cdot", "certin",
    "drdo", "bel", "barc", "isro", "hal", "ecil", "cris",
    "bsnl", "employment_news", "ncs",
    "ongc", "sail", "ntpc", "aai"
]
UPPSC_ORGS = ["uppsc"]

# ── Discovery Engine Configuration ────────────────────────────────────────────
# Seed homepages and career-related URL patterns per org.
# The discovery engine uses these to find new/changed job listing URLs.

DISCOVERY_CONFIG = {
    "cdac": {
        "name": "C-DAC (Centre for Development of Advanced Computing)",
        "homepages": ["https://www.cdac.in/"],
        "patterns": [r"current.?job", r"career", r"openings", r"recruit", r"vacanc", r"notification"],
    },
    "nielit": {
        "name": "NIELIT (National Institute of Electronics & IT)",
        "homepages": ["https://www.nielit.gov.in/"],
        "patterns": [r"recruit", r"career", r"job", r"vacanc"],
    },
    "stpi": {
        "name": "STPI (Software Technology Parks of India)",
        "homepages": ["https://www.stpi.in/"],
        "patterns": [r"career", r"job", r"recruit", r"openings"],
    },
    "nic": {
        "name": "NIC (National Informatics Centre)",
        "homepages": ["https://www.nic.in/", "https://recruitment.nic.in/"],
        "patterns": [r"recruit", r"job", r"career", r"vacanc"],
    },
    "cdot": {
        "name": "C-DOT (Centre for Development of Telematics)",
        "homepages": ["https://www.cdot.in/"],
        "patterns": [r"openings", r"career", r"recruit", r"job", r"vacanc"],
    },
    "certin": {
        "name": "CERT-In (Indian Computer Emergency Response Team)",
        "homepages": ["https://www.cert-in.org.in/"],
        "patterns": [r"recruit", r"vacanc", r"job", r"career"],
    },
    "drdo": {
        "name": "DRDO (Defence Research and Development Organisation)",
        "homepages": ["https://www.drdo.gov.in/"],
        "patterns": [r"vacanc", r"recruit", r"career", r"job", r"offerings"],
    },
    "bel": {
        "name": "BEL (Bharat Electronics Limited)",
        "homepages": ["https://bel-india.in/"],
        "patterns": [r"job", r"career", r"recruit", r"notification", r"vacanc", r"engagement"],
    },
    "barc": {
        "name": "BARC (Bhabha Atomic Research Centre)",
        "homepages": ["https://www.barc.gov.in/"],
        "patterns": [r"career", r"recruit", r"job", r"vacanc", r"rss"],
    },
    "isro": {
        "name": "ISRO (Indian Space Research Organisation)",
        "homepages": ["https://www.isro.gov.in/"],
        "patterns": [r"opportunit", r"recruit", r"career", r"job", r"vacanc"],
    },
    "hal": {
        "name": "HAL (Hindustan Aeronautics Limited)",
        "homepages": ["https://hal-india.co.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"engagement"],
    },
    "ecil": {
        "name": "ECIL (Electronics Corporation of India Ltd)",
        "homepages": ["https://www.ecil.co.in/"],
        "patterns": [r"job", r"career", r"recruit", r"openings", r"vacanc"],
    },
    "cris": {
        "name": "CRIS (Centre for Railway Information Systems)",
        "homepages": ["https://www.cris.org.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"openings"],
    },
    "bsnl": {
        "name": "BSNL (Bharat Sanchar Nigam Ltd)",
        "homepages": ["https://www.bsnl.co.in/"],
        "patterns": [r"exam", r"recruit", r"career", r"job", r"vacanc"],
    },
    "employment_news": {
        "name": "Employment News (Ministry of I&B)",
        "homepages": ["https://employmentnews.gov.in/"],
        "patterns": [r"job", r"vacanc", r"recruit", r"employment", r"all.?job"],
    },
    "ncs": {
        "name": "NCS (National Career Service - Ministry of Labour & Employment)",
        "homepages": ["https://www.ncs.gov.in/", "https://betacloud.ncs.gov.in/"],
        "patterns": [r"job", r"career", r"search", r"listing", r"vacanc"],
    },
    "uppsc": {
        "name": "UPPSC (Uttar Pradesh Public Service Commission)",
        "homepages": ["https://uppsc.up.nic.in/"],
        "patterns": [r"recruit", r"notif", r"vacanc", r"advert"],
    },
    "ongc": {
        "name": "ONGC (Oil and Natural Gas Corporation)",
        "homepages": ["https://ongcindia.com/web/eng/career"],
        "patterns": [r"recruit", r"vacanc", r"career", r"job", r"engagement"],
    },
    "sail": {
        "name": "SAIL (Steel Authority of India)",
        "homepages": ["https://www.sail.co.in/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"job", r"engagement"],
    },
    "ntpc": {
        "name": "NTPC (National Thermal Power Corporation)",
        "homepages": ["https://www.ntpc.co.in/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"job"],
    },
    "aai": {
        "name": "AAI (Airports Authority of India)",
        "homepages": ["https://www.aai.aero/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"job", r"notification"],
    },
    "rrb": {
        "name": "Indian Railways (RRB)",
        "homepages": ["https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,554"],
        "patterns": [r"recruit", r"vacanc", r"notification", r"censal"],
    },
}
