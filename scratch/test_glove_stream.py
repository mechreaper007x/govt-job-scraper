# scratch/test_glove_stream.py
import requests
import gzip
import os
import sys

def test_stream():
    url = "https://github.com/uclnlp/inferbeddings/raw/master/data/glove/glove.6B.50d.txt.gz"
    target_words = {"computer", "software", "programmer", "civil", "developer", "science", "engineering"}
    
    temp_gz = "scratch/glove_temp.gz"
    
    print("Downloading GloVe embeddings via requests with 300s timeout...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, stream=True, timeout=300)
        r.raise_for_status()
        
        file_size = int(r.headers.get('content-length', 0))
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        
        downloaded = 0
        with open(temp_gz, 'wb') as out_file:
            for chunk in r.iter_content(chunk_size=1024*256):
                if chunk:
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / file_size) * 100 if file_size else 0
                    print(f"Downloaded: {downloaded / (1024*1024):.2f} MB ({percent:.1f}%)", end="\r")
                    sys.stdout.flush()
                    
        print("\nDownload complete. Decompressing and filtering...")
        
        embeddings = {}
        with gzip.open(temp_gz, 'rt', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                word = parts[0]
                if word in target_words:
                    vector = [float(x) for x in parts[1:]]
                    embeddings[word] = vector
                    print(f"Found word: '{word}' -> Vector length: {len(vector)}")
                    
        print(f"Extraction complete. Extracted vectors for {len(embeddings)} / {len(target_words)} target words.")
        for word in sorted(embeddings.keys()):
            sample_vals = [round(x, 4) for x in embeddings[word][:3]]
            print(f"  {word}: {sample_vals}...")
            
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        # Cleanup
        if os.path.exists(temp_gz):
            os.remove(temp_gz)
            print("Cleaned up temp file.")

if __name__ == "__main__":
    test_stream()
