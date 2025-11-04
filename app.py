# app.py — Click-to-Run + Downloads + Outcome Summary
import os
import json
import re
from pathlib import Path

import streamlit as st

from ocr import extract
from table_extractor import best_effort_table_extract
from extractor import heuristic_search
from llm_client import GroqLangChain
from utils import save_json, save_excel

# ---------- Page config ----------
st.set_page_config(page_title="📄 Document AI POC", layout="wide")
st.title("📄 Document AI — Extraction POC")

# ---------- Sidebar controls ----------
with st.sidebar:
    st.header("⚙️ Settings")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.1)
    max_tokens = st.number_input("Max tokens", min_value=256, max_value=4096, value=1500, step=64)
    prefer_ocr = st.checkbox("Force OCR (for scanned PDFs)", value=False)
    MAX_PROMPT_CHARS = st.number_input("Prompt char limit", min_value=5000, max_value=120000, value=40000, step=5000)
    st.caption("Tip: enable OCR for scanned/photographed PDFs.")

# ---------- File upload ----------
uploaded = st.file_uploader("📎 Upload a PDF (scanned or digital)", type=["pdf"], accept_multiple_files=False)

# Cache heavy steps so repeated runs (same file) are faster
@st.cache_data(show_spinner=False)
def cached_text_extract(path_str: str, prefer: bool) -> str:
    return extract(path_str, prefer_ocr=prefer) or ""

@st.cache_data(show_spinner=False)
def cached_table_extract(path_str: str):
    return best_effort_table_extract(path_str) or {}

# ---------- UI: Process button ----------
if uploaded:
    tmp_path = Path("temp_uploaded.pdf")
    tmp_path.write_bytes(uploaded.read())
    filename = getattr(uploaded, "name", str(tmp_path))

    st.success(f"✅ File ready: **{filename}**")
    run = st.button("▶️ Process Document", type="primary")

    if run:
        with st.status("Processing document…", expanded=False) as status:
            # Extract text
            status.update(label="Extracting text…")
            text = cached_text_extract(str(tmp_path), prefer_ocr)
            if len(text) > MAX_PROMPT_CHARS:
                text = text[:MAX_PROMPT_CHARS] + "\n\n...[TRUNCATED]"
            st.subheader("📝 Extracted Text (preview)")
            st.text_area("Text", text, height=250)

            # Extract tables
            status.update(label="Extracting tables…")
            tables = cached_table_extract(str(tmp_path))
            if tables:
                st.success(f"Found {len(tables)} table(s).")
                for name, df in tables.items():
                    with st.expander(f"Preview: {name}", expanded=False):
                        st.dataframe(df)
            else:
                st.warning("No tables found (or table extraction failed).")

            # Heuristic KV
            status.update(label="Heuristic key-value extraction…")
            kv = heuristic_search(text)
            with st.expander("Key-Value (heuristics)", expanded=False):
                st.json(kv)

            # Prompt
            status.update(label="Building LLM prompt…")
            prompt_parts = [
                "You are a JSON generator for Document AI. Input: a block of extracted text, a list of tables (as CSV) and key-value heuristics.",
                "Output: a JSON with keys:",
                "- metadata: {filename, page_count (if available)}",
                "- fields: {field_name: {value, confidence (low/med/high), source}}",
                "- tables: [{name, columns: [...], rows: [[...]], detected_table_type (payments/policy terms/etc)}]",
                "- insights: [short bullets summarizing important points, risks, compliance flags]",
                "Return only valid JSON. Do not add any commentary.",
                "---",
                f"FILENAME: {filename}",
                "EXTRACTED_TEXT:",
                text,
                "KEY_VALUE_HEURISTICS:",
                json.dumps(kv),
                "TABLES:"
            ]
            for name, df in tables.items():
                prompt_parts.append(f"### {name}")
                try:
                    prompt_parts.append(df.head(10).to_csv(index=False))
                except Exception:
                    prompt_parts.append(str(df))
            prompt_parts.append("\n\nReturn JSON.")
            prompt = "\n\n".join(prompt_parts)

            with st.expander("Prompt preview", expanded=False):
                st.code(prompt[:2000] + ("... (truncated)" if len(prompt) > 2000 else ""), language="text")

            # LLM call
            status.update(label="Invoking LLM…")
            try:
                llm = GroqLangChain(max_tokens=int(max_tokens), temperature=float(temperature))
                raw = llm.invoke(prompt)
                raw_response = (
                    getattr(raw, "content", None)
                    or getattr(raw, "text", None)
                    or (raw[0].content if hasattr(raw, "__iter__") and not isinstance(raw, (str, bytes)) else None)
                    or str(raw)
                )

                try:
                    parsed = json.loads(raw_response)
                except Exception:
                    m = re.search(r"\{.*\}", raw_response, re.S)
                    parsed = json.loads(m.group(0)) if m else {"llm_text": raw_response}

                st.subheader("✅ Structured JSON (from LLM)")
                st.json(parsed)

                # ✅ OUTCOME SUMMARY SECTION
                st.markdown("### 🧾 Outcome Summary")
                try:
                    meta = parsed.get("metadata", {})
                    fields = parsed.get("fields", {})
                    insights = parsed.get("insights", [])
                    parsed_tables = parsed.get("tables", [])

                    # Metadata metrics
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Filename", meta.get("filename", filename))
                    c2.metric("Pages", str(meta.get("page_count", "—")))
                    c3.metric("Fields Found", str(len(fields) if isinstance(fields, dict) else 0))

                    # Key Fields preview
                    if isinstance(fields, dict) and fields:
                        st.markdown("**Key Fields**")
                        colA, colB = st.columns(2)
                        for i, (k, v) in enumerate(list(fields.items())[:8]):
                            col = colA if i % 2 == 0 else colB
                            val = v.get("value") if isinstance(v, dict) else v
                            col.write(f"- **{k}**: {val}")

                    # First table from LLM
                    if isinstance(parsed_tables, list) and parsed_tables:
                        st.markdown("**Primary Structured Table**")
                        import pandas as pd
                        t0 = parsed_tables[0]
                        df_llm = pd.DataFrame(t0.get("rows", []), columns=t0.get("columns", []))
                        if not df_llm.empty:
                            st.dataframe(df_llm)

                    # Insights bullets
                    if isinstance(insights, list) and insights:
                        st.markdown("**Insights**")
                        for tip in insights[:10]:
                            st.write(f"• {tip}")

                except Exception:
                    st.caption("⚠️ Outcome summary unavailable for this document.")

                # Downloads
                json_path = save_json(parsed, filename="llm_output.json")
                st.success(f"Saved JSON → {json_path}")

                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        "⬇️ Download JSON (saved)",
                        data=open(json_path, "rb").read(),
                        file_name=Path(json_path).name,
                        mime="application/json",
                    )
                if tables:
                    xlsx_path = save_excel(tables, filename="tables_output.xlsx")
                    with dl2:
                        st.download_button(
                            "⬇️ Download Tables (Excel)",
                            data=open(xlsx_path, "rb").read(),
                            file_name=Path(xlsx_path).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )

                status.update(label="Done ✅", state="complete")

            except Exception as e:
                status.update(label="LLM failed", state="error")
                st.error(f"LLM call failed: {e}")
                st.text(str(e))

# ---------- Downloads section ----------
st.markdown("---")
st.subheader("📥 Downloads (saved in /outputs)")
outputs_dir = Path("outputs")
outputs_dir.mkdir(exist_ok=True)
files = sorted(outputs_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
if files:
    for f in files[:6]:
        col1, col2, col3 = st.columns([4, 2, 2])
        col1.write(f"**{f.name}** — {round(f.stat().st_size/1024, 1)} KB")
        col3.download_button("Download", open(f, "rb").read(), file_name=f.name)
else:
    st.caption("No saved files yet.")
