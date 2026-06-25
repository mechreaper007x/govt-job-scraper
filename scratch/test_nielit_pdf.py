import requests
import sys
import os

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scraper.filters import _classify_by_pdf, _extract_pdf_text

def main():
    url = "https://www.nielit.gov.in/Fileviewer?fileId=f/CLyGepHK/UNDQJyTi4rg=="
    session = requests.Session()
    
    print("Testing PDF extraction...")
    text = _extract_pdf_text(url, session)
    print(f"Extracted text length: {len(text)}")
    if text:
        print("Snippet:", text[:200].strip())
        
    result = _classify_by_pdf(url, session)
    print(f"Classification result: {result}")

if __name__ == "__main__":
    main()
