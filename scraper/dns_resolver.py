"""
scraper/dns_resolver.py

Custom thread-safe DNS caching and DNS-over-HTTPS (DoH) resolver.
Monkey-patches Python's socket.getaddrinfo to:
  1. Cache resolved IPs locally to bypass DNS lookup overhead.
  2. Fall back to secure DNS-over-HTTPS (DoH) APIs (Cloudflare & Google)
     if local/ISP DNS queries fail or timeout due to concurrency throttling.
  3. Cache resolution failures (negative caching) to avoid spamming network requests for dead domains.
"""

import warnings
warnings.filterwarnings("ignore", message=".*urllib3.*")

import socket
import urllib.request
import json
import threading
import re
import sys

# Store original getaddrinfo
_original_getaddrinfo = socket.getaddrinfo

# Thread-safe in-memory cache for successful resolutions
_dns_cache = {}
_dns_cache_lock = threading.Lock()

# Thread-safe negative cache for failed resolutions (prevents repeating lookups for dead domains)
_failed_dns_cache = {}
_failed_cache_lock = threading.Lock()

# Regex to identify raw IP addresses
_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

def doh_resolve(host):
    """
    Resolve host using public DNS-over-HTTPS (DoH) services.
    Bypasses local/ISP DNS UDP port 53 throttling and packet drops.
    """
    urls = [
        f"https://cloudflare-dns.com/dns-query?name={host}&type=A",
        f"https://dns.google/resolve?name={host}&type=A"
    ]
    for url in urls:
        try:
            req = urllib.request.Request(
                url, 
                headers={
                    "Accept": "application/dns-json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                if data.get("Status") == 0 and "Answer" in data:
                    for ans in data["Answer"]:
                        if ans.get("type") == 1:  # A record type
                            ip = ans["data"].strip()
                            if _IP_RE.match(ip):
                                return ip
        except Exception:
            pass
    return None

def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    # If host is empty, localhost, or already an IP address, bypass custom resolver
    if not host or host in ("localhost", "127.0.0.1", "::1") or _IP_RE.match(host):
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    # Composite key for positive cache to separate different lookup parameters (like ports 80 and 443)
    cache_key = (host, port, family, type, proto, flags)

    # 1. Check positive DNS cache
    with _dns_cache_lock:
        if cache_key in _dns_cache:
            return _dns_cache[cache_key]

    # 2. Check negative DNS cache (host-based, as dead domains don't resolve on any parameters)
    with _failed_cache_lock:
        if host in _failed_dns_cache:
            raise socket.gaierror(-2, f"Name or service not known (cached negative lookup for {host})")

    # 3. Try original system/local DNS resolver
    try:
        res = _original_getaddrinfo(host, port, family, type, proto, flags)
        with _dns_cache_lock:
            _dns_cache[cache_key] = res
        return res
    except socket.gaierror as e:
        # 4. Fallback to DNS-over-HTTPS (DoH)
        import os
        disable_doh = os.environ.get("SCRAPER_DISABLE_DOH") == "1"

        ip = None
        if not disable_doh:
            # Always try DoH on failure — especially in scale mode where local DNS
            # gets throttled under 20 concurrent threads hitting it simultaneously.
            ip = doh_resolve(host)
            
        if ip:
            try:
                # Use original getaddrinfo to construct correct socket structures for the IP
                res = _original_getaddrinfo(ip, port, family, type, proto, flags)
                with _dns_cache_lock:
                    _dns_cache[cache_key] = res
                print(f"[DNS] Local resolve failed for {host}. Fallback resolved to {ip} via DoH.", file=sys.stderr)
                return res
            except Exception:
                pass

        # 5. Negative caching: Remember the failure to avoid spamming DoH queries
        with _failed_cache_lock:
            _failed_dns_cache[host] = True
        raise e

# Inject monkey-patch globally
socket.getaddrinfo = custom_getaddrinfo
