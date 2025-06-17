import json
import os

def search_documents(keyword, log_file_path="classified_log.json"):
    results = []
    if not os.path.exists(log_file_path):
        return results

    keyword_lower = keyword.lower()

    with open(log_file_path, encoding='utf-8') as f:
        for line in f:
            try:
                log = json.loads(line.strip())
                content = log.get("text", "")
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

                    results.append({
                        "filename": log.get("filename", "unknown"),
                        "content": content,
                        "classification": log.get("predicted_label", "Unclassified"),
                        "snippet": snippet,
                        "metadata": {
                            "created": log.get("timestamp"),
                            "modified": log.get("timestamp"),
                            "size": len(content)
                        },
                        "filetype": os.path.splitext(log.get("filename", ""))[1][1:].upper(),
                    })

            except json.JSONDecodeError:
                continue

    return results
