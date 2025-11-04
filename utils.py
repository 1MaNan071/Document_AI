# utils.py
import os
import json
from pathlib import Path

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

def save_json(obj, filename="output.json"):
    p = OUTPUT_DIR / filename
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return str(p)

def save_excel(df_dict, filename="tables.xlsx"):
    # df_dict: dict of table_name -> pandas.DataFrame
    import pandas as pd
    p = OUTPUT_DIR / filename
    with pd.ExcelWriter(p) as writer:
        for name, df in df_dict.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return str(p)
