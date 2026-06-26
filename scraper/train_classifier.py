# scraper/train_classifier.py
import json
import os
import re
import math
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.filters import classify

def tokenize(text):
    # Normalize and extract alphanumeric tokens
    words = [w.strip() for w in re.split(r"[^a-zA-Z0-9]", text.lower()) if len(w.strip()) > 1]
    features = list(words)
    # Extract bigrams
    for i in range(len(words) - 1):
        features.append(f"{words[i]}_{words[i+1]}")
    return features

def train():
    json_path = "scraped_jobs.json"
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Please run a crawl first.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    orgs = data.get("orgs", {})
    
    # Collect training samples by running the confident rules (bootstrapping)
    pos_samples = []
    neg_samples = []
    
    print("Collecting and labeling training samples...")
    for org_key, org_info in orgs.items():
        for job in org_info.get("jobs", []):
            title = job.get("title", "")
            link = job.get("link", "")
            
            # Use current rule-based classify as our training labels
            label = classify(title, link=link, org_key=org_key, use_ml=False)
            
            if label == "relevant":
                pos_samples.append(title)
            else:
                neg_samples.append(title)

    # Balance the classes by undersampling the negative class to 2x the positive class
    import random
    random.seed(42)
    if len(neg_samples) > 2 * len(pos_samples):
        neg_samples = random.sample(neg_samples, 2 * len(pos_samples))

    print(f"Total training samples - Relevant: {len(pos_samples)}, Excluded: {len(neg_samples)}")

    # Count occurrences
    pos_counts = {}
    neg_counts = {}
    vocab = set()

    for title in pos_samples:
        features = tokenize(title)
        for feat in features:
            pos_counts[feat] = pos_counts.get(feat, 0) + 1
            vocab.add(feat)

    for title in neg_samples:
        features = tokenize(title)
        for feat in features:
            neg_counts[feat] = neg_counts.get(feat, 0) + 1
            vocab.add(feat)

    # Compute Naive Bayes parameters
    alpha = 1.0  # Laplace smoothing
    
    total_samples = len(pos_samples) + len(neg_samples)
    if total_samples == 0:
        print("Error: No training samples collected.")
        return

    # Class priors (priors are log-probabilities)
    prior_relevant = math.log((len(pos_samples) + alpha) / (total_samples + 2 * alpha))
    prior_excluded = math.log((len(neg_samples) + alpha) / (total_samples + 2 * alpha))

    # Conditional probabilities (log-likelihoods)
    total_pos_words = sum(pos_counts.values())
    total_neg_words = sum(neg_counts.values())
    vocab_size = len(vocab)

    log_likelihoods = {}
    for feat in vocab:
        pos_f = pos_counts.get(feat, 0)
        neg_f = neg_counts.get(feat, 0)
        
        # P(feat | relevant) and P(feat | excluded) with Laplace smoothing
        p_pos = (pos_f + alpha) / (total_pos_words + vocab_size * alpha)
        p_neg = (neg_f + alpha) / (total_neg_words + vocab_size * alpha)
        
        log_likelihoods[feat] = {
            "relevant": math.log(p_pos),
            "excluded": math.log(p_neg)
        }

    # Default out-of-vocabulary likelihoods (Laplace smoothed probabilities for unseen words)
    oov_pos = math.log(alpha / (total_pos_words + vocab_size * alpha))
    oov_neg = math.log(alpha / (total_neg_words + vocab_size * alpha))

    model = {
        "priors": {
            "relevant": prior_relevant,
            "excluded": prior_excluded
        },
        "oov": {
            "relevant": oov_pos,
            "excluded": oov_neg
        },
        "weights": log_likelihoods
    }

    model_path = os.path.join("scraper", "model_weights.json")
    with open(model_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)

    print(f"Successfully trained Naive Bayes classifier and wrote weights to {model_path}.")

if __name__ == "__main__":
    train()
