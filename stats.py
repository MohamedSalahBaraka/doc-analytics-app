import json
import os
from datetime import datetime
from collections import defaultdict

def get_statistics(log_file_or_documents='classified_log.json'):
    # Handle case when we receive a list of documents directly
    if isinstance(log_file_or_documents, list):
        entries = log_file_or_documents
    else:
        # Handle case when we receive a file path
        if not os.path.exists(log_file_or_documents):
            return {
                "total_files": 0,
                "total_size": 0,
                "avg_file_size": 0,
                "last_upload": None,
                "file_types": {},
                "size_distribution": {
                    "small": 0,
                    "medium": 0,
                    "large": 0
                }
            }

        entries = []
        with open(log_file_or_documents, encoding='utf-8') as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue

    if not entries:
        return {
            "total_files": 0,
            "total_size": 0,
            "avg_file_size": 0,
            "last_upload": None,
            "file_types": {},
            "size_distribution": {
                "small": 0,
                "medium": 0,
                "large": 0
            }
        }

    file_sizes = []
    valid_timestamps = []
    filenames = []
    
    for e in entries:
        # Handle both document formats (from file or from memory)
        if isinstance(e, dict):
            if 'text' in e:
                file_sizes.append(e["metadata"].get("size",0))
            elif 'content' in e:
                file_sizes.append(e["metadata"].get("size",0))
            
            timestamp = None
            if 'timestamp' in e:
                timestamp = e['timestamp']
            elif 'metadata' in e and 'created' in e['metadata']:
                timestamp = e['metadata']['created']
            
            if timestamp is not None:
                try:
                    # Try to parse the timestamp to ensure it's valid
                    datetime.fromisoformat(timestamp)
                    valid_timestamps.append(timestamp)
                except (ValueError, TypeError):
                    pass
            
            if 'filename' in e:
                filenames.append(e['filename'])
            elif 'name' in e:  # alternative field name
                filenames.append(e['name'])

    file_types = defaultdict(int)
    for fname in filenames:
        ext = os.path.splitext(fname)[1].lower()
        file_types[ext] += 1

    size_distribution = {"small": 0, "medium": 0, "large": 0}
    for size in file_sizes:
        if size < 100 * 1024:  # < 100KB
            size_distribution["small"] += 1
        elif size < 1024 * 1024:  # < 1MB
            size_distribution["medium"] += 1
        else:  # >= 1MB
            size_distribution["large"] += 1

    # Handle last_upload calculation safely
    last_upload = None
    if valid_timestamps:
        try:
            last_upload = max(valid_timestamps)
            last_upload = datetime.fromisoformat(last_upload).strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            last_upload = max(valid_timestamps)  # Keep original format if parsing fails
    print(file_sizes)
    return {
        "total_files": len(entries),
        "total_size": round(sum(file_sizes) / (1024 * 1024), 2) if file_sizes else 0,  # MB
        "avg_file_size": round(sum(file_sizes) / len(file_sizes) / 1024, 2) if file_sizes else 0,  # KB
        "last_upload": last_upload,
        "file_types": dict(file_types),
        "size_distribution": size_distribution,
        "largest_file": round(max(file_sizes) / (1024 * 1024), 2) if file_sizes else 0,  # MB
        "smallest_file": round(min(file_sizes) / 1024, 2) if file_sizes else 0,  # KB
        "median_file_size": round(sorted(file_sizes)[len(file_sizes)//2] / 1024, 2) if file_sizes else 0  # KB
    }