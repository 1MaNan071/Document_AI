"""
Document AI — Serverless API
Extracts text, tables, and structured data from PDFs using Groq LLM.
Optimized for Vercel free-tier deployment.
"""

import csv
import io
import json
import os
import re
import tempfile
from pathlib import Path

import httpx
import pdfplumber
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_FILE_SIZE = 4_500_000  # ~4.5 MB (stay under Vercel's request body limit)

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="Document AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── PDF Processing (pure-Python, no system binaries) ────────────────────────


def extract_text(path: str) -> tuple[str, int]:
    """Return (full_text, page_count) from a digital PDF."""
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text()
            if t and t.strip():
                pages.append(t.strip())
    return "\n\n".join(pages), page_count


def extract_tables(path: str) -> dict[str, list[list[str]]]:
    """Extract tables using pdfplumber's built-in table detection."""
    result: dict[str, list[list[str]]] = {}
    idx = 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if table and len(table) > 1:
                    idx += 1
                    cleaned = [
                        [str(cell or "").strip() for cell in row] for row in table
                    ]
                    result[f"table_{idx}"] = cleaned
    return result


def tables_to_csv(tables: dict[str, list[list[str]]]) -> dict[str, str]:
    """Serialize table rows to CSV strings for the LLM prompt."""
    out: dict[str, str] = {}
    for name, rows in tables.items():
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        out[name] = buf.getvalue()
    return out


# ─── Heuristic key-value extraction ──────────────────────────────────────────

_KV_PATTERNS: dict[str, re.Pattern] = {
    "policy_no": re.compile(
        r"policy\s*(?:no|number)[:\s]*([A-Z0-9\-\/]+)", re.I
    ),
    "invoice_no": re.compile(
        r"invoice\s*(?:no|number|#)[:\s]*([A-Z0-9\-\/]+)", re.I
    ),
    "date": re.compile(r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b"),
    "total_amount": re.compile(
        r"(?:total|amount\s*due|grand\s*total)[:\s]*[\$£€]?([\d,]+\.?\d*)", re.I
    ),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"\+?\d[\d\s\-()]{7,}\d"),
    "name": re.compile(
        r"(?:name|customer|client|insured)[:\s]*([A-Z][A-Za-z\s\.\-]{2,40})", re.I
    ),
}


def heuristic_search(text: str) -> dict[str, str]:
    """Extract key-value pairs from text using line-splitting + regex."""
    kv: dict[str, str] = {}

    # 1. Line-based "Key: Value" extraction
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            left, right = line.split(":", 1)
            key = left.strip().lower()
            val = right.strip()
            if 0 < len(val) < 200 and 1 < len(key) < 50:
                kv[key] = val

    # 2. Regex-based extraction (overrides line-based)
    for key, pattern in _KV_PATTERNS.items():
        m = pattern.search(text)
        if m:
            kv[key] = (m.group(1).strip() if m.lastindex else m.group(0).strip())

    return kv


# ─── LLM via Groq REST API (no LangChain — lighter cold starts) ─────────────

_SYSTEM_PROMPT = """\
You are a Document AI JSON generator.
Given extracted text, tables, and heuristic key-values from a PDF, produce structured JSON.

Output schema (return ONLY this JSON, nothing else):
{
  "metadata": {"filename": "...", "page_count": <int>},
  "fields": {
    "<field_name>": {"value": "...", "confidence": "low|med|high", "source": "text|table|heuristic"}
  },
  "tables": [
    {"name": "...", "columns": ["..."], "rows": [["..."]], "detected_type": "payments|line_items|schedule|other"}
  ],
  "insights": ["concise bullet 1", "concise bullet 2"]
}

Rules:
- Return ONLY valid JSON — no markdown fences, no commentary.
- Extract every meaningful field you can find.
- Set confidence based on extraction clarity.
- Provide 3-8 actionable insights about the document content.
"""


async def call_groq(
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 1500,
) -> dict:
    """Call the Groq chat-completions endpoint directly."""
    if not GROQ_API_KEY:
        raise HTTPException(500, "GROQ_API_KEY is not configured on the server.")

    async with httpx.AsyncClient(timeout=55.0) as client:
        resp = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
        )

    if resp.status_code != 200:
        detail = resp.json().get("error", {}).get("message", resp.text)
        raise HTTPException(502, f"Groq API error: {detail}")

    content = resp.json()["choices"][0]["message"]["content"]

    # Parse JSON (should always work with response_format, but be safe)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {"raw_response": content}


# ─── API Routes ──────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": GROQ_MODEL,
        "api_configured": bool(GROQ_API_KEY),
    }


@app.post("/api/extract")
async def extract_document(
    file: UploadFile = File(...),
    temperature: float = Form(0.0),
    max_tokens: int = Form(1500),
    max_prompt_chars: int = Form(40000),
):
    """Upload a PDF → extract text + tables + heuristics → LLM → structured JSON."""

    # ── Validate ──────────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            f"File too large ({len(content) // 1024} KB). "
            f"Maximum is {MAX_FILE_SIZE // 1024} KB.",
        )

    # ── Write to temp file ────────────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(content)
        tmp.close()

        # 1. Extract text
        text, page_count = extract_text(tmp.name)
        if not text.strip():
            return JSONResponse(
                {
                    "success": False,
                    "error": (
                        "No text could be extracted. This PDF may be scanned or "
                        "image-based. The cloud version supports digital (text-based) "
                        "PDFs only."
                    ),
                },
                status_code=422,
            )

        # 2. Extract tables
        tables = extract_tables(tmp.name)
        tables_csv = tables_to_csv(tables)

        # 3. Heuristic KV extraction
        kv = heuristic_search(text)

        # 4. Truncate text for the prompt if needed
        truncated = len(text) > max_prompt_chars
        prompt_text = (
            text[:max_prompt_chars] + "\n\n...[TRUNCATED]" if truncated else text
        )

        # 5. Build prompt
        prompt_parts = [
            f"FILENAME: {file.filename}",
            f"PAGE COUNT: {page_count}",
            f"EXTRACTED TEXT ({len(prompt_text)} chars"
            f"{', truncated' if truncated else ''}):",
            prompt_text,
            "KEY-VALUE HEURISTICS:",
            json.dumps(kv, indent=2),
            "TABLES:",
        ]
        for name, csv_str in tables_csv.items():
            prompt_parts.append(f"### {name}\n{csv_str}")
        if not tables_csv:
            prompt_parts.append("(no tables detected)")

        prompt = "\n\n".join(prompt_parts)

        # 6. Call LLM
        result = await call_groq(
            prompt, temperature=temperature, max_tokens=max_tokens
        )

        return {
            "success": True,
            "text_length": len(text),
            "text_preview": text[:1000],
            "page_count": page_count,
            "tables_found": len(tables),
            "heuristic_fields": len(kv),
            "heuristics": kv,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Processing error: {exc}") from exc
    finally:
        os.unlink(tmp.name)


# ─── Static files (local dev only — Vercel serves root-level files automatically)

_root = Path(__file__).resolve().parent.parent
if (_root / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(_root), html=True), name="static")
