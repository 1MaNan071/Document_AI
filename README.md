# Document AI

A production-ready Document AI pipeline that extracts text, tables, and structured data from PDFs using AI. Deployed as a serverless app on **Vercel** with a clean web UI.

## Live Demo

Deploy your own instance in one click:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2F1MaNan071%2FDocument_AI&env=GROQ_API_KEY,GROQ_MODEL&envDescription=Get%20a%20free%20Groq%20API%20key%20at%20console.groq.com&envLink=https%3A%2F%2Fconsole.groq.com)

## Features

- **PDF text extraction** — pure-Python via pdfplumber (no system binaries needed)
- **Table detection** — automatic table extraction from digital PDFs
- **Heuristic key-value extraction** — regex + line-based pattern matching
- **AI-powered structuring** — Groq LLM (Llama 3.3 70B) turns raw text into structured JSON
- **Modern web UI** — drag-and-drop upload, real-time progress, downloadable results
- **Serverless** — runs on Vercel free tier, no servers to manage

## Architecture

```
api/index.py      → FastAPI serverless function (PDF processing + Groq LLM)
public/index.html → Static frontend (vanilla HTML/CSS/JS)
vercel.json       → Vercel deployment configuration
```

**Stack:** FastAPI · pdfplumber · Groq API (httpx) · Vanilla JS

## Getting Started

### Prerequisites

- Python 3.10+
- A free [Groq API key](https://console.groq.com)

### Local Development

```bash
# Clone
git clone https://github.com/1MaNan071/Document_AI.git
cd Document_AI

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run locally
uvicorn api.index:app --reload --port 8000
```

Then open [http://localhost:8000](http://localhost:8000) — the static files in `public/` are served by Vercel in production, so for local dev you can open `public/index.html` directly or use a simple file server.

### Deploy to Vercel

1. Push this repo to GitHub
2. Go to [vercel.com/new](https://vercel.com/new) and import the repo
3. Add environment variables:
   - `GROQ_API_KEY` — your Groq API key
   - `GROQ_MODEL` — `llama-3.3-70b-versatile` (default)
4. Click **Deploy**

## API Reference

### `POST /api/extract`

Upload a PDF and get structured JSON back.

**Form fields:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | File | required | PDF file (max 4.5 MB) |
| `temperature` | float | 0.0 | LLM temperature (0–1) |
| `max_tokens` | int | 1500 | Max LLM output tokens |
| `max_prompt_chars` | int | 40000 | Max chars sent to LLM |

**Response:**
```json
{
  "success": true,
  "page_count": 3,
  "tables_found": 1,
  "heuristic_fields": 5,
  "result": {
    "metadata": { "filename": "invoice.pdf", "page_count": 3 },
    "fields": { "invoice_no": { "value": "INV-001", "confidence": "high", "source": "text" } },
    "tables": [{ "name": "line_items", "columns": [...], "rows": [...] }],
    "insights": ["Document is a commercial invoice dated 2025-01-15"]
  }
}
```

### `GET /api/health`

Health check endpoint.

## Limitations

- **Scanned/image PDFs** are not supported in the cloud version (no OCR — Tesseract/Poppler can't run on Vercel)
- **Max file size:** 4.5 MB (Vercel request body limit)
- **Max function duration:** 60 seconds (Vercel Hobby plan)

## License

MIT
