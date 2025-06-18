import os
from pathlib import Path
from datetime import datetime
from io import BytesIO
from parsers.doc_parser import parse_document

def search_documents(keyword, upload_folder="uploads"):
    results = []
    keyword_lower = keyword.lower()

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
                            "classification": None,  # You can add classification if needed
                            "snippet": snippet,
                            "metadata": metadata,
                            "filetype": file_path.suffix[1:].upper() if file_path.suffix else "UNKNOWN"
                        })

            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue

    return results