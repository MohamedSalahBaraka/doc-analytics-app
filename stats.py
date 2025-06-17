import json
import os
from datetime import datetime
from collections import defaultdict

def get_statistics(log_file='classified_log.json'):
    if not os.path.exists(log_file):
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
    with open(log_file, encoding='utf-8') as f:
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

    file_sizes = [len(e.get("text", "")) for e in entries]
    timestamps = [e.get("timestamp") for e in entries if "timestamp" in e]
    filenames = [e.get("filename", "unknown.unk") for e in entries]

    file_types = defaultdict(int)
    for fname in filenames:
        ext = os.path.splitext(fname)[1].lower()
        file_types[ext] += 1

    size_distribution = {"small": 0, "medium": 0, "large": 0}
    for size in file_sizes:
        if size < 100 * 1024:
            size_distribution["small"] += 1
        elif size < 1024 * 1024:
            size_distribution["medium"] += 1
        else:
            size_distribution["large"] += 1

    last_upload = max(timestamps, default=None)
    if last_upload:
        last_upload = datetime.fromisoformat(last_upload).strftime('%Y-%m-%d %H:%M')

    return {
        "total_files": len(entries),
        "total_size": round(sum(file_sizes) / (1024 * 1024), 2),  # MB
        "avg_file_size": round(sum(file_sizes) / len(file_sizes) / 1024, 2),  # KB
        "last_upload": last_upload,
        "file_types": dict(file_types),
        "size_distribution": size_distribution,
        "largest_file": round(max(file_sizes) / (1024 * 1024), 2),  # MB
        "smallest_file": round(min(file_sizes) / 1024, 2),  # KB
        "median_file_size": round(sorted(file_sizes)[len(file_sizes)//2] / 1024, 2)  # KB
    }
