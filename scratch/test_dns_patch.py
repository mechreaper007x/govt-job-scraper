import sys
import socket

# Add project root to path
sys.path.insert(0, r"c:\Users\Savyasachi Mishra\Desktop\Job scraper")

# Import the resolver which patches socket.getaddrinfo globally
import scraper.dns_resolver

# Test domains (both corrected and previously failing subdomains)
test_domains = [
    "karnataka.gov.in",
    "agriculture.karnataka.gov.in",
    "www.iiitbh.ac.in",          # Corrected IIIT Bhagalpur
    "iiitdwd.ac.in",             # Corrected IIIT Dharwad
    "www.iiitu.ac.in",           # Corrected IIIT Una
    "www.iiti.ac.in"             # Corrected IIT Indore
]

print(f"{'Domain':<35} | {'Resolves':<10} | {'IP':<15}")
print("-" * 70)

for domain in test_domains:
    try:
        addr = socket.getaddrinfo(domain, 80)
        ip = addr[0][4][0]
        print(f"{domain:<35} | True       | {ip}")
    except Exception as e:
        print(f"{domain:<35} | False      | {str(e)[:30]}")
