# scratch/test_glove_lfs.py
import requests

def test_lfs():
    # URL for LFS file on iwangjian/Sequence-Models
    url = "https://media.githubusercontent.com/media/iwangjian/Sequence-Models/master/4.%20Word%20Vector%20Representation/data/glove.6B.50d.txt"
    print("Testing connection to LFS mirror...")
    try:
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        print("Connected! Reading first few lines:")
        
        count = 0
        for line in r.iter_lines():
            if count >= 5:
                break
            text = line.decode('utf-8')
            parts = text.split()
            print(f"Line {count}: {parts[0]} -> Vector size: {len(parts[1:])}")
            count += 1
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_lfs()
