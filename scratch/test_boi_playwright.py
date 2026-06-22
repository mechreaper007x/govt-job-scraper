import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("."))

from scraper.spa_scraper import fetch_spa_page

url = "https://www.bankofindia.co.in/"
print(f"Fetching {url} using Playwright...")

html = fetch_spa_page(url, timeout_ms=30000)

print(f"HTML Length: {len(html)}")
if html:
    print("First 500 chars of HTML:")
    print(html[:500])
    
    # Check if "Just a moment" is in the page
    if "Just a moment" in html or "challenges.cloudflare" in html:
        print("FAIL: Cloudflare challenge page is still returned.")
    else:
        print("SUCCESS: Cloudflare challenge bypassed!")
else:
    print("FAIL: No HTML returned.")
