# scraper/download_embeddings.py
import urllib.request
import zipfile
import json
import os
import sys
import re

def get_vocabulary():
    # Read filters.py to extract keyword list variables
    filters_path = os.path.join(os.path.dirname(__file__), "filters.py")
    if not os.path.exists(filters_path):
        print(f"Error: {filters_path} not found.")
        return set()
        
    with open(filters_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Find list contents using regex
    vocab = set()
    lists_to_extract = ["CORE_CS_KEYWORDS", "OTHER_CS_KEYWORDS", "GENERIC_TECH_KEYWORDS", "EXCLUDE_KEYWORDS"]
    
    for list_name in lists_to_extract:
        match = re.search(rf"{list_name}\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            items_str = match.group(1)
            # Find all double/single quoted strings
            items = re.findall(r"['\"](.*?)['\"]", items_str)
            for item in items:
                # Normalize and split multi-word keywords (e.g. "computer science" -> "computer", "science")
                words = [w.strip() for w in re.split(r"[^a-zA-Z]", item.lower()) if len(w.strip()) > 1]
                vocab.update(words)
                
    # Add some common helper words that appear in titles
    helper_words = {
        "manager", "officer", "assistant", "director", "recruitment", "information",
        "project", "research", "fellow", "associate", "science", "technology",
        "computer", "engineering", "management", "technical", "candidate", "advertisement",
        "post", "grade", "level", "notification", "vacancy", "application", "contract",
        "temporary", "regular", "permanent", "online", "written", "test", "interview",
        "selection", "results", "marks", "admit", "card", "syllabus", "tips", "security",
        "national", "state", "internal", "public", "private", "developer", "programmer",
        "software", "data", "engineer", "specialist", "support", "staff", "attendant"
    }
    vocab.update(helper_words)
    return vocab

def download_and_filter():
    vocab = get_vocabulary()
    print(f"Extracted target vocabulary of {len(vocab)} words.")
    
    zip_url = "http://nlp.stanford.edu/data/glove.6B.zip"
    zip_path = os.path.join(os.path.dirname(__file__), "glove.6B.zip")
    txt_filename = "glove.6B.50d.txt"
    json_path = os.path.join(os.path.dirname(__file__), "word_embeddings.json")
    
    # Check if we already have it
    if os.path.exists(json_path):
        print(f"Embedding file already exists at {json_path}")
        return
        
    print(f"Downloading official Stanford GloVe ZIP (822 MB) from {zip_url}...")
    print("This may take 1-2 minutes depending on your internet connection...")
    
    try:
        # Download with simple progress reporting
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                sys.stdout.write(f"\rDownloading: {downloaded / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB ({percent:.1f}%)")
            else:
                sys.stdout.write(f"\rDownloading: {downloaded / (1024*1024):.2f} MB")
            sys.stdout.flush()
            
        urllib.request.urlretrieve(zip_url, zip_path, progress_hook)
        print("\nDownload complete. Extracting and filtering vectors...")
        
        embeddings = {}
        # Open ZIP and parse the 50d file directly from the stream
        with zipfile.ZipFile(zip_path) as z:
            if txt_filename not in z.namelist():
                print(f"Error: {txt_filename} not found in zip.")
                return
                
            with z.open(txt_filename) as f:
                # read line by line (f returns bytes)
                for line_bytes in f:
                    line = line_bytes.decode('utf-8')
                    parts = line.strip().split()
                    if not parts:
                        continue
                    word = parts[0]
                    if word in vocab:
                        vector = [float(x) for x in parts[1:]]
                        embeddings[word] = vector
                        
        print(f"Extraction complete! Found vectors for {len(embeddings)} / {len(vocab)} words.")
        
        # Save to JSON
        with open(json_path, "w", encoding="utf-8") as out:
            json.dump(embeddings, out, indent=2)
            
        print(f"Successfully saved filtered embeddings to {json_path} (~{os.path.getsize(json_path)/1024:.1f} KB).")
        
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        # Cleanup ZIP file
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print("Cleaned up temporary ZIP file.")

if __name__ == "__main__":
    download_and_filter()
