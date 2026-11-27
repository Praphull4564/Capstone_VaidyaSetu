import io
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Request, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from services.ollama_provider import OllamaProviderError, analyze_report
from services.report_extractor import ReportExtractionError, extract_report_text

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MAX_REPORT_BYTES = 15 * 1024 * 1024


class InMemoryUploadRequest(Request):
    def _get_file_stream(
        self,
        total_content_length,
        content_type,
        filename=None,
        content_length=None,
    ):
        return io.BytesIO()


app = Flask(__name__)
app.request_class = InMemoryUploadRequest
app.config["MAX_CONTENT_LENGTH"] = MAX_REPORT_BYTES + 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    return jsonify({
        "success": False,
        "error": {
            "code": "FILE_TOO_LARGE",
            "message": "This report exceeds the maximum supported file size of 15 MB.",
        },
    }), 413


@app.post("/api/vaidya-saransh/analyze")
def analyze_uploaded_report():
    report = request.files.get("report")
    if report is None:
        return _error("MISSING_FILE", "Choose a medical report to upload.", 400)
    if not report.filename:
        return _error("MISSING_FILE", "Choose a medical report to upload.", 400)

    content = report.stream.read(MAX_REPORT_BYTES + 1)
    if not content:
        return _error("EMPTY_FILE", "The selected file is empty. Choose another report.", 400)
    if len(content) > MAX_REPORT_BYTES:
        return _error(
            "FILE_TOO_LARGE",
            "This report exceeds the maximum supported file size of 15 MB.",
            413,
        )

    try:
        extracted_text, extraction_notes = extract_report_text(report.filename, content)
    except ReportExtractionError as error:
        return _error(error.code, error.message, error.status_code)

    try:
        data = analyze_report(
            extracted_text,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=os.getenv("OLLAMA_MODEL", "vaidya-saransh"),
        )
    except OllamaProviderError as error:
        return _error(error.code, error.message, error.status_code)

    data["limitations"] = _merge_limitations(data["limitations"], extraction_notes)
    return jsonify({"success": True, "data": data})


def _merge_limitations(limitations, extraction_notes):
    merged = list(limitations)
    for note in extraction_notes:
        if note not in merged:
            merged.append(note)
    return merged


def _error(code, message, status_code):
    return jsonify({
        "success": False,
        "error": {"code": code, "message": message},
    }), status_code


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5002")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )