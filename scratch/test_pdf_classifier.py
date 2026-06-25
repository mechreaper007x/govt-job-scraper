import os
import sys
import unittest.mock

# Reconfigure stdout to use UTF-8 on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path to import scraper modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from scraper.filters import _classify_by_pdf, _PDF_CACHE_DIR

def run_tests():
    if not os.path.exists(_PDF_CACHE_DIR):
        print(f"Cache directory {_PDF_CACHE_DIR} does not exist.")
        return
        
    files = [f for f in os.listdir(_PDF_CACHE_DIR) if f.endswith(".txt")]
    print(f"Analyzing {len(files)} cached PDF text files using scraper.filters._classify_by_pdf...")
    
    relevant_cnt = 0
    excluded_cnt = 0
    
    for filename in files[:40]:  # check first 40 files
        path = os.path.join(_PDF_CACHE_DIR, filename)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            cached_text = f.read()
            
        # Mock _extract_pdf_text to return the text of this specific file
        with unittest.mock.patch("scraper.filters._extract_pdf_text", return_value=cached_text):
            # Pass a dummy url that ends with .pdf; the mock will intercept the extraction call
            result = _classify_by_pdf("http://dummy.url/doc.pdf?id=" + filename, session="dummy")
            
        snippet = cached_text.replace("\n", " ")[:80].strip()
        print(f"File: {filename} -> {str(result).upper()}")
        print(f"  Snippet: {snippet}")
        print("-" * 60)
        
        if result == "relevant":
            relevant_cnt += 1
        else:
            excluded_cnt += 1
            
    print(f"Summary: Relevant = {relevant_cnt}, Excluded = {excluded_cnt}")

if __name__ == "__main__":
    run_tests()
