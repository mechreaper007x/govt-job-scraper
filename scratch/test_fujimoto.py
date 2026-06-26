# scratch/test_fujimoto.py
import requests

def test_fujimoto():
    url = "https://raw.githubusercontent.com/stanleyfujimoto/glove-mirror/master/glove.6B.50d.txt"
    print("Testing connection to stanleyfujimoto GloVe mirror...")
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
    test_fujimoto()
