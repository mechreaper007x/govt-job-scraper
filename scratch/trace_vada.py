# scratch/trace_vada.py
import sys
import os
import re

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.filters import (
    classify, CORE_CS_RE, OTHER_CS_RE, EXCLUDE_RE, GENERIC_TECH_RE,
    title_similarity_classifier, naive_bayes_classifier, tfidf_embedding_classifier,
    CS_FIRST_ORGS, ORG_OVERRIDES, CS_URL_KEYWORDS, NON_CS_URL_KEYWORDS
)

def trace():
    title = "DP variation 30m road cancellation,Preliminary Notification,Village Maneja , R.S/Block No. 181,182,234,235,236,237,237/1,238 and Village Makarpura , R.S/Block No. 48,53"
    link = "https://vuda.co.in/download/priliminary_notification.pdf"
    org_key = "muni_vada"
    
    print("--- TRACING CLASSIFY ---")
    t = f" {title.lower()} "
    
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
    print(f"Title clean: '{clean_title}'")
    
    # Short check
    if len(clean_title) < 4:
        print("Layer 0: Short title exclusion")
        return
        
    # MB/KB check
    if re.search(r'\b\d+(\.\d+)?\s*(mb|kb)\b', t):
        print("Layer 0: Size exclusion")
        return
        
    # Common navigation exclusion
    if clean_title.lower() in ["careers"]:
        print("Layer 0: Navigation exclusion")
        return
        
    # Year check
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", t)]
    if link:
        years += [int(y) for y in re.findall(r"\b(20\d{2})\b", link.lower())]
    if years and max(years) < 2026:
        print("Layer 0: Expired year exclusion")
        return

    # NIELIT cleanup
    title_clean = re.sub(r'\bnielit\b', '', title, flags=re.IGNORECASE)
    title_clean = re.sub(r'national\s+institute\s+of\s+electronics\s+(&|and)\s+information\s+technology', '', title_clean, flags=re.IGNORECASE)
    print(f"Title clean for CS matching: '{title_clean}'")

    # Layer 1 exclusions
    if EXCLUDE_RE.search(title_clean):
        print("Layer 1: EXCLUDE_RE matches")
        return
    else:
        print("Layer 1: EXCLUDE_RE does NOT match")

    # Layer 1 core CS
    if CORE_CS_RE.search(title_clean):
        print("Layer 1: CORE_CS_RE matches")
        return
        
    # Layer 1 other CS
    if OTHER_CS_RE.search(title_clean):
        print("Layer 1: OTHER_CS_RE matches")
        return
        
    # Layer 1.5 Naive Bayes
    if naive_bayes_classifier.loaded:
        nb_rel, nb_excl = naive_bayes_classifier.predict(title_clean)
        print(f"Layer 1.5: Naive Bayes scores - rel: {nb_rel:.4f}, excl: {nb_excl:.4f}")
        if nb_rel > nb_excl + 1.0:
            print("Layer 1.5: Naive Bayes relevant")
            return
        elif nb_excl > nb_rel + 1.0:
            print("Layer 1.5: Naive Bayes excluded")
            return

    # Layer 1.6 TF-IDF similarity
    cse_sim, excl_sim = title_similarity_classifier.classify_title(title_clean)
    print(f"Layer 1.6: TF-IDF similarity - cse: {cse_sim:.4f}, excl: {excl_sim:.4f}")
    if cse_sim >= 0.25 and cse_sim > excl_sim:
        print("Layer 1.6: TF-IDF relevant")
        return
    elif excl_sim >= 0.25 and excl_sim > cse_sim:
        print("Layer 1.6: TF-IDF excluded")
        return

    # Layer 1.7 Hybrid embeddings
    if tfidf_embedding_classifier.loaded:
        emb_cs_sim, emb_excl_sim = tfidf_embedding_classifier.classify_title(title_clean)
        print(f"Layer 1.7: Embedding similarity - cs: {emb_cs_sim:.4f}, excl: {emb_excl_sim:.4f}")
        if emb_cs_sim >= 0.55 and emb_cs_sim > emb_excl_sim + 0.12:
            print("Layer 1.7: Embedding relevant")
            return
        elif emb_excl_sim >= 0.55 and emb_excl_sim > emb_cs_sim + 0.12:
            print("Layer 1.7: Embedding excluded")
            return

    # Layer 2 generic tech
    has_generic = bool(GENERIC_TECH_RE.search(title_clean))
    print(f"Layer 2: Has generic tech: {has_generic}")
    if has_generic and org_key in CS_FIRST_ORGS:
        print("Layer 2: CS_FIRST_ORG generic match -> relevant")
        return

    # Layer 2a overrides
    overrides = ORG_OVERRIDES.get(org_key, [])
    for pattern, classification in overrides:
        if pattern in t:
            print(f"Layer 2a: Org override matches pattern '{pattern}' -> {classification}")
            return
            
    if org_key in CS_FIRST_ORGS:
        print("Layer 2a: CS_FIRST_ORG default -> relevant")
        return

    # Layer 2b URL-aware
    if link:
        url_lower = link.lower()
        cs_url_hits = sum(1 for kw in CS_URL_KEYWORDS if kw in url_lower)
        non_cs_url_hits = sum(1 for kw in NON_CS_URL_KEYWORDS if kw in url_lower)
        print(f"Layer 2b: URL hits - cs: {cs_url_hits}, non_cs: {non_cs_url_hits}")
        if cs_url_hits >= 2:
            print("Layer 2b: URL relevance match -> relevant")
            return
        if non_cs_url_hits >= 1 and not CORE_CS_RE.search(title_clean):
            print("Layer 2b: URL exclude match -> excluded")
            return

    if has_generic:
        print("Fallback: generic fallback -> relevant")
        return
        
    print("Fallback default -> uncertain")

if __name__ == "__main__":
    trace()
