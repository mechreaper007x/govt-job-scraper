# scratch/trace_harassment.py
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scratch.trace_vada import trace

# Patch the title in trace function
import scratch.trace_vada
scratch.trace_vada.trace = lambda: None

def run_trace():
    title = "Notification of the Sexual Harassment of Women at Workplace"
    link = "https://example.com"
    org_key = "sk_industries"
    
    import re
    from scraper.filters import (
        classify, CORE_CS_RE, OTHER_CS_RE, EXCLUDE_RE, GENERIC_TECH_RE,
        title_similarity_classifier, naive_bayes_classifier, tfidf_embedding_classifier,
        CS_FIRST_ORGS, ORG_OVERRIDES, CS_URL_KEYWORDS, NON_CS_URL_KEYWORDS
    )
    
    print("--- TRACING HARASSMENT ---")
    t = f" {title.lower()} "
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
    
    # Year check
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", t)]
    if link:
        years += [int(y) for y in re.findall(r"\b(20\d{2})\b", link.lower())]
    if years and max(years) < 2026:
        print("Layer 0: Expired year exclusion")
        return

    title_clean = re.sub(r'\bnielit\b', '', title, flags=re.IGNORECASE)
    title_clean = re.sub(r'national\s+institute\s+of\s+electronics\s+(&|and)\s+information\s+technology', '', title_clean, flags=re.IGNORECASE)

    if EXCLUDE_RE.search(title_clean):
        print("Layer 1: EXCLUDE_RE matches")
        return
    else:
        print("Layer 1: EXCLUDE_RE does NOT match")

    if CORE_CS_RE.search(title_clean):
        print("Layer 1: CORE_CS_RE matches")
        return
        
    if OTHER_CS_RE.search(title_clean):
        print("Layer 1: OTHER_CS_RE matches")
        return
        
    if naive_bayes_classifier.loaded:
        nb_rel, nb_excl = naive_bayes_classifier.predict(title_clean)
        print(f"Layer 1.5: Naive Bayes scores - rel: {nb_rel:.4f}, excl: {nb_excl:.4f}")
        if nb_rel > nb_excl + 1.0:
            print("Layer 1.5: Naive Bayes relevant")
            return
        elif nb_excl > nb_rel + 1.0:
            print("Layer 1.5: Naive Bayes excluded")
            return

    cse_sim, excl_sim = title_similarity_classifier.classify_title(title_clean)
    print(f"Layer 1.6: TF-IDF similarity - cse: {cse_sim:.4f}, excl: {excl_sim:.4f}")
    if cse_sim >= 0.25 and cse_sim > excl_sim:
        print("Layer 1.6: TF-IDF relevant")
        return
    elif excl_sim >= 0.25 and excl_sim > cse_sim:
        print("Layer 1.6: TF-IDF excluded")
        return

    if tfidf_embedding_classifier.loaded:
        emb_cs_sim, emb_excl_sim = tfidf_embedding_classifier.classify_title(title_clean)
        print(f"Layer 1.7: Embedding similarity - cs: {emb_cs_sim:.4f}, excl: {emb_excl_sim:.4f}")
        if emb_cs_sim >= 0.55 and emb_cs_sim > emb_excl_sim + 0.12:
            print("Layer 1.7: Embedding relevant")
            return
        elif emb_excl_sim >= 0.55 and emb_excl_sim > emb_cs_sim + 0.12:
            print("Layer 1.7: Embedding excluded")
            return

    has_generic = bool(GENERIC_TECH_RE.search(title_clean))
    print(f"Layer 2: Has generic tech: {has_generic}")
    if has_generic and org_key in CS_FIRST_ORGS:
        print("Layer 2: CS_FIRST_ORG generic match -> relevant")
        return

    print("Fallback default -> uncertain")

if __name__ == "__main__":
    run_trace()
