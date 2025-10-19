# 로컬 저장소

import os, json, uuid
from typing import Dict

STORAGE_DIR = os.getenv("STORAGE_DIR", "./data")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
REPORT_DIR = os.path.join(STORAGE_DIR, "reports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def save_upload(file_bytes: bytes, filename: str) -> str:
    doc_id = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{doc_id}_{filename}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    return doc_id, path

def save_report(doc_id: str, report: Dict) -> str:
    path = os.path.join(REPORT_DIR, f"{doc_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path

def load_report(doc_id: str) -> Dict:
    path = os.path.join(REPORT_DIR, f"{doc_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
