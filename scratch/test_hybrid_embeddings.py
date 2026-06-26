# scratch/test_hybrid_embeddings.py
import sys
import os
import math
import re
import json

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Implement a quick mock of the embedding classifier here to test thresholds
class TestEmbeddingClassifier:
    def __init__(self, embeddings_path):
        with open(embeddings_path, "r", encoding="utf-8") as f:
            self.embeddings = json.load(f)
            
        self.cse_vocab = {
            "computer", "software", "developer", "programmer", "php", "laravel",
            "python", "java", "database", "cyber", "security", "devops", "mca", "cse"
        }
        self.exclude_vocab = {
            "civil", "mechanical", "electrical", "chemical", "nurse",
            "medical", "doctor", "pharmacist", "driver", "clerk", "typist",
            "stenographer", "accountant", "accounts", "audit", "legal",
            "law", "hr", "admin", "helper", "cook", "apprentice",
            "surgeon", "physician", "radiologist", "hospital", "medic",
            "medics", "dentist", "geology", "geophysicist", "geophysics",
            "chemistry", "physics", "forester", "forestry",
            "biotechnology", "biotech", "biology", "toxicology", "draftsman"
        }
        
        self.cs_centroid = self._compute_profile_centroid(self.cse_vocab)
        self.exclude_centroid = self._compute_profile_centroid(self.exclude_vocab)

    def _tokenize(self, text):
        return [w.strip() for w in re.split(r"[^a-zA-Z]", text.lower()) if len(w.strip()) > 1]

    def _compute_profile_centroid(self, vocab_set):
        centroid = [0.0] * 50
        count = 0
        for word in vocab_set:
            if word in self.embeddings:
                vec = self.embeddings[word]
                for d in range(50):
                    centroid[d] += vec[d]
                count += 1
        if count > 0:
            centroid = [x / count for x in centroid]
        return centroid

    def cosine_similarity(self, v1, v2):
        if not v1 or not v2:
            return 0.0
        dot = sum(x*y for x, y in zip(v1, v2))
        norm1 = math.sqrt(sum(x*x for x in v1))
        norm2 = math.sqrt(sum(x*x for x in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def classify_title(self, title):
        tokens = self._tokenize(title)
        if not tokens:
            return 0.0, 0.0
            
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
            
        title_vec = [0.0] * 50
        total_weight = 0.0
        for token, freq in tf.items():
            if token in self.embeddings:
                vec = self.embeddings[token]
                weight = freq * (2.0 if (token in self.cse_vocab or token in self.exclude_vocab) else 1.0)
                for d in range(50):
                    title_vec[d] += vec[d] * weight
                total_weight += weight
                
        if total_weight == 0:
            return 0.0, 0.0
            
        title_vec = [x / total_weight for x in title_vec]
        cs_sim = self.cosine_similarity(title_vec, self.cs_centroid)
        exclude_sim = self.cosine_similarity(title_vec, self.exclude_centroid)
        return cs_sim, exclude_sim

def test():
    embeddings_path = "scraper/word_embeddings.json"
    if not os.path.exists(embeddings_path):
        print(f"Error: {embeddings_path} not found.")
        return

    classifier = TestEmbeddingClassifier(embeddings_path)
    
    print("--- Word to Word Cosine Similarities ---")
    word_pairs = [
        ("developer", "programmer"),
        ("computer", "software"),
        ("developer", "civil"),
        ("programmer", "nurse"),
        ("web", "app"),
        ("laravel", "php")
    ]
    for w1, w2 in word_pairs:
        if w1 in classifier.embeddings and w2 in classifier.embeddings:
            sim = classifier.cosine_similarity(classifier.embeddings[w1], classifier.embeddings[w2])
            print(f"  Similarity between '{w1}' and '{w2}': {sim:.4f}")
            
    print("\n--- Title Embedding Similarities ---")
    test_titles = [
        "Web Coder",
        "Junior Developer (CSE)",
        "Civil Overseer Grade II",
        "Administrative Assistant",
        "Project Engineer (Software)",
        "Staff Nurse",
        "System Administrator"
    ]
    for title in test_titles:
        cs, excl = classifier.classify_title(title)
        margin = cs - excl
        print(f"Title: {title}")
        print(f"  CS Sim: {cs:.4f} | Exclude Sim: {excl:.4f} | Margin: {margin:.4f}")

if __name__ == "__main__":
    test()
