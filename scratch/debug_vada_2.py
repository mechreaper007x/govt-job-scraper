# scratch/debug_vada_2.py
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.filters import classify

if __name__ == "__main__":
    res = classify(
        "DP variation 30m road cancellation,Preliminary Notification,Village Maneja , R.S/Block No. 181,182,234,235,236,237,237/1,238 and Village Makarpura , R.S/Block No. 48,53",
        link="https://vuda.co.in/download/priliminary_notification.pdf",
        org_key="muni_vada"
    )
    print(f"Classification Result: {res}")
