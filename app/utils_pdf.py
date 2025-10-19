# -*- coding: utf-8 -*-
"""
pypdf + OCR 통합 버전
- 1차: pypdf로 페이지별 텍스트 추출
- 2차: 텍스트가 거의 없는 페이지에 한해 pdf2image로 렌더링 후 pytesseract OCR
- 출력: 정규화된 페이지별 텍스트 리스트
"""

import os
import re
import unicodedata
from typing import List, Optional

from pypdf import PdfReader
from pdf2image import convert_from_path
from PIL import Image
import pytesseract


# ----------------------------
# 환경 설정 (선택적)
# ----------------------------
POPPLER_PATH = os.getenv("POPPLER_PATH")  # e.g. r"C:\tools\poppler-24.02.0\Library\bin"
TESSERACT_CMD = os.getenv("TESSERACT_CMD")  # e.g. r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# OCR 언어 기본: 한국어+영어
OCR_LANG = os.getenv("OCR_LANG", "kor+eng")

# pypdf 텍스트 길이 기준 미만이면 OCR 시도
OCR_TRIGGER_LEN = int(os.getenv("OCR_TRIGGER_LEN", "25"))


# ----------------------------
# 유틸: 텍스트 정규화
# ----------------------------
def _normalize_ko(txt: str) -> str:
    """한글/기호 정규화 + 공백/줄바꿈 정리"""
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKC", txt)
    txt = txt.replace("\u00A0", " ")               # non-breaking space
    txt = re.sub(r"[ \t]+", " ", txt)              # 다중 공백 -> 한 칸
    txt = re.sub(r"\r\n?|\u2028|\u2029", "\n", txt)  # 개행 통일
    # 페이지 헤더/푸터 등 잡음 패턴을 원하면 여기에 추가
    return txt.strip()


# ----------------------------
# 유틸: PDF → 이미지 → OCR
# ----------------------------
def _ocr_pdf_pages(path: str, page_indices: List[int]) -> List[Optional[str]]:
    """
    지정한 page_indices에 대해 PDF 페이지를 이미지로 렌더링한 뒤 OCR 수행.
    반환: 각 page index에 대응하는 텍스트(또는 None)의 리스트(입력 순서 보장).
    """
    # convert_from_path는 page 번호를 1부터 받으므로 +1 보정
    if not page_indices:
        return []
    first = min(page_indices) + 1
    last = max(page_indices) + 1

    images = convert_from_path(
        path,
        first_page=first,
        last_page=last,
        poppler_path=POPPLER_PATH  # Windows에서는 필수로 지정하는 것을 권장
    )

    # convert_from_path는 first_page~last_page 범위를 모두 반환.
    # 우리가 원하는 index만 OCR 수행(중간 페이지도 함께 돌아오니 매핑 필요)
    result_map = {}
    for offset, img in enumerate(images):
        page_num = first + offset  # 1-based
        page_idx0 = page_num - 1   # 0-based
        if page_idx0 in page_indices:
            text = pytesseract.image_to_string(img, lang=OCR_LANG) or ""
            result_map[page_idx0] = _normalize_ko(text)

    # 입력 순서대로 반환
    return [result_map.get(i) for i in page_indices]


# ----------------------------
# 메인: PDF → 페이지 텍스트
# ----------------------------
def pdf_to_pages(path: str, max_pages: int = 100) -> List[str]:
    """
    1) pypdf로 텍스트 추출
    2) 텍스트가 거의 없는 페이지는 OCR로 재구성
    3) 정규화된 페이지 텍스트 리스트 반환
    """
    # 0) 암호/권한 처리 (빈 패스워드 열기 시도)
    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")  # 빈 비밀번호 시도
        except Exception as e:
            # 암호 해제 실패 시 빈 리스트 반환(상위에서 에러로 처리해도 됨)
            print(f"[WARN] 암호화 PDF 해제 실패: {e}")
            return []

    # 1) pypdf 1차 추출
    pages_raw: List[Optional[str]] = []
    num_pages = min(len(reader.pages), max_pages)
    for i in range(num_pages):
        try:
            txt = reader.pages[i].extract_text() or ""
        except Exception as e:
            print(f"[WARN] pypdf 추출 실패(page {i+1}): {e}")
            txt = ""
        pages_raw.append(txt)

    # 2) OCR 대상 선정
    ocr_targets = [i for i, txt in enumerate(pages_raw) if len(txt or "") < OCR_TRIGGER_LEN]

    # 3) OCR 수행
    if ocr_targets:
        try:
            ocr_texts = _ocr_pdf_pages(path, ocr_targets)
            for idx, t in zip(ocr_targets, ocr_texts):
                if (t or "").strip():
                    pages_raw[idx] = t
        except Exception as e:
            print(f"[WARN] OCR 수행 실패: {e}")

    # 4) 최종 정규화 + 빈 페이지 제거(필요시)
    pages = []
    for txt in pages_raw:
        norm = _normalize_ko(txt or "")
        # 빈 페이지라도 리포트에 페이지 수를 맞추고 싶다면 append("")로 유지 가능
        if norm:
            pages.append(norm)

    return pages
