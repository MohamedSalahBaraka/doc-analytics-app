from flask import Flask, render_template, request, redirect, url_for
import os
from io import BytesIO
from pathlib import Path
from parsers.doc_parser import parse_document
from search import search_documents
from stats import get_statistics
from classify import MultiLevelClassifier
from datetime import datetime
import json

# Local storage setup
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

classifier = MultiLevelClassifier()
classifier.load_training_data()
classifier.train()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def list_local_files():
    files = []
    for item in Path(app.config['UPLOAD_FOLDER']).rglob('*'):
        if item.is_file():
            files.append(str(item.relative_to(app.config['UPLOAD_FOLDER'])))
    return files

def download_file_from_local(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'rb') as f:
        return f.read()

def get_file_metadata_local(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    stat = os.stat(filepath)
    return {
        'size': stat.st_size,
        'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M'),
        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
    }

def save_file_locally(file, filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file.save(filepath)

def load_logged_documents():
    documents = []
    if not os.path.exists("classified_log.json"):
        return documents

    with open("classified_log.json", encoding='utf-8') as f:
        for line in f:
            try:
                log = json.loads(line.strip())
                documents.append({
                    "filename": log.get("filename", "unknown"),
                    "metadata":log.get("metadata", {
                        "created":datetime.now().isoformat(),
                        "modified":datetime.now().isoformat(),
                        "size": 0
                    }),
                    "filetype": os.path.splitext(log.get("filename", "unknown"))[1][1:].upper(),
                    "content": log.get("text", ""),
                    "classification": log.get("predicted_label", "Unclassified")
                })
            except json.JSONDecodeError:
                continue
    return documents

@app.route('/download/<filename>')
def download_file(filename):
    file_content = download_file_from_local(filename)
    return file_content, 200, {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'application/octet-stream'
    }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("documents")
        for file in files:
            if file.filename == '':
                continue
                
            # Save file to local storage
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            save_file_locally(file, file.filename)

            # Process and classify the document
            file.seek(0)  # Rewind the file pointer
            file_bytes = file.read()
            file_obj = BytesIO(file_bytes)
            
            try:
                result = parse_document(file_obj, filename=file.filename)
                classification = classifier.classify(result["snippet"])

                log_entry = {
                    "filename": file.filename,
                    "text": result["content"][:500],  # keep this light
                    "predicted_label": classification,
                    "timestamp": datetime.now().isoformat(),
                     "metadata": {
                        "created":datetime.now().isoformat(),
                        "modified":datetime.now().isoformat(),
                        "size": len(file_bytes)
                    }
                }
                with open("classified_log.json", "a", encoding='utf-8') as log_file:
                    log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")

        return redirect(url_for("index"))

    # Load from classification log
    documents = load_logged_documents()
    stats = get_statistics(documents)
    return render_template("index.html", documents=documents, stats=stats)

@app.route("/search", methods=["POST"])
def search():
    keyword = request.form.get("keyword", "").strip()
    if not keyword:
        return redirect(url_for("index"))

    results = search_documents(keyword, app.config['UPLOAD_FOLDER'])
    stats = get_statistics(results)  # Make sure get_statistics can handle this format
    
    return render_template("index.html", 
                         documents=results, 
                         keyword=keyword, 
                         stats=stats)
@app.route("/retrain", methods=["POST"])
def retrain():
    classifier.load_training_data()
    classifier.train()
    return redirect(url_for("index"))

@app.route("/details/<filename>")
def document_details(filename):
    try:
        raw = download_file_from_local(filename)
    except Exception as e:
        print(f"Error loading file: {e}")
        return redirect(url_for("index"))

    doc = parse_document(BytesIO(raw))
    metadata = get_file_metadata_local(filename)
    doc.update({
        'filename': filename,
        'metadata': metadata,
        'filetype': os.path.splitext(filename)[1][1:].upper(),
        'classification': classifier.classify(doc['content'])
    })

    return render_template("details.html", document=doc)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
