from PyPDF2 import PdfReader
import docx
import os
from io import BytesIO
import magic  # You'll need to install python-magic (pip install python-magic)

def get_file_type(file_obj, filename=None):
    # First try to determine from filename
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ('.pdf', '.docx', '.txt'):
            return ext
    
    # Then try magic to detect from content
    try:
        file_obj.seek(0)
        header = file_obj.read(1024)
        file_obj.seek(0)
        
        mime = magic.from_buffer(header, mime=True)
        if mime == 'application/pdf':
            return '.pdf'
        elif mime in ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 
                     'application/msword'):
            return '.docx'
        elif mime == 'text/plain':
            return '.txt'
    except:
        pass
    
    return ''

def parse_document(file_obj, filename=None):
    text = ""
    title = None
    file_type = get_file_type(file_obj, filename)
    
    try:
        file_obj.seek(0)  # Ensure we're at the start
        
        if file_type == '.pdf':
            try:
                reader = PdfReader(file_obj)
                title = reader.metadata.title if reader.metadata else None
                for page in reader.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"
            except Exception as e:
                print(f"[PDF ERROR] {e}")
                
        elif file_type == '.docx':
            try:
                doc = docx.Document(file_obj)
                props = doc.core_properties
                title = props.title if props else None
                for para in doc.paragraphs:
                    text += para.text + "\n"
            except Exception as e:
                print(f"[DOCX ERROR] {e}")
                
        elif file_type == '.txt':
            try:
                text = file_obj.read().decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = file_obj.read().decode('latin-1')
                except Exception as e:
                    print(f"[TXT ERROR] {e}")
            except Exception as e:
                print(f"[TXT ERROR] {e}")
        
        # Fallback title from first line of content
        if not title and text.strip():
            title = text.split("\n")[0].strip()
            
    except Exception as e:
        print(f"[GENERAL ERROR] {e}")
    
    return {
        "filename": filename or getattr(file_obj, 'name', 'unknown'),
        "title": (title or "Untitled").strip(),
        "snippet": text[:300].strip(),
        "content": text,
        "classification": None
    }