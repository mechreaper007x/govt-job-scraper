import requests
import io
import pypdf

def main():
    url = "https://ongcindia.com/documents/77751/2660534/retrired-officers190526.pdf/57110574-930f-4fc7-7356-910c8f243006"
    session = requests.Session()
    
    print("Fetching URL...")
    r = session.get(url, timeout=20, stream=True)
    r.raise_for_status()
    
    print("Content-Type:", r.headers.get("Content-Type"))
    
    # Read PDF bytes
    print("Reading content...")
    pdf_bytes = r.content[:5 * 1024 * 1024]
    print(f"Read {len(pdf_bytes)} bytes.")
    
    print("Parsing PDF...")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for i, page in enumerate(reader.pages):
        if i >= 3:
            break
        text += page.extract_text() or ""
        
    print(f"Extracted text length: {len(text)}")
    print("Snippet:", text[:200])

if __name__ == "__main__":
    main()
