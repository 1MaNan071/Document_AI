# extractor.py
import re

# simple examples; extend as needed
KV_PATTERNS = {
    "policy_no": re.compile(r"(policy\s*no[:\s]*)([A-Z0-9\-\/]+)", re.I),
    "premium": re.compile(r"(premium[:\s]*)([\d,\.]+)", re.I),
    "date": re.compile(r"(\b(?:\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4}|\d{4}\-\d{2}\-\d{2})\b)"),
    # add more patterns
}

def extract_key_values(text):
    kv = {}
    for k, patt in KV_PATTERNS.items():
        m = patt.search(text)
        if m:
            # often group 2 captures the value
            if m.lastindex and m.lastindex >= 2:
                kv[k] = m.group(2).strip()
            else:
                kv[k] = m.group(0).strip()
    return kv

def heuristic_search(text):
    # find lines that look like "Policy No: ABC123" etc
    lines = text.splitlines()
    kv = {}
    for line in lines:
        line = line.strip()
        if ":" in line:
            left, right = line.split(":", 1)
            key = left.lower()
            val = right.strip()
            if len(val) > 0 and len(key) < 40:
                kv[key] = val
    # merge with regex
    kv2 = extract_key_values(text)
    kv.update(kv2)
    return kv
