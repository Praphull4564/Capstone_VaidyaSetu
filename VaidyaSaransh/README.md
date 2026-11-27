# VaidyaSaransh

Standalone Flask module for simplifying medical reports. It extracts report text in memory, sends it to a configured Ollama model, validates the response, and renders patient-friendly sections. Uploaded reports are not retained by this app.

## Requirements

- Python 3.10 or newer
- Ollama installed and running locally
- An Ollama model downloaded separately (model weights are not included in this repository)
- Tesseract OCR with English language data for scanned PDFs and images

Install Tesseract and ensure `tesseract.exe` is on `PATH`. Text-based PDFs do not need OCR; scanned PDFs and images do.

## Run locally (Windows PowerShell)

From the repository root:

```powershell
cd VaidyaSaransh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull llama3.1
```

The example `.env` uses `OLLAMA_MODEL=llama3.1`. If you choose a different compatible model, pull it with Ollama and set `OLLAMA_MODEL` in your private `.env` to its exact name. Start the app:

```powershell
python app.py
```

Open `http://127.0.0.1:5002`. With the default Ollama URL, report processing runs on the local computer. If `OLLAMA_BASE_URL` points to another host, report text is sent there.

## Processing and limitations

`POST /api/vaidya-saransh/analyze` accepts a multipart field named `report`. It checks the file extension and signature, enforces a 15 MB file limit and 40-page PDF limit, extracts PDF text, and uses Tesseract for scanned pages and images. OCR may misread values; verify explanations against the original report and discuss important findings with a qualified healthcare professional. This tool does not diagnose or recommend treatment.
