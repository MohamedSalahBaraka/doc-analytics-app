import os
from pathlib import Path
from datetime import datetime
from io import BytesIO
from parsers.doc_parser import parse_document
import fitz  # pip install PyMuPDF
from docx import Document
from docx.shared import RGBColor
from time import time
def highlight_docx(input_path, output_path, keyword):
    doc = Document(input_path)
    for para in doc.paragraphs:
        if keyword.lower() in para.text.lower():
            for run in para.runs:
                if keyword.lower() in run.text.lower():
                    run.font.highlight_color = 3  # Yellow highlight
    doc.save(output_path)

def highlight_pdf(input_path, keyword):
    try:
        doc = fitz.open(input_path)
        keyword_lower = keyword.lower()

        for page in doc:
            text = page.get_text()
            if keyword_lower in text.lower():
                # Re-search using original casing for accurate highlights
                instances = page.search_for(keyword)  # case-sensitive
                if not instances:
                    # fallback: try matching lowercase manually
                    words = page.get_text("words")  # get individual words with positions
                    for w in words:
                        if w[4].lower() == keyword_lower:
                            rect = fitz.Rect(w[:4])
                            page.add_highlight_annot(rect).update()
                else:
                    for inst in instances:
                        page.add_highlight_annot(inst).update()

        doc.save(input_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
        return True
    except Exception as e:
        print(f"PDF highlight failed for {input_path}: {e}")
        return False


def search_documents(keyword, upload_folder="uploads"):
    results = []
    keyword_lower = keyword.lower()
    start_time = time()

    # Ensure the upload folder exists
    if not os.path.exists(upload_folder):
        return results

    # Search through all files in the upload folder
    for file_path in Path(upload_folder).rglob('*'):
        if file_path.is_file():
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    file_obj = BytesIO(file_content)
                    result = parse_document(file_obj, filename=file_path.name)
                    
                    content = result.get("content", "")
                    content_lower = content.lower()

                    if keyword_lower in content_lower:
                        index = content_lower.find(keyword_lower)

                        # Extract snippet with padding
                        start = max(index - 200, 0)
                        end = min(index + len(keyword) + 200, len(content))
                        snippet = content[start:end]

                        # Highlight the keyword
                        original_keyword = content[index:index+len(keyword)]
                        snippet = snippet.replace(
                            original_keyword,
                            f"<mark>{original_keyword}</mark>"
                        )

                        # Get file metadata
                        stat = file_path.stat()
                        metadata = {
                            "created": datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M'),
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                            "size": stat.st_size
                        }

                        results.append({
                            "filename": file_path.name,
                            "content": content,
                            "title": result['title'],
                            "classification": None,  # You can add classification if needed
                            "snippet": snippet,
                            "metadata": metadata,
                            "filetype": file_path.suffix[1:].upper() if file_path.suffix else "UNKNOWN"
                        })
                        if file_path.suffix.lower() == ".pdf":
                            highlight_pdf(file_path, keyword)
                        elif file_path.suffix.lower() == ".docx":
                            highlight_docx(file_path, file_path, keyword)


            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
    search_duration = round(time() - start_time, 2)
    return {
        "results": results,
        "search_time": search_duration
    }