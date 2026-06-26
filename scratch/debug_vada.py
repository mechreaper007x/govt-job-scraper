# scratch/debug_vada.py
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scratch.debug_classify import debug_classify

if __name__ == "__main__":
    debug_classify("DP variation 30m road cancellation,Preliminary Notification,Village Maneja", org_key="vada")
