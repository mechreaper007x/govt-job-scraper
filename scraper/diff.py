# diff.py
# State tracking and item hash comparison logic

import json
import hashlib
import os

def generate_hash(title, link):
    """
    Generates a stable sha256 hash from posting title and link.
    """
    content = f"{title.strip()}{link.strip()}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def diff_and_update_state(scraped_data, state_file_path="state.json"):
    """
    Loads state, finds new postings for each successfully scraped org,
    updates state in memory, and writes it back to state.json.
    
    scraped_data: dict of org_key -> list of postings (e.g. {"cdac": [{"title": ..., "link": ...}], ...})
    Returns: dict of org_key -> list of new postings
    """
    # Load state.json
    state = {}
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {state_file_path} ({e}). Initializing empty state.")
            state = {}

    new_postings = {}
    state_changed = False

    for org_key, postings in scraped_data.items():
        # If postings is None or not a list (e.g. SERVER_DOWN), the scraper failed or was skipped.
        # We skip updates to its state so we check it again next time.
        if postings is None or not isinstance(postings, list):
            continue

        known_hashes = set(state.get(org_key, []))
        current_hashes = []
        org_new_postings = []

        for post in postings:
            p_hash = generate_hash(post["title"], post["link"])
            current_hashes.append(p_hash)
            if p_hash not in known_hashes:
                org_new_postings.append(post)

        if org_new_postings:
            new_postings[org_key] = org_new_postings

        # Always update state to match current live page postings
        # (even if no new postings, as old ones might have been removed)
        if set(state.get(org_key, [])) != set(current_hashes):
            state[org_key] = current_hashes
            state_changed = True

    # If changes were made, write updated state to disk
    if state_changed:
        try:
            with open(state_file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            print(f"Updated {state_file_path} successfully.")
        except Exception as e:
            print(f"Error saving updated state to {state_file_path}: {e}")

    return new_postings
