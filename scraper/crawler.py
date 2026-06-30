"""
scraper/crawler.py

Main crawler that orchestrates the full job discovery and scraping pipeline.

Pipeline:
  Discover (find URLs) → Fetch (download pages) → Parse (extract listings)
  → Filter (classify relevance) → Diff (track state) → Notify (Discord/Email)

Designed to be the primary entry point. The CLI in main.py delegates here.
Extension points are marked for future Playwright (SPA) and curl_cffi (TLS)
integration without changing the pipeline flow.
"""

import ssl
import sys
import os
import json
import time
import signal
import threading
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from scraper.config import ORGS_CONFIG, DEFAULT_HEADERS, MAIN_ORGS
from scraper.page_classifier import score_page as _page_score
from scraper.learned_vocab import get_vocab as _get_vocab

# ─── Helpers ────────────────────────────────────────────────────────────────

_MAX_HISTORY_ENTRIES = 365  # cap archive at ~1 year of daily runs


def _quality_label(pct):
    """Map a relevance percentage to a quality label."""
    if pct >= 80:
        return "HIGH"
    elif pct >= 50:
        return "MEDIUM"
    elif pct >= 20:
        return "LOW"
    return "NOISE"
import scraper.parsers as parsers
import scraper.discovery as discovery
from scraper.filters import annotate
from scraper.diff import diff_and_update_state
from scraper.notify_discord import send_discord_notifications
from scraper.notify_email import send_email_notifications
from scraper.export import save_jobs_json


# ─── Network-failure sentinel ────────────────────────────────────────────────
# Returned by fetch_org when the failure is a transient network issue
# (timeout, connection reset, circuit breaker, DNS failure).
# Distinct from None (code error) so run_all_orgs.py can omit it from the
# failure count while still preserving previous state in diff.
SERVER_DOWN = object()

# ─── SSL Adapter (shared across all HTTP requests) ───────────────────────────

class RobustGovAdapter(HTTPAdapter):
    """
    SSL adapter for Indian government sites that use:
      - Legacy TLS renegotiation (OP_LEGACY_SERVER_CONNECT)
      - Self-signed or locally-issued certificates (cert_reqs=CERT_NONE)

    Safe for monitoring-only use cases; not for auth/sensitive data.

    Extension point: Replace with curl_cffi's CurlSession for TLS fingerprint
    impersonation when targeting Cloudflare-protected sites.
    """
    def init_poolmanager(self, connections, maxsize, block=False):
        ctx = ssl.create_default_context()
        ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
            cert_reqs=ssl.CERT_NONE,
            # Note: assert_hostname removed — urllib3 v2 dropped this kwarg;
            # hostname checking is already disabled via ctx.check_hostname=False
        )

    def cert_verify(self, conn, url, verify, cert):
        # Force verify=False for all requests using this adapter
        super().cert_verify(conn, url, False, cert)


# ─── Parser Map ──────────────────────────────────────────────────────────────

# Maps org keys to their parser functions.
# orgs with `None` are handled specially by _scrape_org (e.g. API-based parsers).
PARSER_MAP = {
    "cdac": parsers.parse_cdac,
    "bel": parsers.parse_bel,
    "drdo": parsers.parse_drdo,
    "isro": parsers.parse_isro,
    "barc": parsers.parse_barc,
    "bsnl": parsers.parse_bsnl,
    "certin": parsers.parse_certin,
    "employment_news": parsers.parse_employment_news,
    "cdot": parsers.parse_cdot,
    "uppsc": parsers.parse_uppsc,
    "nielit": None,   # handled via parsers.parse_nielit(session) — internal API
    "ncs": None,      # handled via parsers.parse_ncs(session) — internal API
    "ecil": parsers.parse_ecil,
    "stpi": parsers.parse_stpi,
    "nic": parsers.parse_nic,
    "hal": parsers.parse_hal,
    "cris": parsers.parse_cris,
    "ongc": parsers.parse_ongc,
    "sail": parsers.parse_sail,
    "ntpc": parsers.parse_ntpc,
    "aai": parsers.parse_aai,
    "rrb": None,          # handled via _fetch_spa() — React SPA, needs Playwright
    "rrb_static": parsers.parse_rrb,
    "drdo_spa": None,     # handled via _fetch_spa() — Playwright variant for DRDO
    "sameer": parsers.parse_sameer,
    "ernet": parsers.parse_ernet,
    "uidai": parsers.parse_uidai,
    "pgcil": parsers.parse_pgcil,
    "iocl": parsers.parse_iocl,
    "bhel": parsers.parse_bhel,
    "coal_india": parsers.parse_coal_india,
    "railtel": parsers.parse_railtel,
    "becil": parsers.parse_becil,
    "sebi": parsers.parse_sebi,
    "sidbi": parsers.parse_sidbi,
    "sjvn": parsers.parse_sjvn,
    "tcil": parsers.parse_tcil,
    "dic": parsers.parse_dic,
    "npcil": parsers.parse_npcil,
    "rites": parsers.parse_rites,
    "dfccil": parsers.parse_dfccil,
    "scl": parsers.parse_scl,
    "csir_4pi": parsers.parse_csir_4pi,
    "igcar": parsers.parse_igcar,
    "rrcat": parsers.parse_rrcat,
    "bpcl": parsers.parse_bpcl,
    "pfc": parsers.parse_pfc,
    "rec": parsers.parse_rec,
    "iti": parsers.parse_iti,
    "cel": parsers.parse_cel,
    "nhpc": parsers.parse_nhpc,
    "grid_india": parsers.parse_grid_india,
    "hpcl": parsers.parse_hpcl,
    "rbi": parsers.parse_rbi,
    "negd": parsers.parse_negd,
    "nixi": parsers.parse_nixi,
    "bisag_n": parsers.parse_bisag_n,
    "upsc": parsers.parse_upsc,
    "ssc": parsers.parse_ssc,
    "irctc": parsers.parse_irctc,
    "concor": None,
    "eil": parsers.parse_eil,
    "mpsc": parsers.parse_mpsc,
    "gpsc": parsers.parse_gpsc,
    "keralapsc": parsers.parse_keralapsc,
    "rpsc": parsers.parse_rpsc,
    "tnpsc": parsers.parse_tnpsc,
    "opsc": parsers.parse_opsc,
    "wbpsc": parsers.parse_wbpsc,
    "appsc": parsers.parse_appsc,
    "mppsc": parsers.parse_mppsc,
    "hpsc": parsers.parse_hpsc,
    "ppsc": parsers.parse_ppsc,
    "ukpsc": parsers.parse_ukpsc,
    "cgpsc": parsers.parse_cgpsc,
    "jpsc": parsers.parse_jpsc,
    "ibps": parsers.parse_ibps,
    "sbi": parsers.parse_sbi,
    "nabard": parsers.parse_nabard,
    "nhb": parsers.parse_nhb,
    "gail": parsers.parse_gail,
    "oil": parsers.parse_oil,
    "nalco": parsers.parse_nalco,
    "mdl": parsers.parse_mdl,
    "dsssb": parsers.parse_dsssb,
    "rsmssb": parsers.parse_rsmssb,
    "hssc": parsers.parse_hssc,
}


# ─── GovJobCrawler ────────────────────────────────────────────────────────────


class GovJobCrawler:
    """
    Orchestrates the full job discovery-to-notification pipeline.

    Usage:
        crawler = GovJobCrawler()
        crawler.run_pipeline()                   # full pipeline: all orgs
        crawler.run_pipeline(orgs=["cdac"])      # single org
        crawler.run_discovery()                  # discover only
        crawler.run_discovery(orgs=["cdac"])     # discover single org
        crawler.run_scrape()                     # scrape only (no discovery)
    """

    def __init__(self, session=None):
        self.session = session or self._create_session()
        self.thread_local = threading.local()

    def _log(self, msg, end="\n"):
        log_list = getattr(self.thread_local, "log_list", None)
        if log_list is not None:
            log_list.append(msg + end)
        else:
            print(msg, end=end)

    # ── Session factory ─────────────────────────────────────────────────────

    @staticmethod
    def _create_session():
        """
        Create a pre-configured requests.Session with the RobustGovAdapter
        and attach a thread-safe caching layer for HTML GET responses.
        """
        session = requests.Session()
        session.mount("https://", RobustGovAdapter(pool_connections=200, pool_maxsize=20))
        session.mount("http://", RobustGovAdapter(pool_connections=200, pool_maxsize=20))
        
        # Thread-safe caching layer and SLD locks on the requests session
        session._html_cache = {}
        session._cache_lock = threading.Lock()
        session._sld_locks = {}
        session._sld_lock_lock = threading.Lock()
        session._sld_last_request_time = {}
        # Circuit breaker: maps Host -> True when any timeout is recorded.
        # All future requests to the same host raise immediately.
        session._host_down = {}
        session._host_down_lock = threading.Lock()
        # Canary coordination: maps Host -> threading.Event.
        # The FIRST thread per host becomes the canary and makes the real request.
        # All other threads for the same host block on the Event until the canary
        # completes.  If the canary times out and trips the breaker, waiters see
        # the breaker instantly rather than each burning their own 5 s timeout.
        session._host_canary = {}          # host -> threading.Event (once set = done)
        session._host_canary_lock = threading.Lock()

        orig_get = session.get

        def cached_get(url, *args, **kwargs):
            from urllib.parse import urlparse
            import time

            # Extract SLD (Second-Level Domain) for rate limiting
            try:
                parsed = urlparse(url)
                host = parsed.netloc.lower()
                if host.startswith("www."):
                    host = host[4:]
                parts = host.split(".")
                if len(parts) >= 3 and parts[-2] in ("gov", "nic", "res", "ac", "co", "org", "edu"):
                    sld = ".".join(parts[-3:])
                elif len(parts) >= 2:
                    sld = ".".join(parts[-2:])
                else:
                    sld = host
            except Exception:
                host = url
                sld = url

            is_scale = os.environ.get("SCALE_CRAWL") == "1"
            # Always lock at SLD level — different subdomains of the same SLD
            # (e.g. fisheries.nagaland.gov.in / forest.nagaland.gov.in) share the
            # same physical server. Per-host locking let workers hammer all
            # subdomains simultaneously → overload → timeouts. SLD-level
            # locking serialises requests within one government server cluster.
            lock_key = sld

            # ── Scale-mode circuit breaker + canary coordination ──────────────
            is_canary = False
            canary_evt = None
            if is_scale:
                # Fast path: Host already known to be down
                with session._host_down_lock:
                    if host in session._host_down:
                        from requests.exceptions import ConnectTimeout
                        raise ConnectTimeout(
                            f"Circuit breaker: {host} marked down after prior ConnectTimeout"
                        )

                # Canary election: first thread per host wins; others wait
                with session._host_canary_lock:
                    existing_evt = session._host_canary.get(host)
                    if existing_evt is None:
                        canary_evt = threading.Event()
                        session._host_canary[host] = canary_evt
                        is_canary = True
                    else:
                        canary_evt = existing_evt
                        is_canary = False

                if not is_canary:
                    # Wait for the canary to finish (up to 30 s),
                    # then re-check the circuit breaker.
                    canary_evt.wait(timeout=30)
                    with session._host_down_lock:
                        if host in session._host_down:
                            from requests.exceptions import ConnectTimeout
                            raise ConnectTimeout(
                                f"Circuit breaker: {host} marked down after prior ConnectTimeout"
                            )

            # ── Per-host lock (rate limiting + HTML cache) ────────────────────
            with session._sld_lock_lock:
                if lock_key not in session._sld_locks:
                    session._sld_locks[lock_key] = threading.Lock()
                lock = session._sld_locks[lock_key]

            with lock:
                last_time = session._sld_last_request_time.get(lock_key, 0)
                now = time.time()
                elapsed = now - last_time

                if is_scale:
                    delay = 0.1
                else:
                    delay = 0.8 if ("gov.in" in sld or "nic.in" in sld) else 0.1

                if elapsed < delay:
                    time.sleep(delay - elapsed)

                session._sld_last_request_time[lock_key] = time.time()

                is_cacheable = kwargs.get("stream") is not True
                if not is_cacheable:
                    try:
                        return orig_get(url, *args, **kwargs)
                    finally:
                        if is_scale and is_canary and canary_evt is not None:
                            canary_evt.set()

                with session._cache_lock:
                    if url in session._html_cache:
                        if is_scale and is_canary and canary_evt is not None:
                            canary_evt.set()
                        return session._html_cache[url]

                try:
                    resp = orig_get(url, *args, **kwargs)
                except Exception as exc:
                    # Trip the circuit breaker for any timeout (connect OR read).
                    # ConnectTimeout: server unreachable (karnataka.gov.in).
                    # ReadTimeout:    server hangs on response (assam.gov.in).
                    if is_scale:
                        err_str = str(exc)
                        exc_type = type(exc).__name__
                        is_timeout = (
                            "ConnectTimeoutError" in err_str
                            or "connect timeout" in err_str.lower()
                            or "Read timed out" in err_str
                            or "ReadTimeout" in exc_type
                            or "read timeout" in err_str.lower()
                        )
                        if is_timeout:
                            with session._host_down_lock:
                                session._host_down[host] = True
                        # Always signal canary done (even on non-timeout errors)
                        if is_canary and canary_evt is not None:
                            canary_evt.set()
                    raise

                # Success path: signal canary done before returning
                if is_scale and is_canary and canary_evt is not None:
                    canary_evt.set()

                if resp.status_code == 200:
                    with session._cache_lock:
                        session._html_cache[url] = resp
                return resp
            
        session.get = cached_get
        return session

    # ── Discovery phase ─────────────────────────────────────────────────────

    def run_discovery(self, orgs=None):
        """
        Phase 1: Discover job-related URLs by checking sitemaps and homepages.

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.

        Returns:
            dict: org_key -> list of discovered candidate URL dicts.
        """
        if orgs is None:
            orgs = MAIN_ORGS

        print("=" * 60)
        print("  CRAWLER — DISCOVERY PHASE")
        print("  Scanning org homepages & sitemaps for job listing URLs")
        print("=" * 60)

        results = discovery.discover_all(self.session, orgs=orgs)

        print("\n" + "=" * 60)
        print("  DISCOVERY SUMMARY")
        print("=" * 60)

        total_found = 0
        for key, candidates in results.items():
            name = ORGS_CONFIG.get(key, {}).get("name", key)
            high = [c for c in candidates if c["score"] >= 50]
            medium = [c for c in candidates if 30 <= c["score"] < 50]

            if candidates:
                print(f"\n{name} ({key}):")
                print(f"  Strong matches: {len(high)}")
                for c in high[:5]:
                    print(f"    [{c['score']:>3}] {c['url'][:90]}")
                if medium:
                    print(f"  Weak matches: {len(medium)}")
                total_found += len(candidates)
            else:
                print(f"\n{name} ({key}): No job-related URLs discovered")

        print(f"\n{'=' * 60}")
        print(f"  Total: {total_found} candidate URLs across {len(orgs)} org(s)")
        print(f"  Review candidates and add new URLs to ORGS_CONFIG in config.py")
        print(f"{'=' * 60}")

        return results

    # ── Scrape phase ────────────────────────────────────────────────────────

    def run_scrape(self, orgs=None, max_workers=4, export_json="scraped_jobs.json"):
        """
        Phase 2: Fetch and parse job listings from all configured org URLs.

        Uses ThreadPoolExecutor for concurrent fetching — up to max_workers
        orgs are scraped in parallel, cutting wall-clock time from ~80s to ~25s.
        A threading lock protects console output so lines don't interleave.

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.
            max_workers: Max concurrent scrape threads (default 4).
            export_json: File path for the auto-generated JSON export.
                         Defaults to 'scraped_jobs.json' in the working directory.
                         Set to None to disable export.

        Returns:
            dict: org_key -> list of filtered posting dicts (or None on failure).
        """
        if orgs is None:
            orgs = MAIN_ORGS

        print(f"Crawler targeting {len(orgs)} organization(s): {', '.join(orgs)}")
        print(f"Concurrent workers: {max_workers}")

        scraped_data = {}
        lock = threading.Lock()

        def _scrape_thread(key):
            """Scrape one org; lock only around shared output."""
            try:
                with lock:
                    print(f"  [{key}] starting...")
                result = self._scrape_org(key)
                with lock:
                    scraped_data[key] = result
                return result
            except Exception as exc:
                with lock:
                    print(f"  FATAL: {key} thread crashed: {exc}")
                    scraped_data[key] = None
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_scrape_thread, key): key for key in orgs}
            for future in as_completed(futures):
                # Wait for completion — data already stored in scraped_data
                future.result()

        # ── Auto JSON export — always runs after every scrape ─────────────────
        if export_json:
            save_jobs_json(scraped_data, filepath=export_json)

        return scraped_data

    def _scrape_org(self, key, log_list=None):
        """
        Scrape a single organization. Handles all fetch strategies:
          - Standard GET + HTML parse
          - NIELIT internal JSON API
          - NCS internal JSON API
          - HAL WordPress POST API
          - BARC RSS feed (bytes)
          - NIC legacy encoding (bytes)

        Extension point: Add Playwright browser scraping for SPAs here.
        """
        self.thread_local.log_list = log_list

        if key not in ORGS_CONFIG:
            self._log(f"  SKIP: {key} not in ORGS_CONFIG")
            return None

        cfg = ORGS_CONFIG[key]
        org_name = cfg["name"]
        url = cfg["url"]
        if cfg.get("resolve_career"):
            from scraper.domain_seeder import resolve_career_url
            try:
                resolved = resolve_career_url(url, session=self.session)
                if resolved:
                    url = resolved
            except Exception:
                pass
        parser_fn = PARSER_MAP.get(key)
        is_special = cfg.get("special") in ("api", "json_api", "hal_api", "ncs_api", "playwright")

        # Standard HTML pages can be parsed via the AdaptiveParser even without custom parser mapped.
        # No error return needed if not parser_fn.

        self._log(f"  Fetching {org_name}...", end=" ")

        try:
            # ── Special API-based parsers ────────────────────────────────
            if key == "nielit":
                postings = parsers.parse_nielit(session=self.session)
            elif key == "ncs":
                postings = parsers.parse_ncs(session=self.session)
            elif key == "iith":
                from scraper.spa_scraper import parse_iith_spa
                postings = parse_iith_spa()
            elif cfg.get("special") == "hal_api":
                postings = self._fetch_hal(url)
            elif cfg.get("special") == "playwright":
                postings = self._fetch_spa(key, url)
            else:
                # ── Standard HTTP fetch ──────────────────────────────────
                is_scale = os.environ.get("SCALE_CRAWL") == "1"
                timeout = 15 if is_scale else 15
                r = None
                try_cffi = False
                try:
                    r = self.session.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
                    if r.status_code in (403, 503, 429, 401, 502, 504):
                        try_cffi = True
                except Exception as exc:
                    err_str = str(exc)
                    if any(sig in err_str.lower() for sig in ("connectionreseterror", "10054", "connection aborted", "remotedisconnected", "timeout")):
                        try_cffi = True
                    else:
                        raise

                if try_cffi:
                    self._log(f"[WAF/network reset, retrying with curl_cffi]", end=" ")
                    try:
                        from curl_cffi import requests as cffi_requests
                        cr = cffi_requests.get(
                            url,
                            impersonate="chrome120",
                            headers={
                                "Accept": DEFAULT_HEADERS["Accept"],
                                "Accept-Language": DEFAULT_HEADERS["Accept-Language"],
                            },
                            timeout=timeout,
                            verify=False,
                        )
                        # Wrap in a simple namespace so downstream code sees .text / .headers
                        class _Resp:
                            def __init__(self, r):
                                self.text = r.text
                                self.content = r.content
                                self.status_code = r.status_code
                                self.headers = r.headers
                            def raise_for_status(self):
                                if self.status_code >= 400:
                                    raise Exception(f"HTTP {self.status_code}")
                        r = _Resp(cr)
                    except Exception as cffi_exc:
                        if r is None:
                            raise cffi_exc
                
                if r is None:
                    raise Exception("Failed to fetch page")
                r.raise_for_status()

                content_type = r.headers.get("Content-Type", "").lower()
                _pg_score = 0.0  # default; computed for HTML pages below

                # Check for PDF response directly on the landing page URL
                if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                    filename = url.split("/")[-1].split("?")[0] or "document.pdf"
                    title = filename.replace("_", " ").replace("-", " ").replace(".pdf", "").title()
                    if not title or len(title) < 5:
                        title = f"{org_name} Job Notification"
                    postings = [{"title": title, "link": url, "date": ""}]
                # Check for other binary file types
                elif any(ext in content_type or url.lower().endswith(ext) for ext in (".docx", ".doc", ".xls", ".xlsx", ".zip", ".png", ".jpg", ".jpeg")):
                    filename = url.split("/")[-1].split("?")[0] or "document"
                    title = filename.replace("_", " ").replace("-", " ").title()
                    postings = [{"title": f"{org_name} Notification: {title}", "link": url, "date": ""}]
                elif key in ("barc", "nic"):
                    content = r.content
                    postings = parser_fn(content)
                else:
                    _pg_score = _page_score(r.text)
                    from scraper.adaptive_parser import parse_adaptive
                    try:
                        postings = parse_adaptive(r.text, base_url=url)
                    except Exception as e:
                        self._log(f"WARNING: parse_adaptive failed on {url}: {e}")
                        postings = []

                    # Fallback to legacy custom parser if adaptive found nothing
                    if not postings and parser_fn:
                        try:
                            postings = parser_fn(r.text)
                        except Exception as e:
                            self._log(f"WARNING: parser_fn failed on {url}: {e}")

                    # ── Self-thinking: sub-page exploration ──────────────────────
                    # If the main page yielded nothing but shows some job-page
                    # signal (page_score > 0.20), explore the top-scored links
                    # on the page autonomously (1 hop deeper, max 3 links).
                    if not postings and _pg_score >= 0.20:
                        subpage_postings = self._explore_subpages(
                            r.text, base_url=url, org_key=key
                        )
                        if subpage_postings:
                            postings = subpage_postings
                            self._log(f"[sub-page exploration found {len(postings)} listings]")

            annotate(postings, org_key=key, session=self.session)

            # Filter out cross-domain links (links pointing to other organizations' domains)
            from urllib.parse import urlparse
            cfg = ORGS_CONFIG.get(key, {})
            allowed_domains = set()
            for url_field in [cfg.get("url", "")] + cfg.get("homepages", []):
                if url_field:
                    parsed = urlparse(url_field)
                    if parsed.netloc:
                        dom = parsed.netloc.lower()
                        if dom.startswith("www."):
                            dom = dom[4:]
                        allowed_domains.add(dom)

            # Extend allowed domains to parent state or university domains
            extended_allowed = set(allowed_domains)
            for dom in allowed_domains:
                parts = dom.split(".")
                if len(parts) >= 3:
                    suffix_3 = ".".join(parts[-3:])
                    if any(suffix_3.endswith(s) for s in (".gov.in", ".nic.in", ".edu.in", ".ac.in", ".co.in", ".org.in", ".res.in")):
                        extended_allowed.add(suffix_3)
                if len(parts) >= 2:
                    suffix_2 = ".".join(parts[-2:])
                    if any(suffix_2.endswith(s) for s in (".edu", ".org", ".com", ".net", ".in")):
                        extended_allowed.add(suffix_2)
            allowed_domains = extended_allowed

            # Standard globally allowed domains for document sharing, application forms, etc.
            GLOBAL_ALLOWED_DOMAINS = {
                "google.com", "docs.google.com", "drive.google.com", "forms.gle",
                "github.com", "dropbox.com", "samarth.edu.in", "samarth.ac.in",
                "mponline.gov.in", "nta.nic.in", "digialm.com", "careers.irrtc.co.in",
                "ecareer.in", "digilocker.gov.in", "s3.amazonaws.com"
            }

            filtered_postings = []
            for p in postings:
                p_url = p.get("link", "").strip()
                if not p_url:
                    continue
                parsed_p = urlparse(p_url)
                if not parsed_p.netloc:
                    filtered_postings.append(p)
                    continue
                p_dom = parsed_p.netloc.lower()
                if p_dom.startswith("www."):
                    p_dom = p_dom[4:]
                
                is_allowed = False
                for allowed in allowed_domains:
                    if p_dom == allowed or p_dom.endswith("." + allowed):
                        is_allowed = True
                        break
                if not is_allowed:
                    for global_dom in GLOBAL_ALLOWED_DOMAINS:
                        if p_dom == global_dom or p_dom.endswith("." + global_dom):
                            is_allowed = True
                            break
                if is_allowed:
                    filtered_postings.append(p)
            postings = filtered_postings

            # Deduplicate and group by title and URL to separate apply_link vs pdf_link
            import re
            
            def normalize_url(url):
                if not url or url.strip() in {"", "#", "javascript:void(0);"}:
                    return ""
                url = url.split("?")[0].split("#")[0]
                if url.endswith("/"):
                    url = url[:-1]
                return url.strip().lower()

            def clean_title(t):
                t = re.sub(r"[^a-zA-Z0-9\s]", " ", t.lower())
                return re.sub(r"\s+", " ", t).strip()

            GENERIC_TITLES = {"notification", "recruitment", "careers", "jobs", "vacancy", "advertisement", "click here", "view", "details", "heading"}

            merged_groups = []

            for p in postings:
                title = p.get("title", "").strip()
                if not title:
                    continue
                
                link = p.get("link", "").strip()
                norm_title = clean_title(title)
                norm_url = normalize_url(link)
                is_pdf = link.lower().endswith(".pdf") or ".pdf?" in link.lower()

                # Try to find a matching group to merge with
                matched_group = None
                for g in merged_groups:
                    # Match by URL
                    if norm_url:
                        g_apply_norm = normalize_url(g["apply_link"])
                        g_pdf_norm = normalize_url(g["pdf_link"])
                        if norm_url in (g_apply_norm, g_pdf_norm):
                            matched_group = g
                            break
                    
                    # Match by Title
                    if norm_title and norm_title not in GENERIC_TITLES and len(norm_title) > 8:
                        if norm_title == clean_title(g["title"]):
                            # One must be PDF and the other must be webpage
                            g_has_pdf = bool(g["pdf_link"])
                            g_has_web = bool(g["apply_link"])
                            if (is_pdf and not g_has_pdf) or (not is_pdf and not g_has_web):
                                matched_group = g
                                break

                if matched_group:
                    # Merge date if empty
                    if not matched_group["date"] and p.get("date", ""):
                        matched_group["date"] = p.get("date", "")
                    
                    # Keep more relevant category
                    rel_rank = {"relevant": 2, "uncertain": 1, "excluded": 0}
                    p_rel = p.get("relevance", "uncertain")
                    g_rel = matched_group["relevance"]
                    if rel_rank.get(p_rel, 0) > rel_rank.get(g_rel, 0):
                        matched_group["relevance"] = p_rel
                    
                    # Merge links
                    if is_pdf:
                        if not matched_group["pdf_link"]:
                            matched_group["pdf_link"] = link
                    else:
                        if not matched_group["apply_link"]:
                            matched_group["apply_link"] = link
                else:
                    # Create new group
                    merged_groups.append({
                        "title": title,
                        "date": p.get("date", ""),
                        "relevance": p.get("relevance", "uncertain"),
                        "apply_link": "" if is_pdf else link,
                        "pdf_link": link if is_pdf else "",
                    })

            final_postings = []
            for g in merged_groups:
                p_out = {
                    "title": g["title"],
                    "link": g["apply_link"] or g["pdf_link"],
                    "apply_link": g["apply_link"],
                    "pdf_link": g["pdf_link"],
                    "date": g["date"],
                    "relevance": g["relevance"]
                }
                final_postings.append(p_out)

            filtered = [p for p in final_postings if p.get("relevance") != "excluded"]
            self._log(f"{len(filtered)} listings (from {len(postings)})")
            return filtered

        except Exception as exc:
            err_str = str(exc)
            # Network-level failures: timeout, reset, DNS, circuit breaker.
            # Return SERVER_DOWN so the caller can distinguish these from real
            # code/parsing errors and not count them in the failure total.
            # Use BOTH isinstance (reliable) and string matching (catches wrapped exceptions).
            import requests.exceptions as _rex
            _is_network_type = isinstance(exc, (
                _rex.Timeout,          # ReadTimeout, ConnectTimeout
                _rex.ConnectionError,  # all connection-level errors
            ))
            _NETWORK_STRINGS = (
                "connecttimeouterror", "readtimeout", "read timed out",
                "connect timeout", "connecttimeout", "connection timed out",
                "timed out", "timeout", "time out", "operation timed out",
                "connectionreseterror", "connection aborted", "connection was reset", "connection reset",
                "remotedisconnected", "nameresolutionerror", "recv failure",
                "getaddrinfo failed", "circuit breaker",
                "newconnectionerror", "max retries exceeded",
                # Transient HTTP server errors (5xx, 429) & status codes
                "503 server error", "502 server error", "504 server error", "500 server error",
                "503", "502", "504", "500", "429", "403",
                "http 503", "http 502", "http 504", "http 500", "http 429", "http 403",
                "service temporarily unavailable", "bad gateway", "internal server error",
                # curl_cffi and libcurl-specific codes (e.g. timeout = 28, connection reset = 35)
                "curl: (28)", "curl: (35)", "curl: (7)", "curl: (52)", "curl: (56)",
            )
            _is_network_str = any(sig in err_str.lower() for sig in _NETWORK_STRINGS)
            is_network = _is_network_type or _is_network_str
            self._log(f"ERROR: {exc}")
            if is_network:
                return SERVER_DOWN  # transient network issue — preserve state
            return None  # code/parsing error — also preserves state


    def _explore_subpages(self, html, base_url, org_key, max_links=3, timeout=10):
        """
        Self-thinking sub-page exploration.

        When the main page yields no postings, this method:
          1. Extracts all internal links from the page
          2. Scores each link via CareerURLVocabulary (no LLM)
          3. Fetches the top `max_links` candidates
          4. Parses each with parse_adaptive
          5. Records successful patterns back into the vocabulary

        Returns combined postings list (may be empty).
        """
        from urllib.parse import urlparse, urljoin
        from bs4 import BeautifulSoup
        from scraper.adaptive_parser import parse_adaptive

        try:
            soup = BeautifulSoup(html, "html.parser")
            base_host = urlparse(base_url).netloc
            vocab = _get_vocab()

            # Score all internal links
            candidates = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith(("javascript:", "mailto:", "#", "tel:")):
                    continue
                abs_href = urljoin(base_url, href)
                # Stay on the same host
                if urlparse(abs_href).netloc != base_host:
                    continue
                text = a.get_text().strip()
                score = vocab.score_link(abs_href, text, base_host)
                if score > 0:
                    candidates.append((score, abs_href, text))

            # Sort by score descending, take top N unique URLs
            candidates.sort(key=lambda x: -x[0])
            seen = set()
            top_candidates = []
            for score, url, text in candidates:
                if url not in seen:
                    seen.add(url)
                    top_candidates.append((score, url))
                    if len(top_candidates) >= max_links:
                        break

            if not top_candidates:
                return []

            self._log(f"[exploring {len(top_candidates)} sub-pages: {[u for _, u in top_candidates]}]")

            # Fetch and parse top candidates
            all_postings = []
            for score, sub_url in top_candidates:
                try:
                    sub_r = self.session.get(sub_url, headers=DEFAULT_HEADERS,
                                             timeout=timeout, verify=False)
                    # Check if sub_url is a direct PDF/binary file
                    sub_content_type = sub_r.headers.get("Content-Type", "").lower()
                    is_pdf = "application/pdf" in sub_content_type or sub_url.lower().endswith(".pdf")
                    is_binary = any(ext in sub_content_type or sub_url.lower().endswith(ext) 
                                    for ext in (".docx", ".doc", ".xls", ".xlsx", ".zip", ".png", ".jpg", ".jpeg"))
                    
                    if is_pdf:
                        filename = sub_url.split("/")[-1].split("?")[0] or "document.pdf"
                        title = filename.replace("_", " ").replace("-", " ").replace(".pdf", "").title()
                        if not title or len(title) < 5:
                            title = f"{ORGS_CONFIG.get(org_key, {}).get('name', org_key)} Job Notification"
                        all_postings.append({"title": title, "link": sub_url, "date": ""})
                        vocab.record_success(base_url, sub_url)
                        continue
                    elif is_binary:
                        filename = sub_url.split("/")[-1].split("?")[0] or "document"
                        title = filename.replace("_", " ").replace("-", " ").title()
                        all_postings.append({"title": f"{ORGS_CONFIG.get(org_key, {}).get('name', org_key)} Notification: {title}", "link": sub_url, "date": ""})
                        vocab.record_success(base_url, sub_url)
                        continue

                    sub_score = _page_score(sub_r.text)
                    if sub_score < 0.15:
                        continue  # page classifier says it's not a jobs page
                    sub_postings = parse_adaptive(sub_r.text, base_url=sub_url)
                    if sub_postings:
                        all_postings.extend(sub_postings)
                        # Reinforce this URL pattern in the vocabulary
                        vocab.record_success(base_url, sub_url)
                except Exception:
                    continue

            return all_postings

        except Exception:
            return []

    # Static fallback URL for RRB when SPA returns no useful content
    _RRB_STATIC_URL = "https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,554"

    def _fallback_to_static(self, reason=""):
        """Fetch RRB static board page as fallback when SPA returns no data."""
        if reason:
            self._log(f"{reason}, falling back to static page...", end=" ")
        try:
            is_scale = os.environ.get("SCALE_CRAWL") == "1"
            timeout = 15 if is_scale else 15
            r = self.session.get(
                self._RRB_STATIC_URL,
                headers=DEFAULT_HEADERS, timeout=timeout,
            )
            r.raise_for_status()
            postings = parsers.parse_rrb(r.text)
            self._log(f"→ static fallback got {len(postings)} listings")
            return postings
        except Exception:
            self._log("→ static fallback also failed")
            return []

    def _fetch_spa(self, key, url):
        """
        Fetch a page using Playwright headless Chromium for SPAs.

        Uses the spa_scraper module to render JavaScript and extract HTML,
        then passes the rendered content to the org's parser function.

        Falls back to the static parser (parse_rrb) for RRB if SPA returns
        no useful content.
        """
        from scraper.spa_scraper import fetch_spa_page, parse_rrb_spa, parse_drdo_spa, parse_generic_spa, parse_iitb_spa, parse_iitm_spa

        self._log(f"[SPA] Launching Chromium for {key}...", end=" ")

        # Wait selector: try to find job listing containers
        wait_sel = None
        if key == "rrb":
            wait_sel = "div[class*='card'], div[class*='cen'], div[class*='recruit'], table, .job-listing"

        html = fetch_spa_page(url, wait_selector=wait_sel, timeout_ms=30000)

        if not html or len(html) < 500:
            return self._fallback_to_static("SPA empty")

        # Parse the rendered HTML with org-specific parser
        if key == "rrb":
            postings = parse_rrb_spa(html)
        elif key == "drdo_spa":
            postings = parse_drdo_spa(html)
        elif key == "iitb":
            postings = parse_iitb_spa(html, base_url=url)
        elif key == "iitm":
            postings = parse_iitm_spa(html, base_url=url)
        else:
            postings = parse_generic_spa(html, base_url=url)

        if not postings:
            if key == "rrb":
                return self._fallback_to_static(f"SPA rendered {len(html)} chars but no job data visible (auth-gated)")
            self._log(f"SPA rendered {len(html)} chars but parser found no listings")
            return []

        self._log(f"got {len(postings)} listings")
        return postings

    def _fetch_hal(self, url):
        """
        Fetch HAL career data via the WordPress REST API.
        The site's WAF blocks requests with default script UA; must send
        browser-like headers to get JSON instead of an HTML block page.

        Extension point: Replace with Playwright for Angular SPA rendering
        when the REST API changes.
        """
        hal_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": "https://hal-india.co.in/",
            "Origin": "https://hal-india.co.in",
            "Accept-Language": "en-US,en;q=0.9",
        }
        is_scale = os.environ.get("SCALE_CRAWL") == "1"
        timeout = 10 if is_scale else 30
        r = self.session.post(url, headers=hal_headers, json={}, timeout=timeout)
        r.raise_for_status()
        return parsers.parse_hal(r.text)

    # ── Coverage report ──────────────────────────────────────────────────

    def generate_report(self, orgs=None):
        """
        Run scrape and generate a CS/IT signal-vs-noise coverage report.

        Returns a dict with per-org stats and overall summary.
        """
        if orgs is None:
            orgs = MAIN_ORGS

        scraped_data = self.run_scrape(orgs=orgs)

        report = {"orgs": {}, "summary": {}}
        total_relevant = total_uncertain = total_all = 0

        for key in orgs:
            postings = scraped_data.get(key)
            name = ORGS_CONFIG.get(key, {}).get("name", key)

            if postings is None or postings is SERVER_DOWN:
                report["orgs"][key] = {"name": name, "status": "error", "total": 0, "relevant": 0, "uncertain": 0, "relevant_pct": 0.0, "signal_quality": "N/A"}
                continue

            relevant = sum(1 for p in postings if p.get("relevance") == "relevant")
            uncertain = sum(1 for p in postings if p.get("relevance") == "uncertain")
            total = relevant + uncertain
            pct = round(100 * relevant / total, 1) if total else 0

            quality = _quality_label(pct)

            report["orgs"][key] = {
                "name": name,
                "status": "ok",
                "total": total,
                "relevant": relevant,
                "uncertain": uncertain,
                "relevant_pct": pct,
                "signal_quality": quality,
            }
            total_relevant += relevant
            total_uncertain += uncertain
            total_all += total

        overall_pct = round(100 * total_relevant / total_all, 1) if total_all else 0
        report["summary"] = {
            "total_postings": total_all,
            "total_relevant": total_relevant,
            "total_uncertain": total_uncertain,
            "overall_relevant_pct": overall_pct,
            "orgs_ok": sum(1 for v in report["orgs"].values() if v["status"] == "ok"),
            "orgs_failed": sum(1 for v in report["orgs"].values() if v["status"] == "error"),
        }

        return report

    def save_report_json(self, report, path=None):
        """
        Save coverage report to a JSON file.

        Args:
            report: Report dict from generate_report().
            path: Output file path. Defaults to 'coverage_report.json'.

        Returns:
            str: Absolute path to the written file.
        """
        if path is None:
            path = "coverage_report.json"

        # Add metadata for dashboards
        report_out = {
            "generated_at": datetime.now().isoformat(),
            **report,
        }

        abs_path = os.path.abspath(path)
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(report_out, f, indent=2, ensure_ascii=False)

        print(f"Report saved to {abs_path}")
        return abs_path

    def archive_report(self, report, path=None):
        """
        Append the current report to a historical archive for trend tracking.

        Each entry stores the timestamp, per-org stats, and overall summary.
        The archive is a JSON array that grows over time.

        Args:
            report: Report dict from generate_report().
            path: Archive file path. Defaults to 'coverage_history.json'.

        Returns:
            int: Total number of snapshots in the archive.
        """
        if path is None:
            path = "coverage_history.json"

        abs_path = os.path.abspath(path)

        # Load existing archive
        history = []
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        # Build snapshot
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "org_count": len(report.get("orgs", {})),
            "summary": report.get("summary", {}),
            "orgs": {},
        }
        for key, stats in report.get("orgs", {}).items():
            snapshot["orgs"][key] = {
                "total": stats.get("total", 0),
                "relevant": stats.get("relevant", 0),
                "uncertain": stats.get("uncertain", 0),
                "relevant_pct": stats.get("relevant_pct", 0.0),
                "signal_quality": stats.get("signal_quality", "N/A"),
                "status": stats.get("status", "error"),
            }

        history.append(snapshot)

        # Trim to max entries (keep most recent)
        if len(history) > _MAX_HISTORY_ENTRIES:
            history = history[-_MAX_HISTORY_ENTRIES:]

        # Write archive
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        print(f"Archived report #{len(history)} to {abs_path}")
        return len(history)

    def print_trend(self, path=None, last_n=10):
        """
        Print historical accuracy trends from the coverage archive.

        Shows a compact table of past runs with overall relevance %, total
        listings, orgs scraped, and key changes.

        Args:
            path: Archive file path. Defaults to 'coverage_history.json'.
            last_n: Number of recent snapshots to show (default 10).
        """
        if path is None:
            path = "coverage_history.json"

        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            print(f"No history file found at {abs_path}")
            print("Run --report-archive first to start tracking trends.")
            return

        with open(abs_path, "r", encoding="utf-8") as f:
            history = json.load(f)

        if not history:
            print("History archive is empty.")
            return

        snapshots = history[-last_n:]

        print("\n" + "=" * 70)
        print("  HISTORICAL ACCURACY TREND")
        print("=" * 70)
        print(" {:<12} {:>6} {:>7} {:>6} {:>6} {:>8}".format(
            "Date", "Orgs", "Total", "Rel", "Rel%", "Quality"
        ))
        print("-" * 70)

        prev_pct = None
        for snap in snapshots:
            ts = snap.get("timestamp", "")[:10]  # YYYY-MM-DD
            s = snap.get("summary", {})
            orgs = snap.get("org_count", 0)
            total = s.get("total_postings", 0)
            rel = s.get("total_relevant", 0)
            pct = s.get("overall_relevant_pct", 0.0)

            # Trend arrow
            arrow = ""
            if prev_pct is not None:
                diff = pct - prev_pct
                if diff > 0:
                    arrow = f" (+{diff:.1f})"
                elif diff < 0:
                    arrow = f" ({diff:.1f})"
                else:
                    arrow = " (=)"
            prev_pct = pct

            quality = _quality_label(pct)

            print(" {:<12} {:>6} {:>7} {:>6} {:>5.1f}% {:>7}{}".format(
                ts, orgs, total, rel, pct, quality, arrow
            ))

        print("-" * 70)
        print(f"  Total snapshots: {len(history)}")

        # Summary stats
        if len(history) >= 2:
            first = history[0].get("summary", {}).get("overall_relevant_pct", 0)
            last = history[-1].get("summary", {}).get("overall_relevant_pct", 0)
            change = last - first
            if change > 0:
                print(f"  Overall trend: +{change:.1f}% improvement from first to last run")
            elif change < 0:
                print(f"  Overall trend: {change:.1f}% change from first to last run")
            else:
                print(f"  Overall trend: stable at {last:.1f}%")

        print("=" * 70)

    def print_report(self, report):
        """Pretty-print a coverage report."""
        fmt = " {:<22} {:>5} {:>5} {:>5} {:>7} {:>8}"

        print("\n" + "=" * 60)
        print("  CS/IT COVERAGE REPORT — Signal vs Noise")
        print("=" * 60)
        print(fmt.format("Organization", "Total", "Rel", "Unc", "Rel%", "Quality"))
        print("-" * 60)

        for key, stats in report["orgs"].items():
            name = stats["name"][:22]
            if stats["status"] == "error":
                print(fmt.format(name, " ERR", "-", "-", "-", "N/A"))
            else:
                print(fmt.format(
                    name,
                    stats["total"],
                    stats["relevant"],
                    stats["uncertain"],
                    f"{stats['relevant_pct']}%",
                    _quality_label(stats["relevant_pct"]),
                ))

        print("-" * 60)
        s = report["summary"]
        print(fmt.format(
            "TOTAL",
            s["total_postings"],
            s["total_relevant"],
            s["total_uncertain"],
            f"{s['overall_relevant_pct']}%",
            _quality_label(s["overall_relevant_pct"]),
        ))
        print()
        print(f"  Orgs scraped: {s['orgs_ok']}/{s['orgs_ok'] + s['orgs_failed']}")
        print(f"  Signal quality: HIGH=>=80%  MEDIUM=50-79%  LOW=20-49%  NOISE=<20%")
        print()

        # Rank orgs by relevance
        ranked = [(k, v) for k, v in report["orgs"].items() if v["status"] == "ok" and v["total"] > 0]
        ranked.sort(key=lambda x: x[1]["relevant_pct"], reverse=True)

        print("  TOP 5 (best signal):")
        for key, stats in ranked[:5]:
            print(f"    {stats['name'][:30]} — {stats['relevant_pct']}% relevant ({stats['relevant']}/{stats['total']})")
        print()
        print("  BOTTOM 5 (most noise):")
        for key, stats in ranked[-5:]:
            print(f"    {stats['name'][:30]} — {stats['relevant_pct']}% relevant ({stats['relevant']}/{stats['total']})")
        print("=" * 60)

    # ── Watch mode ─────────────────────────────────────────────────────

    def run_watch(self, orgs=None, interval_minutes=30):
        """
        Watch mode: re-scrape every N minutes and alert on new postings.

        Runs indefinitely until interrupted (Ctrl+C). Each cycle:
          1. Scrape all orgs concurrently
          2. Diff against previous state (saves to state.json)
          3. Send Discord/email alerts only for new postings
          4. Wait for the next interval

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.
            interval_minutes: Minutes between scrape cycles (default 30).
        """
        if orgs is None:
            orgs = MAIN_ORGS

        # Graceful shutdown on Ctrl+C / SIGTERM
        stop_event = threading.Event()

        def _shutdown(signum, frame):
            print(f"\n\n[{datetime.now():%H:%M:%S}] Received signal {signum}, shutting down...")
            stop_event.set()

        signal.signal(signal.SIGINT, _shutdown)
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, _shutdown)

        cycle = 0
        total_new = 0

        print("=" * 60)
        print("  CRAWLER — WATCH MODE")
        print(f"  Orgs: {', '.join(orgs)}")
        print(f"  Interval: {interval_minutes} min")
        print(f"  Press Ctrl+C to stop")
        print("=" * 60)

        while not stop_event.is_set():
            cycle += 1
            now = datetime.now()
            print(f"\n{'─' * 60}")
            print(f"  CYCLE {cycle} — {now:%Y-%m-%d %H:%M:%S}")
            print(f"{'─' * 60}")

            try:
                scraped_data = self.run_scrape(orgs=orgs)
                new_postings = diff_and_update_state(scraped_data)
                cycle_new = sum(len(v) for v in new_postings.values())
                total_new += cycle_new

                if cycle_new > 0:
                    print(f"\n🔔 Detected {cycle_new} new posting(s)! Sending alerts...")
                    send_discord_notifications(new_postings, ORGS_CONFIG)
                    send_email_notifications(new_postings, ORGS_CONFIG)
                else:
                    print(f"\nNo new postings this cycle.")

                # Count total tracked
                total_tracked = sum(
                    len(v) for v in scraped_data.values() if v
                )
                print(f"  Running totals: {total_tracked} tracked, {total_new} new since start")

            except Exception as exc:
                print(f"\n⚠️  Cycle {cycle} failed: {exc}")

            # Sleep in 1-second increments so Ctrl+C is responsive
            print(f"\n  Next scan in {interval_minutes} min...")
            while not stop_event.wait(1):
                pass

        print(f"\n{'=' * 60}")
        print(f"  WATCH MODE STOPPED — {cycle} cycle(s), {total_new} new posting(s)")
        print(f"{'=' * 60}")

    # ── Full pipeline ─────────────────────────────────────────────────────

    def run_pipeline(self, orgs=None, discover_first=False):
        """
        Full pipeline: optionally discover, then scrape, diff, and notify.

        Args:
            orgs: List of org keys. Defaults to MAIN_ORGS.
            discover_first: If True, run discovery before scraping.

        Returns:
            dict: org_key -> list of new posting dicts from this run.
        """
        if orgs is None:
            orgs = MAIN_ORGS

        if discover_first:
            self.run_discovery(orgs=orgs)
            print("\n" + "─" * 60 + "\n")

        scraped_data = self.run_scrape(orgs=orgs)

        # Diff against previous state
        print()
        new_postings = diff_and_update_state(scraped_data)

        # Notify
        total_new = sum(len(v) for v in new_postings.values())
        if total_new > 0:
            print(f"\nAlert! Detected {total_new} new posting(s).")
            send_discord_notifications(new_postings, ORGS_CONFIG)
            send_email_notifications(new_postings, ORGS_CONFIG)
        else:
            print("\nNo new postings detected. Skipping notifications.")

        return new_postings
