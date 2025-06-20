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

def load_logged_documents(sort_by='title', sort_order='asc'):
    documents = []
    if not os.path.exists("classified_log.json"):
        return documents

    with open("classified_log.json", encoding='utf-8') as f:
        for line in f:
            try:
                log = json.loads(line.strip())
                documents.append({
                    "filename": log.get("filename", "unknown"),
                    "title": log.get("title", "unknown"),
                    "metadata": log.get("metadata", {
                        "created": datetime.now().isoformat(),
                        "modified": datetime.now().isoformat(),
                        "size": 0
                    }),
                    "filetype": os.path.splitext(log.get("filename", "unknown"))[1][1:].upper(),
                    "content": log.get("text", ""),
                    "classification": log.get("predicted_label", "Unclassified")
                })
            except json.JSONDecodeError:
                continue

    # Sorting logic
    reverse_order = sort_order == 'desc'
    if sort_by == 'title':
        documents.sort(key=lambda x: x['title'].lower(), reverse=reverse_order)
    elif sort_by == 'filename':
        documents.sort(key=lambda x: x['filename'].lower(), reverse=reverse_order)
    elif sort_by == 'size':
        documents.sort(key=lambda x: x['metadata'].get('size', 0), reverse=reverse_order)
    elif sort_by == 'created':
        documents.sort(key=lambda x: x['metadata'].get('created', ''), reverse=reverse_order)
    elif sort_by == 'classification':
        documents.sort(key=lambda x: x['classification'].lower(), reverse=reverse_order)

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
                    "title": result["title"],
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
    sort_by = request.args.get('sort_by', 'title')
    sort_order = request.args.get('sort_order', 'asc')
    
    # Load from classification log with sorting
    documents = load_logged_documents(sort_by=sort_by, sort_order=sort_order)
    stats = get_statistics(documents)
    return render_template("index.html", documents=documents, stats=stats,
        sort_by=sort_by,
        sort_order=sort_order)

@app.route("/search", methods=["POST"])
def search():
    keyword = request.form.get("keyword", "").strip()
    if not keyword:
        return redirect(url_for("index"))

    # Get sorting parameters from request
    sort_by = request.args.get('sort_by', 'title')
    sort_order = request.args.get('sort_order', 'asc')
    
    results = search_documents(keyword, app.config['UPLOAD_FOLDER'])
    stats = get_statistics(results['results'])
    
    # Sort the results
    reverse_order = sort_order == 'desc'
    if sort_by == 'title':
        results['results'].sort(key=lambda x: x['title'].lower(), reverse=reverse_order)
    elif sort_by == 'filename':
        results['results'].sort(key=lambda x: x['filename'].lower(), reverse=reverse_order)
    elif sort_by == 'size':
        results['results'].sort(key=lambda x: x['metadata'].get('size', 0), reverse=reverse_order)
    elif sort_by == 'created':
        results['results'].sort(key=lambda x: x['metadata'].get('created', ''), reverse=reverse_order)
    elif sort_by == 'classification':
        results['results'].sort(key=lambda x: x['classification'].lower(), reverse=reverse_order)
    
    return render_template("index.html", 
                         documents=results['results'],
                         search_time=results['search_time'], 
                         keyword=keyword, 
                         stats=stats,
                         sort_by=sort_by,
                         sort_order=sort_order)
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
import json
import os

@app.route("/delete/<filename>", methods=["POST"])
def delete_document(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Remove the file if exists
    if os.path.exists(filepath):
        os.remove(filepath)

    # Remove from classified_log.json
    try:
        if os.path.exists("classified_log.json"):
            with open("classified_log.json", "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Filter out the document to delete
            updated_entries = []
            for line in lines:
                try:
                    entry = json.loads(line)
                    if entry.get("filename") != filename:
                        updated_entries.append(entry)
                except json.JSONDecodeError:
                    # Skip malformed lines or keep them? Here we skip
                    continue

            # Rewrite the file without the deleted document
            with open("classified_log.json", "w", encoding="utf-8") as f:
                for entry in updated_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Error updating classified_log.json: {e}")

    return redirect("/")  # or wherever you want
@app.route("/update/<filename>", methods=["GET", "POST"])
def update_document(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    if request.method == "POST":
        new_file = request.files.get("new_file")
        if not new_file or new_file.filename == '':
            return "No file selected", 400
        print(f"Updating file: {filename}, new file: {new_file.filename}")
        try:
            # Save the new file (overwrite existing)
            save_file_locally(new_file, filename)

            # Re-parse and classify
            new_file.seek(0)
            file_bytes = new_file.read()
            file_obj = BytesIO(file_bytes)

            result = parse_document(file_obj, filename=filename)
            classification = classifier.classify(result["snippet"])

            # Load all previous entries
            documents = load_logged_documents()

            # Update or insert the new entry
            updated_log = []
            found = False
            for doc in documents:
                if doc["filename"] == filename:
                    doc["text"] = result["content"][:500]
                    doc["title"] = result["title"]
                    doc["predicted_label"] = classification
                    doc["timestamp"] = datetime.now().isoformat()
                    doc["metadata"] = {
                        "created": doc.get("metadata", {}).get("created", datetime.now().isoformat()),
                        "modified": datetime.now().isoformat(),
                        "size": len(file_bytes),
                    }
                    found = True
                updated_log.append(doc)

            if not found:
                updated_log.append({
                    "filename": filename,
                    "text": result["content"][:500],
                    "title": result["title"],
                    "predicted_label": classification,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "created": datetime.now().isoformat(),
                        "modified": datetime.now().isoformat(),
                        "size": len(file_bytes),
                    }
                })

            # Rewrite the log
            with open("classified_log.json", "w", encoding='utf-8') as log_file:
                for entry in updated_log:
                    log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"Error updating file {filename}: {e}")
            return f"Failed to update document: {e}", 500

        return redirect(url_for("index"))

    return render_template("update.html", filename=filename)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
