````md
# Installation

## Prerequisites (Windows 11)
- Python 3.10+ (3.11 recommended)
- PowerShell or Windows Terminal
- VS Code (optional)
- Groq API key

## System Tools
### Tesseract OCR
- Install (recommended):
  - Installer: https://github.com/UB-Mannheim/tesseract/wiki
  - Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### Poppler (for scanned PDFs via pdf2image)
- Download prebuilt ZIP: https://github.com/oschwartz10612/poppler-windows/releases
- Extract to e.g. `C:\Tools\poppler\`
- Your Poppler **bin** folder must contain `pdftoppm.exe` and `pdfinfo.exe`, e.g.:
  - `C:\Tools\poppler\bin` or
  - `C:\Tools\poppler\Library\bin`

### (Optional) Java (for tabula-py)
- Install any JDK (e.g. Temurin/OpenJDK 17)

## Project Setup
```powershell
# clone or open your project folder
# cd path\to\your\project

# 1) Create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Upgrade pip
pip install --upgrade pip

# 3) Install Python deps
pip install -r requirements.txt
````

## Environment Variables (.env)

Create a file named `.env` in the project root:

```
GROQ_API_KEY=sk-REPLACE_WITH_YOUR_KEY
GROQ_MODEL=llama-3.3-70b-versatile

# Local tool paths (adjust to your machine)
POPPLER_PATH=C:\Tools\poppler\bin
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Run

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Open the Local URL shown in the terminal (e.g., [http://localhost:8501](http://localhost:8501)).

## Notes

* Ensure `POPPLER_PATH` points to the folder that contains `pdftoppm.exe` and `pdfinfo.exe`.
* If Tesseract isn’t on PATH, set `TESSERACT_PATH` as above.
* For scanned PDFs, enable **Force OCR** in the UI.

```
::contentReference[oaicite:0]{index=0}
```
