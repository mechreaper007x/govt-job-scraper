import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RobustGovAdapter(HTTPAdapter):
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
            assert_hostname=False,
        )

    def cert_verify(self, conn, url, verify, cert):
        super().cert_verify(conn, url, False, cert)

session = requests.Session()
session.mount("https://", RobustGovAdapter())

urls = [
    "http://www.edudel.nic.in",
    "https://www.edudel.nic.in",
    "http://www.tn.gov.in",
    "https://www.tn.gov.in"
]

for url in urls:
    try:
        r = session.get(url, timeout=5, verify=False, allow_redirects=True)
        print(f"GET {url:<30} -> Success! Code: {r.status_code}, Final URL: {r.url}")
    except Exception as e:
        print(f"GET {url:<30} -> Failed: {e}")
