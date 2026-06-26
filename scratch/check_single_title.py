# scratch/check_single_title.py
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
    exclude_vocab = {
        "civil", "mechanical", "electrical", "chemical", "nurse",
        "medical", "doctor", "pharmacist", "driver", "clerk", "typist",
        "stenographer", "accountant", "accounts", "audit", "legal",
        "law", "hr", "admin", "helper", "cook", "apprentice",
        "surgeon", "physician", "radiologist", "hospital", "medic",
        "medics", "dentist", "geology", "geophysicist", "geophysics",
        "chemistry", "physics", "forester", "forestry",
        "biotechnology", "biotech", "biology", "toxicology", "draftsman"
    }
    
    def cosine_similarity(v1, v2):
        dot = sum(x*y for x, y in zip(v1, v2))
        norm1 = math.sqrt(sum(x*x for x in v1))
        norm2 = math.sqrt(sum(x*x for x in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def compute_centroid(vocab_set):
        centroid = [0.0] * 50
        count = 0
        for word in vocab_set:
            if word in embeddings:
                vec = embeddings[word]
                for d in range(50):
                    centroid[d] += vec[d]
                count += 1
        if count > 0:
            centroid = [x / count for x in centroid]
        return centroid

    cs_centroid = compute_centroid(cse_vocab)
    exclude_centroid = compute_centroid(exclude_vocab)

    def classify_title(title):
        words = [w.strip() for w in re.split(r"[^a-zA-Z]", title.lower()) if len(w.strip()) > 1]
        tf = {}
        for w in words:
            tf[w] = tf.get(w, 0) + 1
            
        title_vec = [0.0] * 50
        total_weight = 0.0
        for token, freq in tf.items():
            if token in embeddings:
                vec = embeddings[token]
                weight = freq * (2.0 if (token in cse_vocab or token in exclude_vocab) else 1.0)
                for d in range(50):
                    title_vec[d] += vec[d] * weight
                total_weight += weight
                
        if total_weight == 0:
            return 0.0, 0.0, []
            
        title_vec = [x / total_weight for x in title_vec]
        cs_sim = cosine_similarity(title_vec, cs_centroid)
        exclude_sim = cosine_similarity(title_vec, exclude_centroid)
        return cs_sim, exclude_sim, list(tf.keys())

    titles = ["Recruitment", "Detailed Advertisement", "Notice-3_Application Count", "Notification"]
    for t in titles:
        cs, excl, tokens = classify_title(t)
        print(f"Title: '{t}' | Tokens found in embeddings: {tokens}")
        print(f"  CS Sim: {cs:.4f} | Exclude Sim: {excl:.4f} | Margin: {(cs - excl):.4f}")

if __name__ == "__main__":
    test()
