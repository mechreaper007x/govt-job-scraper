# scratch/test_glove_raw.py
import requests

def test_raw():
    url = "https://raw.githubusercontent.com/iwangjian/Sequence-Models/master/4.%20Word%20Vector%20Representation/data/glove.6B.50d.txt"
    print("Testing connection to raw GitHub GloVe file...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        print("Connected successfully!")
        
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
    test_raw()
