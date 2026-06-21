"""
scraper/domain_seeder.py

Dynamic Domain Seeder & Career Page Resolver.
Generates a comprehensive registry of 2,300+ Indian public sector, academic,
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

# 30 key state government departments/directorates
_DEPARTMENTS = [
    "education", "health", "pwd", "forest", "agriculture", "revenue", "transport", 
    "wrd", "sports", "police", "finance", "coop", "excise", "tourism", "socialwelfare", 
    "tribal", "urban", "rural", "industries", "planning", "animalhusbandry", "fisheries", 
    "labour", "information", "law", "energy", "science", "technicaleducation", "highereducation", "home",
    "food", "welfare", "housing", "water", "disaster"
]

# Comprehensive list of ~430 districts in India
_DISTRICTS = [
    # UP
    "lucknow", "kanpur", "varanasi", "allahabad", "agra", "meerut", "ghaziabad", "bareilly", "aligarh", "moradabad", 
    "saharanpur", "gorakhpur", "jhansi", "muzaffarnagar", "mathura", "ayodhya", "mirzapur", "firozabad", "raebareli", 
    "sitapur", "hardoi", "lakhimpur", "barabanki", "unnao", "sultanpur", "amethi", "bahraich", "shravasti", "balrampur", 
    "gonda", "basti", "amroha", "bijnor", "rampur", "sambhal", "pilibhit", "shahjahanpur", "kanpurdehat", "farrukhabad", 
    "kannauj", "etawah", "auraiya", "jalaun", "hamirpur", "mahoba", "banda", "chitrakoot", "fatehpur", "pratapgarh", 
    "kaushambi", "jaunpur", "ghazipur", "chandauli", "ballia", "mau", "deoria", "kushinagar", "maharajganj", "bhadohi", 
    "sonbhadra", "lalitpur", "hapur", "shamli", "baghpat", "bulandshahr", "kasganj", "hathras", "etah", "mainpuri", "azamgarh",
    # Maharashtra
    "mumbai", "thane", "pune", "nagpur", "nashik", "aurangabad", "solapur", "amravati", "kolhapur", "sangli", "satara", 
    "jalgaon", "dhule", "chandrapur", "latur", "akola", "parbhani", "buldhana", "yavatmal", "wardha", "bhandara", "gondia", 
    "gadchiroli", "hingoli", "osmanabad", "beed", "nandurbar", "ratnagiri", "sindhudurg", "raigad", "palghar", "nanded", 
    "jalna", "washim",
    # Bihar
    "patna", "gaya", "muzaffarpur", "bhagalpur", "darbhanga", "purnia", "arrah", "begusarai", "katihar", "munger", 
    "chhapra", "saharsa", "sasaram", "hajipur", "siwan", "motihari", "bettiah", "jehanabad", "nawada", "nalanda", 
    "buxar", "rohtas", "bhojpur", "vaishali", "saran", "samastipur", "madhubani", "sitamarhi", "sheohar", "araria", 
    "kishanganj", "supaul", "madhepura", "khagaria", "jamui", "lakhisarai", "sheikhpura", "banka", "arwal",
    # Gujarat
    "ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "jamnagar", "junagadh", "gandhinagar", "nadiad", "morbi", 
    "surendranagar", "gandhidham", "veraval", "navsari", "bharuch", "anand", "porbandar", "godhra", "patan", "dahod", 
    "amreli", "valsad", "vapi", "mehsana", "palanpur", "vyara", "ahwa", "himatnagar", "modasa", "chhotaudepur", "botad",
    # Rajasthan
    "jaipur", "jodhpur", "kota", "bikaner", "ajmer", "udaipur", "bhilwara", "alwar", "sikar", "sriganganagar", "pali", 
    "hanumangarh", "tonk", "baran", "bundi", "churu", "dholpur", "jaisalmer", "jalore", "jhalawar", "jhunjhunu", "karauli", 
    "nagaur", "pratapgarh", "rajsamand", "sawaimadhopur", "sirohi",
    # MP
    "bhopal", "indore", "jabalpur", "gwalior", "ujjain", "sagar", "dewas", "satna", "ratlam", "rewa", "murwara", "singrauli", 
    "burhanpur", "khandwa", "bhind", "chhindwara", "guna", "shivpuri", "vidisha", "chhatarpur", "damoh", "mandsaur", 
    "khargone", "neemuch", "hoshangabad", "itarsi", "sehore", "betul", "seoni", "balaghat", "mandla", "dindori", "shahdol", 
    "anuppur", "umaria", "sidhi", "jhabua", "alirajpur", "dhar", "barwani", "shajapur", "agar-malwa", "rajgarh", "sheopur", 
    "morena", "datia", "tikamgarh", "niwari", "panna", "katni", "narsinghpur", "harda", "raisen",
    # Andhra
    "visakhapatnam", "vijayawada", "guntur", "nellore", "kurnool", "kakinada", "kadapa", "tirupati", "anantapur", 
    "eluru", "ongole", "nandyal", "machilipatnam", "adoni", "tenali", "proddatur", "chittoor", "hindupur", "bhimavaram", 
    "madanapalle", "guntakal", "srikakulam", "vizianagaram", "amalapuram", "parvathipuram",
    # Telangana
    "hyderabad", "warangal", "nizamabad", "karimnagar", "khammam", "ramagundam", "mahabubnagar", "nalgonda", "adilabad", 
    "suryapet", "miryalaguda", "jagtial", "mancherial", "kothagudem", "siricilla", "kamareddy", "siddipet", "wanaparthy", 
    "gadwal", "narayanpet", "bhupalpally", "mulugu",
    # Tamil Nadu
    "chennai", "coimbatore", "madurai", "tiruchirappalli", "tiruppur", "salem", "erode", "vellore", "thoothukudi", 
    "dindigul", "thanjavur", "ranipet", "sivakasi", "karur", "udagamandalam", "nagercoil", "kanchipuram", "tiruvannamalai", 
    "cuddalore", "dharmapuri", "krishnagiri", "namakkal", "nilgiris", "perambalur", "pudukkottai", "ramanathapuram", 
    "sivaganga", "theni", "thiruvallur", "thiruvarur", "tirunelveli", "tenkasi", "tirupathur", "villupuram", "virudhunagar",
    # Karnataka
    "bengaluru", "mysuru", "hubballi", "dharwad", "mangaluru", "belagavi", "kalaburagi", "davanagere", "ballari", 
    "vijayapura", "shivamogga", "tumakuru", "raichur", "bidar", "hospet", "hassan", "gadag", "bagalkot", "kolar", 
    "mandya", "chikmagalur", "chitradurga", "haveri", "yadgir", "ramanagara", "chamarajanagar", "udupi", "kodagu", 
    "karwar", "koppal", "chikkaballapur",
    # Kerala
    "thiruvananthapuram", "kochi", "kozhikode", "kollam", "thrissur", "alappuzha", "palakkad", "kannur", "kottayam", 
    "kasaragod", "pathanamthitta", "idukki", "wayanad", "malappuram",
    # West Bengal
    "kolkata", "howrah", "darjeeling", "kalimpong", "jalpaiguri", "alipurduar", "coochbehar", "malda", "murshidabad", 
    "nadia", "purulia", "bankura", "birbhum", "hooghly", "midnapore", "kharagpur", "asansol", "durgapur", "siliguri", 
    "bardhaman", "jhargram", "purvamedinipur", "paschimmedinipur",
    # Punjab
    "ludhiana", "amritsar", "jalandhar", "patiala", "bathinda", "mohali", "pathankot", "hoshiarpur", "batala", "moga", 
    "phagwara", "firozpur", "muktsar", "barnala", "faridkot", "gurdaspur", "kapurthala", "mansa", "rupnagar", "sangrur", 
    "tarntaran", "fazilka", "malerkotla",
    # Haryana
    "gurugram", "faridabad", "panipat", "ambala", "yamunanagar", "rohtak", "hisar", "karnal", "sonipat", "panchkula", 
    "sirsa", "bhiwani", "bahadurgarh", "jind", "kaithal", "rewari", "palwal", "nuh", "fatehabad", "mahendragarh", 
    "charkhidadri", "jhajjar",
    # Odisha
    "khordha", "cuttack", "ganjam", "bhadrak", "balasore", "mayurbhanj", "puri", "sambalpur", "rourkela", "sundargarh", 
    "bolangir", "koraput", "rayagada", "kalahandi", "nawarangpur", "malkangiri", "kendrapada", "jajpur", "jagatsinghpur", 
    "dhenkanal", "angul", "keonjhar", "nayagarh", "boudh", "subarnapur", "bargarh", "jharsuguda", "deogarh", "nuapada", "gajapati",
    # J&K and North-East
    "anantnag", "bandipora", "baramulla", "budgam", "doda", "ganderbal", "kathua", "kishtwar", "kulgam", "kupwara", 
    "poonch", "pulwama", "ramban", "reasi", "samba", "shopian", "udhampur", "northgoa", "southgoa", "dhalai", "gomati", 
    "khowai", "northtripura", "sepahijala", "southtripura", "unakoti", "westtripura", "bishnupur", "chandel", "churachandpur", 
    "imphaleast", "imphalwest", "jiribam", "kakching", "kamjong", "kangpokpi", "noney", "pherzawl", "senapati", "tamenglong", 
    "tengnoupal", "thoubal", "ukhrul", "eastgarohills", "eastjaintiahills", "eastkhasihills", "northgarohills", "ribhoi", 
    "southgarohills", "southwestgarohills", "southwestkhasihills", "westgarohills", "westjaintiahills", "westkhasihills", 
    "aizawl", "champhai", "kolasib", "lawngtlai", "lunglei", "mamit", "saiha", "serchhip", "hnahthial", "khawzawl", "saitual",
    "chumuoukedima", "dimapur", "kiphire", "kohima", "longleng", "mokokchung", "mon", "niuland", "noklak", "peren", "phek", 
    "shamator", "tseminyu", "tuensang", "wokha", "zunheboto", "gangtok", "gyalshing", "mangan", "namchi", "soreng", "pakyong",
    "tawang", "westkameng", "eastkameng", "papumpare", "kurungkumey", "kraadaadi", "lowersubansiri", "uppersubansiri", 
    "westsiang", "eastsiang", "siang", "uppersiang", "lowersiang", "lowerdibangvalley", "dibangvalley", "anjaw", "lohit", 
    "namsai", "changlang", "tirap", "longding", "kamle", "leparada"
]

# Municipal Corporations / Urban Local Bodies
_MUNICIPALITIES = [
    "mcgm", "pmc", "nmmc", "kdmc", "mbmc", "vvcmc", "ulhasnagar", "bnmc", "smc_gj", "amc_gj", 
    "vmc_gj", "rmc_gj", "jmc_rj", "jo_mc", "kmc_wb", "hmc_wb", "mcshimla", "mcg", "mcf", "mcc_ka", 
    "bmrda", "hmrda", "cmda", "ghmc", "gvmc", "vuda", "vada", "kda", "jda", "uda", "ada", "gda", 
    "udaipurmc", "kotamc", "bikanermc", "ajmermc", "bhilwaramc", "alwarmc", "sikarmc", "pnbmc", 
    "dharmc", "gwalior-mc", "bhopal-mc", "indore-mc", "jabalpur-mc", "sagar-mc", "satna-mc", "rewa-mc"
]

# Central PSUs
_PSU_DOMAINS = [
    "gail.co.in", "gailonline.com", "oil-india.com", "nalcoindia.com", "mazagondock.in",
    "bhel.com", "ongcindia.com", "sail.co.in", "ntpc.co.in", "powergrid.in", "iocl.com",
    "coalindia.in", "railtel.in", "becil.com", "sidbi.in", "sjvn.co.in", "tcil.net.in",
    "dic.gov.in", "npcilcareers.co.in", "rites.com", "dfccil.com", "bpcl.in", "pfcindia.com",
    "recl.co.in", "itiltd.in", "celindia.co.in", "nhpcindia.com", "grid-india.in",
    "hindustanpetroleum.com", "irctc.com", "concorindia.co.in", "engineersindia.com",
    "hzlindia.com", "hzl.co.in", "balcoindia.com", "vizagsteel.com",
    "meconlimited.co.in", "hecltd.com", "kioclltd.in", "midhani-india.in", "bdl-india.in",
    "grse.in", "goashipyard.co.in", "hsl.gov.in", "cochinshipyard.in", "hmtindia.com",
    "nmdc.co.in", "nationalfertilizers.com", "rcfltd.com", "fact.co.in", "mfl.co.in"
]

# Public Banks, Insurance companies, and Regional Rural Banks
_BANK_DOMAINS = [
    "sbi.co.in", "pnbindia.in", "bankofbaroda.in", "canarabank.com", "unionbankofindia.co.in",
    "indianbank.in", "mahabank.in", "indianoverseasbank.in", "ucobank.com", "bankofindia.co.in",
    "centralbankofindia.co.in", "psbindia.com", "rbi.org.in", "sebi.gov.in", "nabard.org",
    "nhb.org.in", "eximbankindia.in", "ecgc.in", "ibps.in", "licindia.in", "gicofindia.com",
    "nia.co.in", "nationalinsurance.nic.in", "orientalinsurance.org.in", "newindia.co.in",
    # Regional Rural Banks (RRBs)
    "apgbank.in", "apgvbank.in", "agb.co.in", "aryavartbank-rrb.com", "bgvb.in", "brkgb.com",
    "cgrgb.co.in", "karnatakagraminbank.com", "kvgbank.in", "keralagbank.sg", "mgbgrameen.in",
    "mpgb.co.in", "meghalayagraminbank.co.in", "mizoramruralbank.co.in", "nagalandruralbank.co.in",
    "ogb.co.in", "pgb.org.in", "sgbrrb.org", "utkalgrameenbank.co.in", "ubgb.in", "pbgb.org.in",
    "prathamaupbank.com", "supgrrb.com"
]

# Academic & Research Suffixes (IITs, NITs, IIITs, Universities)
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
    "nitmanipur.ac.in", "nitm.ac.in", "nitmz.ac.in", "nitnagaland.ac.in",
    "nitsikkim.ac.in", "nitpy.edu.in", "nitgoa.ac.in", "nitdelhi.ac.in", "nith.ac.in",
    "nitrr.ac.in", "nitjsr.ac.in", "nituk.ac.in",
    # IIITs
    "iiitd.ac.in", "iiitb.ac.in", "iiitm.ac.in", "iiitg.ac.in", "iiith.ac.in", "iiitk.ac.in",
    "iiitl.ac.in", "iiitp.ac.in", "iiits.ac.in", "iiitvadodara.ac.in", "iiitkottayam.ac.in",
    "iiitdharwad.ac.in", "iiitkalyani.ac.in", "iiituna.ac.in", "iiitranchi.ac.in",
    "iiitnagpur.ac.in", "iiitbhagalpur.ac.in", "iiitbhopal.ac.in", "iiitsurat.ac.in",
    # Universities
    "du.ac.in", "jnu.ac.in", "bhu.ac.in", "uohyd.ac.in", "amu.ac.in", "jmi.ac.in",
    "curaj.ac.in", "tezu.ernet.in", "iisc.ac.in", "tifr.res.in", "csir.res.in",
    "manipal.edu", "bits-pilani.ac.in", "annauniv.edu", "vtu.ac.in", "jntu.ac.in",
    "caluniv.ac.in", "mu.ac.in", "unom.ac.in", "unipune.ac.in"
]

# Key Ministries, Central Agencies, and Research Labs
_MINISTRIES_LABS = [
    "meity.gov.in", "education.gov.in", "defence.gov.in", "finmin.nic.in", "mha.gov.in",
    "railways.gov.in", "isro.gov.in", "drdo.gov.in", "barc.gov.in", "dae.gov.in",
    "dst.gov.in", "dbtindia.gov.in", "csir.res.in", "icmr.gov.in", "icar.org.in",
    "sac.gov.in", "vssc.gov.in", "ursc.gov.in", "sdsc.gov.in", "iprc.gov.in",
    "iist.ac.in", "nrsc.gov.in", "iirs.gov.in", "prl.res.in", "narl.gov.in",
    "neist.res.in", "iict.res.in", "ncl-india.org", "nplindia.org", "ccmb.res.in",
    "cdri.res.in", "iiim.res.in", "ihbt.res.in", "imtech.res.in", "nio.org",
    "ngri.res.in", "neeri.res.in", "cgcri.res.in", "cecri.res.in", "clri.org"
]

def generate_domains():
    """
    Generates a registry of 2,300+ target domains across:
      - Central/State PSCs and SSBs (180+ domains)
      - State Department portals (1,080+ domains)
      - District NIC portals (430+ domains)
      - Municipal Corporations (50+ domains)
      - Central and State PSUs (160+ domains)
      - Public Sector Banks & Regional Rural Banks (50+ domains)
      - Elite Academic & Research Institutions (80+ domains)
      - Ministries & Research Labs (40+ domains)
    """
    domains = {}

    # 1. State level portals (PSC, SSB, Police, Gov)
    for code in _STATE_CODES:
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
        domains[f"{code}_gov"] = {
            "name": f"{code.upper()} Government Portal",
            "url": f"https://www.nic.in/{code}"
        }

    # 2. State departments subdomains (combining states * depts)
    for code in _STATE_CODES:
        for dept in _DEPARTMENTS:
            key = f"{code}_{dept}"
            domains[key] = {
                "name": f"{code.upper()} {dept.title()} Department",
                "url": f"https://{dept}.{code}.gov.in"
            }

    # 3. Districts (NIC Portals)
    for dist in _DISTRICTS:
        key = f"dist_{dist}"
        domains[key] = {
            "name": f"{dist.title()} District Portal",
            "url": f"https://{dist}.nic.in"
        }

    # 4. Municipal Corporations
    for muni in _MUNICIPALITIES:
        key = f"muni_{muni}"
        domains[key] = {
            "name": f"{muni.upper().replace('_', ' ')} Municipal Corporation",
            "url": f"https://www.{muni}.org"
        }

    # 5. PSUs
    for dom in _PSU_DOMAINS:
        key = dom.split(".")[0]
        domains[key] = {
            "name": f"{key.upper()} (Central PSU)",
            "url": f"https://www.{dom}"
        }

    # 6. State PSUs (rtc, transco, genco)
    for code in _STATE_CODES:
        domains[f"{code}_transco"] = {
            "name": f"{code.upper()} Transmission Corp (State PSU)",
            "url": f"https://{code}transco.co.in"
        }
        domains[f"{code}_genco"] = {
            "name": f"{code.upper()} Power Generation Corp (State PSU)",
            "url": f"https://{code}genco.co.in"
        }
        domains[f"{code}_rtc"] = {
            "name": f"{code.upper()} Road Transport Corp (State PSU)",
            "url": f"https://{code}rtc.in"
        }

    # 7. Banks
    for dom in _BANK_DOMAINS:
        key = dom.split(".")[0]
        domains[f"bank_{key}"] = {
            "name": f"{key.upper()} (Public Sector Banking/Insurance)",
            "url": f"https://www.{dom}"
        }

    # 8. Academic
    for dom in _ACADEMIC_SEEDS:
        key = dom.split(".")[0]
        domains[key] = {
            "name": f"{key.upper()} (Elite Academic/Research)",
            "url": f"https://www.{dom}"
        }

    # 9. Ministries & Labs
    for dom in _MINISTRIES_LABS:
        key = dom.split(".")[0]
        domains[f"lab_{key}"] = {
            "name": f"{key.upper()} (Ministry/Research Lab)",
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
