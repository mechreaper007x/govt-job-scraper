import os
# Force SCALE_CRAWL=1 to enable bypasses
os.environ["SCALE_CRAWL"] = "1"

import time
import socket
import requests
import scraper.dns_resolver
from scraper.crawler import GovJobCrawler
from scraper.domain_seeder import _dns_resolves

def test_dns_caching():
    print("\n=== Testing DNS Caching ===")
    dead_host = "invalid-dead-domain-xyz-123.gov.in"
    
    # First resolve: should trigger system DNS lookup and fail
    start = time.time()
    res1 = _dns_resolves(f"http://{dead_host}")
    t1 = time.time() - start
    print(f"First resolution (dead host): {res1} in {t1:.4f}s")
    
    # Second resolve: should hit negative cache instantly
    start = time.time()
    res2 = _dns_resolves(f"http://{dead_host}")
    t2 = time.time() - start
    print(f"Second resolution (dead host): {res2} in {t2:.4f}s")
    assert t2 < 0.05, f"Negative cache didn't hit fast enough: {t2}s"
    print("✓ DNS Negative caching test passed!")

def test_doh_bypass():
    print("\n=== Testing DoH Bypass ===")
    # Clear caches
    scraper.dns_resolver._failed_dns_cache.clear()
    
    # Run resolution of dead host while SCALE_CRAWL=1
    dead_host = "another-dead-domain-abc-789.nic.in"
    start = time.time()
    try:
        socket.getaddrinfo(dead_host, 80)
    except socket.gaierror:
        pass
    duration = time.time() - start
    # If DoH fallback was active, it would take > 6s. Since it is bypassed, it should take system timeout time only.
    print(f"Failed resolution with DoH bypass took: {duration:.4f}s")
    assert duration < 5.0, f"DoH fallback might not be bypassed. Took {duration}s"
    print("✓ DoH Bypass test passed!")

def test_dynamic_sld_rate_limiting():
    print("\n=== Testing Dynamic SLD Rate Limiting ===")
    crawler = GovJobCrawler()
    
    # First request to domain A
    start = time.time()
    try:
        pass
    except Exception:
        pass
        
    session = crawler.session
    
    url1 = "http://domain1.gov.in/jobs"
    url2 = "http://domain2.gov.in/jobs"
    
    class DummyResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        text = "dummy"
    
    def dummy_get(url, *args, **kwargs):
        return DummyResponse()
        
    session._html_cache.clear()
    session._sld_last_request_time.clear()
    
    class MockAdapter(requests.adapters.BaseAdapter):
        def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
            resp = requests.Response()
            resp.status_code = 200
            resp.url = request.url
            resp._content = b"<html><body>mock</body></html>"
            return resp
        def close(self):
            pass
            
    # Mount mock adapter
    session.mount("http://", MockAdapter())
    session.mount("https://", MockAdapter())
    
    # Now, let's request domain1.gov.in
    t0 = time.time()
    session.get("http://domain1.gov.in/jobs")
    t1 = time.time()
    print(f"Request 1 to domain1.gov.in took: {t1 - t0:.4f}s")
    
    # Request domain2.gov.in (different domain) - should be instant!
    t0 = time.time()
    session.get("http://domain2.gov.in/jobs")
    t2 = time.time()
    print(f"Request 2 to domain2.gov.in (different domain) took: {t2 - t0:.4f}s")
    assert t2 - t0 < 0.1, f"Second distinct domain request slept! Took {t2 - t0}s"
    
    # Request domain1.gov.in (same domain again) - should sleep to satisfy 0.1s rate limit!
    t0 = time.time()
    session.get("http://domain1.gov.in/jobs")
    t3 = time.time()
    print(f"Request 3 to domain1.gov.in (same domain again) took: {t3 - t0:.4f}s")
    assert t3 - t0 >= 0.08, f"Sequential request to same domain did not sleep! Took {t3 - t0}s"
    
    print("✓ Dynamic SLD Rate Limiting test passed!")

if __name__ == "__main__":
    test_dns_caching()
    test_doh_bypass()
    test_dynamic_sld_rate_limiting()
    print("\nAll tests passed successfully!")
