# app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .storage import save_upload, load_report
from .pipeline import analyze_pdf
from .schemas import UploadResponse
from .schemas import Report
from .storage import UPLOAD_DIR
from .utils_pdf import pdf_to_pages

app = FastAPI(title="Contract Summary & Risk Detector (MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.post("/upload", response_model=Report)
async def upload(file: UploadFile = File(...)) -> Report:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "PDF만 지원합니다. (스캔본은 OCR 필요)")
    content = await file.read()
    doc_id, path = save_upload(content, file.filename)
    report = analyze_pdf(doc_id, path)
    return Report(**report)

@app.get("/report/{doc_id}")
async def get_report(doc_id: str):
    try:
        return load_report(doc_id)
    except FileNotFoundError:
        raise HTTPException(404, "리포트를 찾을 수 없습니다.")

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/debug/text/{doc_id}")
async def debug_text(doc_id: str, max_pages: int = 5):
    # 업로드된 원본에서 텍스트만 미리보기
    import glob, os, json
    matches = glob.glob(os.path.join(UPLOAD_DIR, f"{doc_id}_*.pdf"))
    if not matches:
        raise HTTPException(404, "원본 PDF를 찾을 수 없습니다.")
    pages = pdf_to_pages(matches[0], max_pages=max_pages)
    return {"pages": pages[:max_pages], "count": len(pages)}