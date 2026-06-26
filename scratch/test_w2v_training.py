# scratch/test_w2v_training.py
import json
import os
import re
import math
import random

def tokenize(text):
    # Normalize and extract alphanumeric tokens
    return [w.strip() for w in re.split(r"[^a-zA-Z]", text.lower()) if len(w.strip()) > 1]

def train():
    json_path = "scraped_jobs.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Collect all titles
    titles = []
    for org_key, org_info in data.get("orgs", {}).items():
        for job in org_info.get("jobs", []):
            titles.append(job.get("title", ""))

    print(f"Loaded {len(titles)} job titles.")

    # Build vocabulary
    word_counts = {}
    tokenized_titles = []
    for title in titles:
        tokens = tokenize(title)
        tokenized_titles.append(tokens)
        for token in tokens:
            word_counts[token] = word_counts.get(token, 0) + 1

    # Keep words with frequency >= 2
    vocab = sorted([w for w, c in word_counts.items() if c >= 2])
    word_to_idx = {w: i for i, w in enumerate(vocab)}
    idx_to_word = {i: w for i, w in enumerate(vocab)}
    vocab_size = len(vocab)
    print(f"Vocabulary size: {vocab_size} (filtered from {len(word_counts)} words with freq >= 2)")

    if vocab_size == 0:
        print("Error: Empty vocabulary.")
        return

    # Skip-gram Parameters
    dim = 16
    window_size = 2
    neg_samples = 5
    epochs = 50
    init_lr = 0.025

    # Initialize weights randomly in [-0.5/dim, 0.5/dim]
    random.seed(42)
    W_in = [[(random.random() - 0.5) / dim for _ in range(dim)] for _ in range(vocab_size)]
    W_out = [[0.0 for _ in range(dim)] for _ in range(vocab_size)]

    # Generate training pairs (target_idx, context_idx)
    pairs = []
    for tokens in tokenized_titles:
        indices = [word_to_idx[t] for t in tokens if t in word_to_idx]
        for i, target in enumerate(indices):
            start = max(0, i - window_size)
            end = min(len(indices), i + window_size + 1)
            for j in range(start, end):
                if i != j:
                    pairs.append((target, indices[j]))

    print(f"Generated {len(pairs)} target-context pairs.")

    # Unigram table for negative sampling (with power of 3/4)
    power = 0.75
    sum_pow = sum(word_counts[idx_to_word[i]] ** power for i in range(vocab_size))
    unigram_table = []
    table_size = 1e6
    for i in range(vocab_size):
        c = word_counts[idx_to_word[i]]
        pct = (c ** power) / sum_pow
        unigram_table.extend([i] * int(pct * table_size))
    if not unigram_table:
        unigram_table = list(range(vocab_size))

    # Sigmoid function helper
    def sigmoid(x):
        if x > 6: return 1.0
        if x < -6: return 0.0
        return 1.0 / (1.0 + math.exp(-x))

    # Training Loop (SGD)
    for epoch in range(epochs):
        lr = init_lr * (1.0 - epoch / epochs)
        random.shuffle(pairs)
        
        loss = 0.0
        for target, context in pairs:
            # Positive sample
            v_t = W_in[target]
            v_c = W_out[context]
            
            # dot product
            dp = sum(x*y for x, y in zip(v_t, v_c))
            sig = sigmoid(dp)
            loss -= math.log(max(sig, 1e-9))
            
            g_t = [0.0] * dim
            g_c = [0.0] * dim
            
            # Gradients
            err = sig - 1.0
            for d in range(dim):
                g_t[d] += err * v_c[d]
                g_c[d] += err * v_t[d]
                
            # Update context vector
            for d in range(dim):
                W_out[context][d] -= lr * g_c[d]
                
            # Negative samples
            for _ in range(neg_samples):
                neg = random.choice(unigram_table)
                if neg == context or neg == target:
                    continue
                v_n = W_out[neg]
                dp_n = sum(x*y for x, y in zip(v_t, v_n))
                sig_n = sigmoid(dp_n)
                loss -= math.log(max(1.0 - sig_n, 1e-9))
                
                err_n = sig_n - 0.0
                g_n = [0.0] * dim
                for d in range(dim):
                    g_t[d] += err_n * v_n[d]
                    g_n[d] += err_n * v_t[d]
                    
                # Update negative context vector
                for d in range(dim):
                    W_out[neg][d] -= lr * g_n[d]
                    
            # Update target vector
            for d in range(dim):
                W_in[target][d] -= lr * g_t[d]

        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {loss:.4f}, lr: {lr:.5f}")

    # Helper to calculate cosine similarity
    def cosine_similarity(v1, v2):
        dot = sum(x*y for x, y in zip(v1, v2))
        norm1 = math.sqrt(sum(x*x for x in v1))
        norm2 = math.sqrt(sum(x*x for x in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    # Let's find top-5 similar words for some keywords
    test_words = ["computer", "programmer", "software", "development", "data", "engineer", "civil", "medical"]
    for word in test_words:
        if word not in word_to_idx:
            print(f"Word '{word}' not in vocabulary.")
            continue
        
        idx = word_to_idx[word]
        v = W_in[idx]
        
        sims = []
        for other_idx in range(vocab_size):
            if other_idx != idx:
                other_word = idx_to_word[other_idx]
                sim = cosine_similarity(v, W_in[other_idx])
                sims.append((other_word, sim))
        
        sims.sort(key=lambda x: x[1], reverse=True)
        print(f"\nMost similar words to '{word}':")
        for w, s in sims[:5]:
            print(f"  {w}: {s:.4f}")

if __name__ == "__main__":
    train()
