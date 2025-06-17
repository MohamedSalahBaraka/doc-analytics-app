from PyPDF2 import PdfReader
import docx
import os

def extract_pdf_title(filepath):
    try:
        reader = PdfReader(filepath)
        return reader.metadata.title or None
    except:
        return None

def extract_docx_title(filepath):
    try:
        doc = docx.Document(filepath)
        props = doc.core_properties
        return props.title or None
    except:
        return None

def parse_document(filepath):
    text = ""
    title = None
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        title = extract_pdf_title(filepath)
        try:
            with open(filepath, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"
        except Exception as e:
            print(f"[ERROR] Failed to read PDF: {e}")

    elif ext == ".docx":
        title = extract_docx_title(filepath)
        try:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print(f"[ERROR] Failed to read DOCX: {e}")

    # Fallback title from first line of content
    if not title and text.strip():
        title = text.split("\n")[0]

    snippet = text[:300]
    return {
        "filename": os.path.basename(filepath),
        "title": (title or "Untitled").strip(),
        "snippet": snippet.strip(),
        "content": text,
        "classification": None
    }
