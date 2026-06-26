# scratch/debug_classify.py
import sys
import os
import re

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.filters import (
    classify, CORE_CS_RE, OTHER_CS_RE, EXCLUDE_RE, GENERIC_TECH_RE,
    title_similarity_classifier, naive_bayes_classifier, tfidf_embedding_classifier
)

def debug_classify(title, org_key=""):
    t = f" {title.lower()} "
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
    
    print(f"\nDebugging: '{title}' (Clean: '{clean_title}')")
    
    # 1. EXCLUDE_RE check
    if EXCLUDE_RE.search(title):
        print("  -> Matched EXCLUDE_RE")
        return "excluded"
    else:
        print("  -> Did NOT match EXCLUDE_RE")
        
    # 2. CORE_CS_RE check
    if CORE_CS_RE.search(title):
        print("  -> Matched CORE_CS_RE")
        return "relevant"
    else:
        print("  -> Did NOT match CORE_CS_RE")
        
    # 3. OTHER_CS_RE check
    if OTHER_CS_RE.search(title):
        print("  -> Matched OTHER_CS_RE")
        return "relevant"
    else:
        print("  -> Did NOT match OTHER_CS_RE")
        
    # 4. Naive Bayes
    if naive_bayes_classifier.loaded:
        nb_rel, nb_excl = naive_bayes_classifier.predict(title)
        print(f"  -> Naive Bayes: rel={nb_rel}, excl={nb_excl}")
        if nb_rel is not None and nb_excl is not None:
            if nb_rel > nb_excl + 1.0:
                print("    -> Classified as relevant by Naive Bayes")
                return "relevant"
            elif nb_excl > nb_rel + 1.0:
                print("    -> Classified as excluded by Naive Bayes")
                return "excluded"
                
    # 5. TF-IDF Cosine similarity
    cse_sim, excl_sim = title_similarity_classifier.classify_title(title)
    print(f"  -> TF-IDF similarity: cse={cse_sim:.4f}, excl={excl_sim:.4f}")
    if cse_sim >= 0.25 and cse_sim > excl_sim:
        print("    -> Classified as relevant by TF-IDF Similarity")
        return "relevant"
    elif excl_sim >= 0.25 and excl_sim > cse_sim:
        print("    -> Classified as excluded by TF-IDF Similarity")
        return "excluded"
        
    # 6. Hybrid Word Embeddings
    if tfidf_embedding_classifier.loaded:
        emb_cs_sim, emb_excl_sim = tfidf_embedding_classifier.classify_title(title)
        print(f"  -> Hybrid Embeddings: cs={emb_cs_sim:.4f}, excl={emb_excl_sim:.4f}")
        if emb_cs_sim >= 0.55 and emb_cs_sim > emb_excl_sim + 0.12:
            print("    -> Classified as relevant by Hybrid Embeddings")
            return "relevant"
        elif emb_excl_sim >= 0.55 and emb_excl_sim > emb_cs_sim + 0.12:
            print("    -> Classified as excluded by Hybrid Embeddings")
            return "excluded"
            
    # 7. Generic Tech
    has_generic = bool(GENERIC_TECH_RE.search(title))
    print(f"  -> Has Generic Tech: {has_generic}")
    
    return "uncertain"

if __name__ == "__main__":
    debug_classify("Recruitment")
    debug_classify("Detailed Advertisement")
    debug_classify("Notice-3_Application Count")
    debug_classify("Notification")
