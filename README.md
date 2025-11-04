# Document AI — Extraction

A local Document AI pipeline built with Streamlit that extracts text, tables, and key-values from PDFs (scanned or digital), converts them into structured JSON, and generates insights using a Groq LLM via LangChain.

## Features
- Extract text from native and scanned PDFs (OCR with Tesseract + Poppler)
- Table extraction (tabula / camelot)
- Heuristic key-value extraction using regex and line heuristics
- LLM-based JSON generation and insights (Groq via LangChain)
- Export structured JSON and Excel (tables)
- Click-to-run UI with a human-readable outcome summary

## Main files
- `app.py` — Streamlit UI and pipeline orchestration  
- `ocr.py` — text extraction and OCR logic  
- `table_extractor.py` — table extraction utilities  
- `extractor.py` — key-value heuristics  
- `llm_client.py` — Groq + LangChain wrapper  
- `utils.py` — helper functions (save JSON/Excel)  
- `requirements.txt` — Python dependencies
