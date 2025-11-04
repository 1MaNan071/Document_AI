# table_extractor.py
from pathlib import Path
import pandas as pd

def extract_tables_tabula(pdf_path, pages='all'):
    # tabula-py wrapper (depends on Java)
    import tabula
    dfs = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=True)
    # returns list of dfs
    result = {}
    for i, df in enumerate(dfs):
        result[f"table_{i+1}"] = df
    return result

def extract_tables_camelot(pdf_path, pages='1-end'):
    # camelot - requires conda or special install on windows
    import camelot
    tables = camelot.read_pdf(pdf_path, pages=pages)
    result = {}
    for i, table in enumerate(tables):
        result[f"table_{i+1}"] = table.df
    return result

def best_effort_table_extract(pdf_path):
    # try tabula first (simpler on windows)
    try:
        return extract_tables_tabula(pdf_path)
    except Exception as e:
        print("tabula failed:", e)
        try:
            return extract_tables_camelot(pdf_path)
        except Exception as e2:
            print("camelot failed:", e2)
            return {}
