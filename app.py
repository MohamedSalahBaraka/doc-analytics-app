from flask import Flask, render_template, request, redirect, url_for
import os
import boto3
from io import BytesIO
from parsers.doc_parser import parse_document
from search import search_documents
from stats import get_statistics
from classify import MultiLevelClassifier
from datetime import datetime
import json

# AWS setup
S3_BUCKET = "your-s3-bucket-name"
S3_PREFIX = "uploads/"
AWS_ACCESS_KEY_ID = "your_access_key"
AWS_SECRET_ACCESS_KEY = "your_secret_key"
AWS_REGION = "your-region"
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

classifier = MultiLevelClassifier()
classifier.load_training_data()
classifier.train()

app = Flask(__name__)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def list_s3_files():
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    return [obj['Key'] for obj in response.get('Contents', []) if not obj['Key'].endswith("/")]

def download_file_from_s3(key):
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return obj['Body'].read()

def get_file_metadata_s3(key):
    obj = s3.head_object(Bucket=S3_BUCKET, Key=key)
    return {
        'size': obj['ContentLength'],
        'created': obj['LastModified'].strftime('%Y-%m-%d %H:%M'),
        'modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M'),
    }

def generate_presigned_url(filename):
    return s3.generate_presigned_url('get_object',
        Params={'Bucket': S3_BUCKET, 'Key': filename},
        ExpiresIn=3600)  # 1 hour
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
                    "metadata": {
                        "created": log.get("timestamp"),
                        "modified": log.get("timestamp"),
                        "size": len(log.get("text", ""))
                    },
                    "filetype": os.path.splitext(log.get("filename", "unknown"))[1][1:].upper(),
                    "content": log.get("text", ""),
                    "classification": log.get("predicted_label", "Unclassified")
                })
            except json.JSONDecodeError:
                continue
    return documents

@app.route('/download/<filename>')
def download_file(filename):
    return download_file_from_s3(filename)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("documents")
        for file in files:
            file_key = f"{S3_PREFIX}{file.filename}"
            s3.upload_fileobj(file, S3_BUCKET, file_key)

            content = file.read()
            result = parse_document(BytesIO(content))
            classification = classifier.classify(result["content"])

            log_entry = {
                "filename": file.filename,
                "text": result["content"][:500],  # keep this light
                "predicted_label": classification,
                "timestamp": datetime.now().isoformat()
            }
            with open("classified_log.json", "a", encoding='utf-8') as log_file:
                log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return redirect(url_for("index"))

    # 🟡 Load from classification log instead of S3
    documents = load_logged_documents()
    stats = get_statistics(documents)
    return render_template("index.html", documents=documents, stats=stats)

@app.route("/search", methods=["POST"])
def search():
    keyword = request.form.get("keyword", "").lower()
    documents = load_logged_documents()
    
    results = []
    for doc in documents:
        if keyword in doc["content"].lower():
            highlighted = doc["content"].replace(
                keyword, f"<mark>{keyword}</mark>"
            )
            doc["content"] = highlighted
            results.append(doc)

    stats = get_statistics(results)
    return render_template("index.html", documents=results, keyword=keyword, stats=stats)

@app.route("/retrain", methods=["POST"])
def retrain():
    classifier.load_training_data()
    classifier.train()
    return redirect(url_for("index"))

@app.route("/details/<filename>")
def document_details(filename):
    key = f"{S3_PREFIX}{filename}"
    try:
        raw = download_file_from_s3(key)
    except Exception:
        return redirect(url_for("index"))

    doc = parse_document(BytesIO(raw))
    metadata = get_file_metadata_s3(key)
    doc.update({
        'filename': filename,
        'metadata': metadata,
        'filetype': os.path.splitext(filename)[1][1:].upper(),
        'classification': classifier.classify(doc['content'])
    })

    return render_template("details.html", document=doc)

if __name__ == "__main__":
    app.run(debug=True)
