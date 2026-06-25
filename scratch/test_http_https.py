import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

urls = [
    "http://www.edudel.nic.in",
    "https://www.edudel.nic.in",
    "http://www.tn.gov.in",
    "https://www.tn.gov.in"
]

for url in urls:
    try:
        r = requests.get(url, timeout=5, verify=False, allow_redirects=True)
        print(f"GET {url:<30} -> Success! Code: {r.status_code}, Final URL: {r.url}")
    except Exception as e:
        print(f"GET {url:<30} -> Failed: {e}")
