# ocr.py
import os
from pathlib import Path
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from dotenv import load_dotenv   # <-- add this

load_dotenv()

# Read optional paths from env
POPPLER_PATH = os.getenv("POPPLER_PATH", "").strip()  # e.g. C:\Tools\poppler\bin
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "").strip()  # e.g. C:\Program Files\Tesseract-OCR\tesseract.exe

# If Tesseract not on PATH, use the provided env path
if TESSERACT_PATH and Path(TESSERACT_PATH).exists():
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def _validate_poppler_dir(p: str) -> str:
    """
    Ensure POPPLER_PATH points to a directory that contains pdftoppm.exe and pdfinfo.exe.
    Return normalized string path to pass to pdf2image.
    """
    if not p:
        raise RuntimeError(
            "POPPLER_PATH is empty. Set it in .env to the Poppler 'bin' folder that contains "
            "pdftoppm.exe and pdfinfo.exe (e.g., C:\\Tools\\poppler\\bin)."
        )
    d = Path(p)
    if not d.exists() or not d.is_dir():
        raise RuntimeError(f"POPPLER_PATH does not exist or is not a directory: {p}")

    need = ["pdftoppm.exe", "pdfinfo.exe"]
    missing = [exe for exe in need if not (d / exe).exists()]
    if missing:
        raise RuntimeError(
            "POPPLER_PATH is set but required executables are missing.\n"
            f"POPPLER_PATH = {p}\n"
            f"Missing: {', '.join(missing)}\n"
            "Open your Poppler folder and locate the **bin** that contains these .exe files, "
            "then set POPPLER_PATH to that exact folder."
        )
    return str(d)

def extract_text_pdf(path: str) -> str:
    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n\n".join(text)

def ocr_image_pdf(path: str, dpi: int = 300) -> str:
    """
    Convert PDF pages to images using Poppler, then OCR with Tesseract.
    """
    kwargs = {"dpi": dpi}
    if POPPLER_PATH:
        # Validate and normalize only once
        normalized = _validate_poppler_dir(POPPLER_PATH)
        kwargs["poppler_path"] = normalized

    try:
        images = convert_from_path(path, **kwargs)
    except Exception as e:
        raise RuntimeError(
            "pdf2image could not run. Make sure Poppler is installed and accessible.\n"
            "Quick check:\n"
            f" - POPPLER_PATH={POPPLER_PATH or '(not set)'}\n"
            " - It must be the folder that contains pdftoppm.exe and pdfinfo.exe\n"
            "Fix:\n"
            " - If using a portable ZIP, point POPPLER_PATH to ...\\poppler\\bin (or ...\\Library\\bin)\n"
            " - If using Chocolatey shims, try POPPLER_PATH=C:\\ProgramData\\chocolatey\\bin\n"
            f"Original error: {e}"
        )

    texts = []
    for img in images:
        txt = pytesseract.image_to_string(img)
        texts.append(txt)
    return "\n\n".join(texts)

def extract(path: str, prefer_ocr: bool = False) -> str:
    """
    Prefer text extraction with pdfplumber; fallback to OCR if empty or if prefer_ocr=True.
    """
    text = ""
    if not prefer_ocr:
        try:
            text = extract_text_pdf(path)
        except Exception as e:
            print("pdfplumber text extraction error:", e)

    if prefer_ocr or not text.strip():
        text = ocr_image_pdf(path)

    return text
