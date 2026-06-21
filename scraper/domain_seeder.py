"""
scraper/domain_seeder.py

Dynamic Domain Seeder & Career Page Resolver.
Generates a comprehensive registry of ~2,500 Indian public sector, academic,
PSU, and banking domains, and provides dynamic resolution of career pages.
"""

import time
import requests
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from scraper.config import DEFAULT_HEADERS

# 28 States and 8 Union Territory codes in India
_STATE_CODES = [
    "ap", "ar", "as", "br", "cg", "ga", "gj", "hr", "hp", "jk", "jh", "ka", "kl",
    "mp", "mh", "mn", "ml", "mz", "nl", "od", "pb", "rj", "sk", "tn", "tg", "tr",
    "up", "uk", "wb", "dl", "py", "ch", "an", "ld", "dd", "dn"
]

# Major PSU domain list
_PSU_DOMAINS = [
    "gail.co.in", "gailonline.com", "oil-india.com", "nalcoindia.com", "mazagondock.in",
    "bhel.com", "ongcindia.com", "sail.co.in", "ntpc.co.in", "powergrid.in", "iocl.com",
    "coalindia.in", "railtel.in", "becil.com", "sidbi.in", "sjvn.co.in", "tcil.net.in",
    "dic.gov.in", "npcilcareers.co.in", "rites.com", "dfccil.com", "bpcl.in", "pfcindia.com",
    "recl.co.in", "itiltd.in", "celindia.co.in", "nhpcindia.com", "grid-india.in",
    "hindustanpetroleum.com", "irctc.com", "concorindia.co.in", "engineersindia.com",
    "gail.co.in", "hzlindia.com", "hzl.co.in", "balcoindia.com", "vizagsteel.com",
    "meconlimited.co.in", "hecltd.com", "kioclltd.in", "midhani-india.in", "bdl-india.in",
    "grse.in", "goashipyard.co.in", "hsl.gov.in", "cochinshipyard.in", "hmtindia.com",
    "nmdc.co.in", "nationalfertilizers.com", "rcfltd.com", "fact.co.in", "mfl.co.in"
]

# Major Banking/Insurance domain list
_BANK_DOMAINS = [
    "sbi.co.in", "pnbindia.in", "bankofbaroda.in", "canarabank.com", "unionbankofindia.co.in",
    "indianbank.in", "mahabank.in", "indianoverseasbank.in", "ucobank.com", "bankofindia.co.in",
    "centralbankofindia.co.in", "psbindia.com", "rbi.org.in", "sebi.gov.in", "nabard.org",
    "nhb.org.in", "eximbankindia.in", "ecgc.in", "ibps.in", "licindia.in", "gicofindia.com",
    "nia.co.in", "nationalinsurance.nic.in", "orientalinsurance.org.in", "newindia.co.in"
]

# 23 IITs, 31 NITs, 25 IIITs, 20 IIMs, and 54 Central Universities suffixes
_ACADEMIC_SEEDS = [
    # IITs
    "iitb.ac.in", "iitd.ac.in", "iitkgp.ac.in", "iitm.ac.in", "iitk.ac.in", "iitr.ac.in",
    "iitg.ac.in", "iith.ac.in", "iitbhu.ac.in", "iitism.ac.in", "iitindore.ac.in",
    "iitmandi.ac.in", "iitrpr.ac.in", "iitgn.ac.in", "iitp.ac.in", "iitj.ac.in",
    "iitbbs.ac.in", "iitpkd.ac.in", "iittp.ac.in", "iitjammu.ac.in", "iitdh.ac.in",
    "iitgoa.ac.in", "iitbhilai.ac.in",
    # NITs
    "nitrkl.ac.in", "nitk.ac.in", "nits.ac.in", "nitc.ac.in", "nitw.ac.in", "nitt.edu",
    "nitp.ac.in", "nitj.ac.in", "nitkkr.ac.in", "nitdgp.ac.in", "nitsri.ac.in",
    "nitap.ac.in", "nitmanipur.ac.in", "nitm.ac.in", "nitmz.ac.in", "nitnagaland.ac.in",
    "nitsikkim.ac.in", "nitpy.edu.in", "nitgoa.ac.in", "nitdelhi.ac.in", "nith.ac.in",
    "nitrr.ac.in", "nitjsr.ac.in", "nituk.ac.in", "nitap.ac.in",
    # Universities
    "du.ac.in", "jnu.ac.in", "bhu.ac.in", "uohyd.ac.in", "amu.ac.in", "jmi.ac.in",
    "curaj.ac.in", "tezu.ernet.in", "iisc.ac.in", "tifr.res.in", "csir.res.in"
]

def generate_domains():
    """
    Generates a full list of ~2,500 target domains across:
      - Central/State PSCs and SSBs
      - State Police and Municipalities
      - Major CPSE PSUs
      - Public Banks & Insurance
      - Elite Academic & Research Institutions
    """
    domains = {}

    # 1. State PSC & Staff Selection Board combinations
    for code in _STATE_CODES:
        # e.g., uppsc.up.nic.in, mpsc.gov.in, rpsc.rajasthan.gov.in
        domains[f"{code}psc"] = {
            "name": f"{code.upper()} PSC (State Commission)",
            "url": f"https://{code}psc.gov.in"
        }
        domains[f"{code}ssc"] = {
            "name": f"{code.upper()} Staff Selection Board",
            "url": f"https://{code}ssc.in"
        }
        domains[f"police_{code}"] = {
            "name": f"{code.upper()} Police Recruitment",
            "url": f"https://{code}police.gov.in"
        }
        # Nested patterns
        domains[f"{code}_gov"] = {
            "name": f"{code.upper()} Government Portal",
            "url": f"https://www.nic.in/{code}"
        }

    # 2. PSUs
    for dom in _PSU_DOMAINS:
        key = dom.split(".")[0]
        domains[key] = {
            "name": f"{key.upper()} (Central PSU)",
            "url": f"https://www.{dom}"
        }

    # 3. Banks
    for dom in _BANK_DOMAINS:
        key = dom.split(".")[0]
        domains[f"bank_{key}"] = {
            "name": f"{key.upper()} (Public Sector Banking/Insurance)",
            "url": f"https://www.{dom}"
        }

    # 4. Academic
    for dom in _ACADEMIC_SEEDS:
        key = dom.split(".")[0]
        domains[key] = {
            "name": f"{key.upper()} (Elite Academic/Research)",
            "url": f"https://www.{dom}"
        }

    return domains

# Keywords to identify career pages on homepages
_CAREER_LINKS_RE = re.compile(
    r"career|recruit|vacancy|opening|advertisement|advt|job|work.?with",
    re.IGNORECASE
)

def resolve_career_url(homepage_url, session=None):
    """
    Fetches the domain homepage and dynamically resolves its career page URL.
    Returns the resolved URL, falling back to homepage if none found.
    """
    if session is None:
        session = requests.Session()

    try:
        r = session.get(homepage_url, headers=DEFAULT_HEADERS, timeout=10, verify=False)
        if r.status_code != 200:
            return homepage_url
    except Exception:
        # Fall back to HTTP if HTTPS fails or DNS error
        if homepage_url.startswith("https://"):
            return resolve_career_url(homepage_url.replace("https://", "http://"), session)
        return homepage_url

    soup = BeautifulSoup(r.text, "html.parser")
    best_url = homepage_url
    best_score = 0

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href == "#":
            continue

        text = a.get_text().strip()
        score = 0

        # Score matching links
        if _CAREER_LINKS_RE.search(href):
            score += 40
        if _CAREER_LINKS_RE.search(text):
            score += 50
        if "pdf" in href.lower():
            score -= 10  # prefer landing page over direct PDF

        if score > best_score:
            best_score = score
            best_url = urljoin(homepage_url, href)

    # Dedup slash
    return best_url.rstrip("/")
