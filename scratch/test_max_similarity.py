# scratch/test_max_similarity.py
import json
import os
import math
import re

def test():
    embeddings_path = "scraper/word_embeddings.json"
    with open(embeddings_path, "r", encoding="utf-8") as f:
        embeddings = json.load(f)
        
    cse_vocab = {
        "computer", "software", "developer", "programmer", "php", "laravel",
        "python", "java", "database", "cyber", "security", "devops", "mca", "cse"
    }
    
    def cosine_similarity(v1, v2):
        dot = sum(x*y for x, y in zip(v1, v2))
        norm1 = math.sqrt(sum(x*x for x in v1))
        norm2 = math.sqrt(sum(x*x for x in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def max_word_similarity(title):
        words = [w.strip() for w in re.split(r"[^a-zA-Z]", title.lower()) if len(w.strip()) > 1]
        max_sim = 0.0
        best_word = ""
        best_cs_word = ""
        
        for w in words:
            if w in embeddings:
                for cs_w in cse_vocab:
                    if cs_w in embeddings:
                        sim = cosine_similarity(embeddings[w], embeddings[cs_w])
                        if sim > max_sim:
                            max_sim = sim
                            best_word = w
                            best_cs_word = cs_w
        return max_sim, best_word, best_cs_word

    titles = [
        "Web Coder",
        "Recruitment",
        "Detailed Advertisement",
        "Notice-3_Application Count",
        "Junior Developer (CSE)",
        "System Administrator",
        "Civil Engineer",
        "Staff Nurse"
    ]
    
    print("--- Max Word Similarity to CS Vocab ---")
    for title in titles:
        max_sim, best_w, cs_w = max_word_similarity(title)
        print(f"Title: '{title}'")
        print(f"  Max Sim: {max_sim:.4f} (word '{best_w}' vs '{cs_w}')")

if __name__ == "__main__":
    test()
