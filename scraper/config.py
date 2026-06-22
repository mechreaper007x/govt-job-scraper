# config.py
# Configuration for the Indian Government Job Scraper

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
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
    "drdo_spa": {
        "name": "DRDO (Playwright SPA)",
        "url": "https://www.drdo.gov.in/drdo/en/offerings/vacancies",
        "special": "playwright",  # JS-rendered card layout; static parser already works, SPA validates framework
        "note": "Playwright-powered variant of DRDO to validate the generic SPA parser on a second target."
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
        "url": "https://www.sailcareers.com",
        "note": "May fail with SSL certificate chain error — server-side issue."
    },
    # ── Power PSUs ─────────────────────────────────────────────────────────
    "ntpc": {
        "name": "NTPC (National Thermal Power Corporation)",
        "url": "https://www.ntpc.co.in/jobs-ntpc"
    },
    # ── Aviation / Infrastructure ──────────────────────────────────────────
    "aai": {
        "name": "AAI (Airports Authority of India)",
        "url": "https://www.aai.aero/en/careers/recruitment"
    },
    # ── Indian Railways ────────────────────────────────────────────────────
    "rrb": {
        "name": "Indian Railways (RRB)",
        "url": "https://rrbapply.gov.in/#/auth/landing",
        "special": "playwright",  # React SPA — requires browser rendering
        "note": "rrbapply.gov.in is a React SPA with hash routing; static HTML returns nothing. Uses Playwright headless Chromium."
    },
    "rrb_static": {
        "name": "Indian Railways (RRB) — Static Board",
        "url": "https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,554",
        "note": "Static fallback page with older recruitment links"
    },
    "sameer": {
        "name": "SAMEER (R&D under MeitY)",
        "url": "https://recruit.sameer.gov.in/"
    },
    "ernet": {
        "name": "ERNET India (MeitY)",
        "url": "https://ernet.in/career",
        "special": "playwright"
    },
    "uidai": {
        "name": "UIDAI (Aadhaar)",
        "url": "https://uidai.gov.in/en/about-uidai/work-with-uidai.html"
    },
    "pgcil": {
        "name": "PGCIL (Power Grid Corporation of India)",
        "url": "https://www.powergrid.in/job-opportunities"
    },
    "iocl": {
        "name": "IOCL (Indian Oil Corporation)",
        "url": "https://iocl.com/Pages/Careers.aspx"
    },
    "bhel": {
        "name": "BHEL (Bharat Heavy Electricals)",
        "url": "https://www.bhel.com/recruitment"
    },
    "coal_india": {
        "name": "Coal India Limited",
        "url": "https://www.coalindia.in/career-cil/jobs-coal-india/"
    },
    "railtel": {
        "name": "RailTel Corporation of India",
        "url": "https://www.railtel.in"
    },
    "becil": {
        "name": "BECIL (Broadcast Engineering Consultants)",
        "url": "https://www.becil.com"
    },
    "sebi": {
        "name": "SEBI (Securities & Exchange Board)",
        "url": "https://www.sebi.gov.in"
    },
    "sidbi": {
        "name": "SIDBI (Small Industries Development Bank)",
        "url": "https://www.sidbi.in/en/careers"
    },
    "sjvn": {
        "name": "SJVN Limited",
        "url": "https://recruitment.sjvn.co.in/ErecruitLogin/Login.jsp",
        "special": "playwright"
    },
    "tcil": {
        "name": "TCIL (Telecommunications Consultants)",
        "url": "https://www.tcil.net.in"
    },
    "dic": {
        "name": "Digital India Corporation (DIC)",
        "url": "https://www.dic.gov.in/careers"
    },
    "npcil": {
        "name": "Nuclear Power Corporation of India (NPCIL)",
        "url": "https://www.npcilcareers.co.in"
    },
    "rites": {
        "name": "RITES Limited",
        "url": "https://www.rites.com/Career"
    },
    "dfccil": {
        "name": "Dedicated Freight Corridor Corporation (DFCCIL)",
        "url": "https://dfccil.com"
    },
    "scl": {
        "name": "Semi-Conductor Laboratory (SCL) Mohali",
        "url": "https://www.scl.gov.in/career.html"
    },
    "csir_4pi": {
        "name": "CSIR Fourth Paradigm Institute",
        "url": "https://csir4pi.res.in/index.php/en/careers/apply-for-a-position"
    },
    "igcar": {
        "name": "Indira Gandhi Centre for Atomic Research (IGCAR)",
        "url": "https://www.igcar.gov.in/recruitment.html"
    },
    "rrcat": {
        "name": "Raja Ramanna Centre for Advanced Technology (RRCAT)",
        "url": "https://www.rrcat.gov.in/hrd/Openings/Current_Openings.html"
    },
    "bpcl": {
        "name": "Bharat Petroleum Corporation Limited (BPCL)",
        "url": "https://www.bharatpetroleum.in/careers/job-openings"
    },
    "pfc": {
        "name": "Power Finance Corporation (PFC)",
        "url": "https://www.pfcindia.com/Home/VS/19"
    },
    "rec": {
        "name": "REC Limited",
        "url": "https://www.recl.co.in/recljobs/career.php"
    },
    "iti": {
        "name": "ITI Limited (Indian Telephone Industries)",
        "url": "https://www.itiltd.in/careers.php"
    },
    "cel": {
        "name": "Central Electronics Limited (CEL)",
        "url": "https://www.celindia.co.in/career-opportunity"
    },
    "nhpc": {
        "name": "NHPC Limited",
        "url": "http://www.nhpcindia.com/welcome/job"
    },
    "grid_india": {
        "name": "Grid Controller of India Limited (GRID-INDIA)",
        "url": "https://grid-india.in/careers/"
    },
    "hpcl": {
        "name": "Hindustan Petroleum Corporation Limited (HPCL)",
        "url": "https://www.hindustanpetroleum.com/careers"
    },
    "rbi": {
        "name": "Reserve Bank of India (RBI)",
        "url": "https://opportunities.rbi.org.in/scripts/vacancies.aspx"
    },
    "negd": {
        "name": "National e-Governance Division (NeGD)",
        "url": "https://negd.gov.in/careers/"
    },
    "nixi": {
        "name": "National Internet Exchange of India (NIXI)",
        "url": "https://nixi.in/career/"
    },
    "bisag_n": {
        "name": "BISAG-N (Bhaskaracharya National Institute for Space Applications)",
        "url": "https://www.bisag-n.gov.in"
    },
    "upsc": {
        "name": "UPSC (Union Public Service Commission)",
        "url": "https://www.upsc.gov.in/recruitment/recruitment-advertisements"
    },
    "ssc": {
        "name": "SSC (Staff Selection Commission)",
        "url": "https://ssc.gov.in/"
    },
    "irctc": {
        "name": "IRCTC (Indian Railway Catering and Tourism Corporation)",
        "url": "https://www.irctc.com/recruitment.php"
    },
    "concor": {
        "name": "CONCOR (Container Corporation of India)",
        "url": "https://www.concorindia.co.in/careers_rect.asp",
        "special": "playwright"
    },
    "eil": {
        "name": "EIL (Engineers India Limited)",
        "url": "https://www.engineersindia.com/careers/"
    },
    "mpsc": {
        "name": "MPSC (Maharashtra Public Service Commission)",
        "url": "https://mpsc.gov.in/"
    },
    "gpsc": {
        "name": "GPSC (Gujarat Public Service Commission)",
        "url": "https://gpsc.gujarat.gov.in/"
    },
    "keralapsc": {
        "name": "Kerala Public Service Commission",
        "url": "https://www.keralapsc.gov.in/"
    },
    "rpsc": {
        "name": "RPSC (Rajasthan Public Service Commission)",
        "url": "https://rpsc.rajasthan.gov.in/"
    },
    "tnpsc": {
        "name": "TNPSC (Tamil Nadu Public Service Commission)",
        "url": "https://www.tnpsc.gov.in/"
    },
    "opsc": {
        "name": "OPSC (Odisha Public Service Commission)",
        "url": "https://www.opsc.gov.in/Public/OPSC/Default.aspx"
    },
    "wbpsc": {
        "name": "WBPSC (West Bengal Public Service Commission)",
        "url": "https://psc.wb.gov.in/"
    },
    "appsc": {
        "name": "APPSC (Andhra Pradesh Public Service Commission)",
        "url": "https://psc.ap.gov.in/"
    },
    "mppsc": {
        "name": "MPPSC (Madhya Pradesh Public Service Commission)",
        "url": "https://mppsc.mp.gov.in/"
    },
    "hpsc": {
        "name": "HPSC (Haryana Public Service Commission)",
        "url": "https://hpsc.gov.in/en-us/"
    },
    "ppsc": {
        "name": "PPSC (Punjab Public Service Commission)",
        "url": "https://ppsc.gov.in/"
    },
    "ukpsc": {
        "name": "UKPSC (Uttarakhand Public Service Commission)",
        "url": "https://psc.uk.gov.in/"
    },
    "cgpsc": {
        "name": "CGPSC (Chhattisgarh Public Service Commission)",
        "url": "https://psc.cg.gov.in/"
    },
    "jpsc": {
        "name": "JPSC (Jharkhand Public Service Commission)",
        "url": "https://www.jpsc.gov.in/"
    },
    "ibps": {
        "name": "IBPS (Institute of Banking Personnel Selection)",
        "url": "https://www.ibps.in/"
    },
    "sbi": {
        "name": "SBI Careers (State Bank of India)",
        "url": "https://sbi.co.in/web/careers/current-openings"
    },
    "nabard": {
        "name": "NABARD (National Bank for Agriculture and Rural Development)",
        "url": "https://www.nabard.org/"
    },
    "nhb": {
        "name": "NHB (National Housing Bank)",
        "url": "https://www.nhb.org.in/careers-with-nhb-archives/"
    },
    "gail": {
        "name": "GAIL (India) Limited",
        "url": "https://gailonline.com/"
    },
    "oil": {
        "name": "OIL (Oil India Limited)",
        "url": "https://www.oil-india.com/advertisement-list"
    },
    "nalco": {
        "name": "NALCO (National Aluminium Company)",
        "url": "https://nalcoindia.com/career/"
    },
    "mdl": {
        "name": "MDL (Mazagon Dock Shipbuilders)",
        "url": "https://mazagondock.in/"
    },
    "dsssb": {
        "name": "DSSSB (Delhi Subordinate Services Selection Board)",
        "url": "https://dsssb.delhi.gov.in/"
    },
    "rsmssb": {
        "name": "RSMSSB (Rajasthan Staff Selection Board)",
        "url": "https://rsmssb.rajasthan.gov.in/"
    },
    "hssc": {
        "name": "HSSC (Haryana Staff Selection Commission)",
        "url": "https://www.hssc.gov.in/"
    },
    "bank_bankofindia": {
        "name": "Bank of India",
        "url": "https://www.bankofindia.co.in/Careers",
        "special": "playwright"
    },
    "bank_pgb": {
        "name": "Paschim Banga Gramin Bank",
        "url": "https://www.pgb.org.in/recruitment.php",
        "special": "playwright"
    },
    "iitgn": {
        "name": "IIT Gandhinagar",
        "url": "https://iitgn.ac.in/careers/staff",
        "special": "playwright"
    },
    "jh_education": {
        "name": "JH Education Department",
        "url": "https://education.jharkhand.gov.in/",
        "special": "playwright"
    },
    "tn_police": {
        "name": "TN Police Department",
        "url": "https://police.tn.gov.in/",
        "special": "playwright"
    },
    "police_tn": {
        "name": "TN Police Recruitment Portal",
        "url": "https://www.tnusrb.tn.gov.in/",
        "special": "playwright"
    },
    "vtu": {
        "name": "VTU (Visvesvaraya Technological University)",
        "url": "https://vtu.ac.in/en/category/administration-careers/",
        "special": "playwright"
    }
}

# Orgs to run in the main GitHub Actions workflow
MAIN_ORGS = [
    "cdac", "nielit", "stpi", "nic", "cdot", "certin",
    "drdo", "bel", "barc", "isro", "hal", "ecil", "cris",
    "bsnl", "employment_news", "ncs",
    "ongc", "sail", "ntpc", "aai",
    "sameer", "ernet", "uidai", "pgcil", "iocl", "bhel",
    "coal_india", "railtel", "becil", "sebi", "sidbi", "sjvn",
    "tcil", "dic", "npcil", "rites", "dfccil",
    "scl", "csir_4pi", "igcar", "rrcat", "bpcl", "pfc", "rec", "iti",
    "cel", "nhpc", "grid_india", "hpcl", "rbi", "negd", "nixi", "bisag_n",
    "upsc", "ssc", "irctc", "concor", "eil", "mpsc", "gpsc", "keralapsc", "rpsc",
    "tnpsc", "opsc", "wbpsc", "appsc", "mppsc", "hpsc", "ppsc", "ukpsc", "cgpsc", "jpsc",
    "ibps", "sbi", "nabard", "nhb", "gail", "oil", "nalco", "mdl", "dsssb", "rsmssb", "hssc"
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
    "scl": {
        "name": "Semi-Conductor Laboratory (SCL) Mohali",
        "homepages": ["https://www.scl.gov.in/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"job"],
    },
    "csir_4pi": {
        "name": "CSIR Fourth Paradigm Institute",
        "homepages": ["https://csir4pi.res.in/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"position", r"job"],
    },
    "igcar": {
        "name": "Indira Gandhi Centre for Atomic Research (IGCAR)",
        "homepages": ["https://www.igcar.gov.in/"],
        "patterns": [r"recruit", r"vacanc", r"job", r"career"],
    },
    "rrcat": {
        "name": "Raja Ramanna Centre for Advanced Technology (RRCAT)",
        "homepages": ["https://www.rrcat.gov.in/"],
        "patterns": [r"opening", r"recruit", r"vacanc", r"career", r"hrd"],
    },
    "bpcl": {
        "name": "Bharat Petroleum Corporation Limited (BPCL)",
        "homepages": ["https://www.bharatpetroleum.in/"],
        "patterns": [r"career", r"job", r"recruit", r"opening", r"vacanc"],
    },
    "pfc": {
        "name": "Power Finance Corporation (PFC)",
        "homepages": ["https://www.pfcindia.com/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"job", r"opening"],
    },
    "rec": {
        "name": "REC Limited",
        "homepages": ["https://www.recl.co.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "iti": {
        "name": "ITI Limited (Indian Telephone Industries)",
        "homepages": ["https://www.itiltd.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "cel": {
        "name": "Central Electronics Limited (CEL)",
        "homepages": ["https://www.celindia.co.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "nhpc": {
        "name": "NHPC Limited",
        "homepages": ["http://www.nhpcindia.com/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "grid_india": {
        "name": "Grid Controller of India Limited (GRID-INDIA)",
        "homepages": ["https://grid-india.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "hpcl": {
        "name": "Hindustan Petroleum Corporation Limited (HPCL)",
        "homepages": ["https://www.hindustanpetroleum.com/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "rbi": {
        "name": "Reserve Bank of India (RBI)",
        "homepages": ["https://opportunities.rbi.org.in/"],
        "patterns": [r"vacancy", r"recruit", r"job", r"opportunity", r"career"],
    },
    "negd": {
        "name": "National e-Governance Division (NeGD)",
        "homepages": ["https://negd.gov.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "nixi": {
        "name": "National Internet Exchange of India (NIXI)",
        "homepages": ["https://nixi.in/"],
        "patterns": [r"career", r"job", r"recruit", r"vacanc", r"opening"],
    },
    "bisag_n": {
        "name": "BISAG-N (Bhaskaracharya National Institute for Space Applications)",
        "homepages": ["https://www.bisag-n.gov.in/"],
        "patterns": [r"notice", r"recruit", r"vacanc", r"career", r"job"],
    },
    "upsc": {
        "name": "UPSC (Union Public Service Commission)",
        "homepages": ["https://www.upsc.gov.in/"],
        "patterns": [r"recruit", r"vacanc", r"exam", r"advertisement"],
    },
    "ssc": {
        "name": "SSC (Staff Selection Commission)",
        "homepages": ["https://ssc.gov.in/"],
        "patterns": [r"notice", r"exam", r"recruit", r"vacanc"],
    },
    "irctc": {
        "name": "IRCTC (Indian Railway Catering and Tourism Corporation)",
        "homepages": ["https://www.irctc.com/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"opening", r"job"],
    },
    "concor": {
        "name": "CONCOR (Container Corporation of India)",
        "homepages": ["https://www.concorindia.co.in/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"opening", r"hr"],
    },
    "eil": {
        "name": "EIL (Engineers India Limited)",
        "homepages": ["https://www.engineersindia.com/"],
        "patterns": [r"career", r"recruit", r"vacanc", r"opening", r"job"],
    },
    "mpsc": {
        "name": "MPSC (Maharashtra Public Service Commission)",
        "homepages": ["https://mpsc.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "gpsc": {
        "name": "GPSC (Gujarat Public Service Commission)",
        "homepages": ["https://gpsc.gujarat.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "keralapsc": {
        "name": "Kerala Public Service Commission",
        "homepages": ["https://www.keralapsc.gov.in/"],
        "patterns": [r"notification", r"recruit", r"vacanc", r"job"],
    },
    "rpsc": {
        "name": "RPSC (Rajasthan Public Service Commission)",
        "homepages": ["https://rpsc.rajasthan.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "tnpsc": {
        "name": "TNPSC (Tamil Nadu Public Service Commission)",
        "homepages": ["https://www.tnpsc.gov.in/"],
        "patterns": [r"notification", r"recruit", r"vacanc", r"job", r"announcement"],
    },
    "opsc": {
        "name": "OPSC (Odisha Public Service Commission)",
        "homepages": ["https://www.opsc.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "wbpsc": {
        "name": "WBPSC (West Bengal Public Service Commission)",
        "homepages": ["https://psc.wb.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "appsc": {
        "name": "APPSC (Andhra Pradesh Public Service Commission)",
        "homepages": ["https://psc.ap.gov.in/"],
        "patterns": [r"notification", r"recruit", r"vacanc", r"job"],
    },
    "mppsc": {
        "name": "MPPSC (Madhya Pradesh Public Service Commission)",
        "homepages": ["https://mppsc.mp.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "hpsc": {
        "name": "HPSC (Haryana Public Service Commission)",
        "homepages": ["https://hpsc.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "ppsc": {
        "name": "PPSC (Punjab Public Service Commission)",
        "homepages": ["https://ppsc.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "ukpsc": {
        "name": "UKPSC (Uttarakhand Public Service Commission)",
        "homepages": ["https://psc.uk.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "cgpsc": {
        "name": "CGPSC (Chhattisgarh Public Service Commission)",
        "homepages": ["https://psc.cg.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "jpsc": {
        "name": "JPSC (Jharkhand Public Service Commission)",
        "homepages": ["https://www.jpsc.gov.in/"],
        "patterns": [r"advertisement", r"notification", r"recruit", r"vacanc"],
    },
    "ibps": {
        "name": "IBPS (Institute of Banking Personnel Selection)",
        "homepages": ["https://www.ibps.in/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "sbi": {
        "name": "SBI Careers (State Bank of India)",
        "homepages": ["https://sbi.co.in/web/careers/current-openings"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"opening", r"career"],
    },
    "nabard": {
        "name": "NABARD (National Bank for Agriculture and Rural Development)",
        "homepages": ["https://www.nabard.org/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "nhb": {
        "name": "NHB (National Housing Bank)",
        "homepages": ["https://www.nhb.org.in/careers-with-nhb-archives/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "gail": {
        "name": "GAIL (India) Limited",
        "homepages": ["https://gailonline.com/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "oil": {
        "name": "OIL (Oil India Limited)",
        "homepages": ["https://www.oil-india.com/advertisement-list"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "nalco": {
        "name": "NALCO (National Aluminium Company)",
        "homepages": ["https://nalcoindia.com/career/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "mdl": {
        "name": "MDL (Mazagon Dock Shipbuilders)",
        "homepages": ["https://mazagondock.in/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"career"],
    },
    "dsssb": {
        "name": "DSSSB (Delhi Subordinate Services Selection Board)",
        "homepages": ["https://dsssb.delhi.gov.in/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"vacancy"],
    },
    "rsmssb": {
        "name": "RSMSSB (Rajasthan Staff Selection Board)",
        "homepages": ["https://rsmssb.rajasthan.gov.in/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"vacancy"],
    },
    "hssc": {
        "name": "HSSC (Haryana Staff Selection Commission)",
        "homepages": ["https://www.hssc.gov.in/"],
        "patterns": [r"recruit", r"advertisement", r"notification", r"vacancy"],
    },
}
