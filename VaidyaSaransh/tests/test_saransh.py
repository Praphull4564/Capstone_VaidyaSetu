import io
import json
import unittest
from unittest.mock import Mock, patch

import pymupdf

from app import app
from services.ollama_provider import OllamaProviderError, analyze_report
from services.report_extractor import (
    ReportExtractionError,
    extract_report_text,
)
from services.report_schema import REPORT_SCHEMA, validate_report


def valid_report():
    return {
        "reportInfo": {"reportType": "Blood test", "date": "", "patientInfo": ""},
        "overallSummary": "The report lists the values shown below.",
        "keyFindings": [{
            "parameter": "Hemoglobin",
            "value": "13.2",
            "unit": "g/dL",
            "referenceRange": "12-16 g/dL",
            "status": "normal",
            "simpleExplanation": "This is the oxygen-carrying protein measured in the report.",
        }],
        "importantObservations": [],
        "medicalTerms": [],
        "questionsForDoctor": [],
        "limitations": [],
    }


class ReportSchemaTests(unittest.TestCase):
    def test_accepts_valid_structured_result(self):
        self.assertEqual(validate_report(valid_report()), valid_report())

    def test_rejects_missing_required_field(self):
        result = valid_report()
        del result["overallSummary"]
        with self.assertRaises(ValueError):
            validate_report(result)

    def test_rejects_invalid_status(self):
        result = valid_report()
        result["keyFindings"][0]["status"] = "critical"
        with self.assertRaises(ValueError):
            validate_report(result)


class ExtractionTests(unittest.TestCase):
    def test_extracts_text_from_pdf_without_ocr(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "Complete blood count. Hemoglobin: 13.2 g/dL. Reference range: 12-16 g/dL.")
        content = document.tobytes()
        document.close()

        text, notes = extract_report_text("report.pdf", content)
        self.assertIn("Hemoglobin: 13.2", text)
        self.assertEqual(notes, [])

    def test_rejects_unsupported_file(self):
        with self.assertRaises(ReportExtractionError) as raised:
            extract_report_text("report.docx", b"not a report")
        self.assertEqual(raised.exception.code, "UNSUPPORTED_FILE")

    def test_rejects_mismatched_pdf_signature(self):
        with self.assertRaises(ReportExtractionError) as raised:
            extract_report_text("report.pdf", b"not a pdf")
        self.assertEqual(raised.exception.code, "UNREADABLE_REPORT")

    @patch("services.report_extractor.pytesseract.image_to_string", return_value="Scanned report with readable result values")
    def test_ocr_extracts_scanned_pdf(self, ocr):
        document = pymupdf.open()
        document.new_page()
        content = document.tobytes()
        document.close()

        text, notes = extract_report_text("scanned.pdf", content)
        self.assertIn("readable result values", text)
        self.assertTrue(any("OCR" in note for note in notes))
        ocr.assert_called_once()

    @patch("services.report_extractor.pytesseract.image_to_string", return_value="")
    def test_rejects_image_when_ocr_extracts_nothing(self, _ocr):
        from PIL import Image

        image = Image.new("RGB", (40, 40), "white")
        output = io.BytesIO()
        image.save(output, format="PNG")
        with self.assertRaises(ReportExtractionError) as raised:
            extract_report_text("blank.png", output.getvalue())
        self.assertEqual(raised.exception.code, "EMPTY_EXTRACTION")

    @patch("services.report_extractor.pytesseract.image_to_string", return_value="A readable medical report result 123 units")
    def test_ocr_extracts_text_from_jpeg(self, ocr):
        from PIL import Image

        image = Image.new("RGB", (40, 40), "white")
        output = io.BytesIO()
        image.save(output, format="JPEG")
        text, _notes = extract_report_text("report.jpg", output.getvalue())
        self.assertIn("readable medical report", text)
        ocr.assert_called_once()

    @patch("services.report_extractor.pytesseract.image_to_string", side_effect=__import__("pytesseract").TesseractNotFoundError())
    def test_reports_when_ocr_engine_is_not_installed(self, _ocr):
        from PIL import Image

        image = Image.new("RGB", (40, 40), "white")
        output = io.BytesIO()
        image.save(output, format="PNG")
        with self.assertRaises(ReportExtractionError) as raised:
            extract_report_text("report.png", output.getvalue())
        self.assertEqual(raised.exception.code, "OCR_NOT_INSTALLED")

    @patch("services.report_extractor.pytesseract.image_to_string", return_value="A readable medical report result 123 units")
    def test_ocr_extracts_text_from_png(self, ocr):
        from PIL import Image

        image = Image.new("RGB", (40, 40), "white")
        output = io.BytesIO()
        image.save(output, format="PNG")
        text, _notes = extract_report_text("report.png", output.getvalue())
        self.assertIn("readable medical report", text)
        ocr.assert_called_once()


class ApiTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"VaidyaSaransh", response.data)

    def test_rejects_missing_file(self):
        response = self.client.post("/api/vaidya-saransh/analyze", data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["code"], "MISSING_FILE")

    def test_rejects_unsupported_upload(self):
        response = self.client.post(
            "/api/vaidya-saransh/analyze",
            data={"report": (io.BytesIO(b"content"), "report.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json["error"]["code"], "UNSUPPORTED_FILE")

    def test_rejects_oversized_upload(self):
        from app import MAX_REPORT_BYTES

        response = self.client.post(
            "/api/vaidya-saransh/analyze",
            data={"report": (io.BytesIO(b"x" * (MAX_REPORT_BYTES + 1)), "report.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json["error"]["code"], "FILE_TOO_LARGE")

    def test_ai_failure_does_not_leak_provider_details(self):
        content = b"%PDF-1.4"
        with patch("app.extract_report_text", return_value=("Readable report content here", [])), \
             patch("app.analyze_report", side_effect=OllamaProviderError("OLLAMA_UNAVAILABLE", "Ollama is not reachable. Start Ollama and try again.", 503)):
            response = self.client.post(
                "/api/vaidya-saransh/analyze",
                data={"report": (io.BytesIO(content), "report.pdf")},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"Readable report content", response.data)

    def test_upload_returns_validated_analysis(self):
        with patch("app.extract_report_text", return_value=("Readable report content", ["OCR was used."])), \
             patch("app.analyze_report", return_value=valid_report()):
            response = self.client.post(
                "/api/vaidya-saransh/analyze",
                data={"report": (io.BytesIO(b"%PDF-1.4"), "report.pdf")},
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertIn("OCR was used.", response.json["data"]["limitations"])


class ProviderTests(unittest.TestCase):
    def test_sends_json_schema_and_validates_response(self):
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.json.return_value = {"message": {"role": "assistant", "content": json.dumps(valid_report())}}
        with patch("services.ollama_provider.requests.post", return_value=response) as post:
            result = analyze_report("Report text", base_url="http://127.0.0.1:11434", model="qwen2.5:7b")
        self.assertEqual(result["reportInfo"]["reportType"], "Blood test")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:11434/api/chat")
        self.assertFalse(post.call_args.kwargs["json"]["stream"])
        self.assertEqual(post.call_args.kwargs["json"]["format"], REPORT_SCHEMA)
        self.assertNotIn("Authorization", post.call_args.kwargs["headers"] if "headers" in post.call_args.kwargs else {})

    def test_maps_request_timeout(self):
        import requests

        with patch("services.ollama_provider.requests.post", side_effect=requests.Timeout):
            with self.assertRaises(OllamaProviderError) as raised:
                analyze_report("Report text")
        self.assertEqual(raised.exception.code, "AI_TIMEOUT")

    def test_maps_ollama_connection_error(self):
        import requests

        with patch("services.ollama_provider.requests.post", side_effect=requests.ConnectionError):
            with self.assertRaises(OllamaProviderError) as raised:
                analyze_report("Report text")
        self.assertEqual(raised.exception.code, "OLLAMA_UNAVAILABLE")
        self.assertEqual(raised.exception.status_code, 503)

    def test_missing_model_suggests_ollama_pull(self):
        response = Mock(status_code=404, ok=False)
        with patch("services.ollama_provider.requests.post", return_value=response):
            with self.assertRaises(OllamaProviderError) as raised:
                analyze_report("Report text", model="qwen2.5:7b")
        self.assertEqual(raised.exception.code, "MODEL_NOT_FOUND")
        self.assertIn("ollama pull qwen2.5:7b", raised.exception.message)

    def test_bundled_model_suggests_local_import_command(self):
        response = Mock(status_code=404, ok=False)
        with patch("services.ollama_provider.requests.post", return_value=response):
            with self.assertRaises(OllamaProviderError) as raised:
                analyze_report("Report text", model="vaidya-saransh")
        self.assertEqual(raised.exception.code, "MODEL_NOT_FOUND")
        self.assertIn("ollama create vaidya-saransh -f Modelfile", raised.exception.message)

    def test_rejects_invalid_json_output(self):
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.json.return_value = {"message": {"role": "assistant", "content": "not json"}}
        with patch("services.ollama_provider.requests.post", return_value=response):
            with self.assertRaises(OllamaProviderError) as raised:
                analyze_report("Report text")
        self.assertEqual(raised.exception.code, "INVALID_AI_RESPONSE")

    def test_maps_provider_rate_limit(self):
        response = Mock(status_code=429, ok=False)
        with patch("services.ollama_provider.requests.post", return_value=response):
            with self.assertRaises(OllamaProviderError) as raised:
                analyze_report("Report text")
        self.assertEqual(raised.exception.code, "MODEL_BUSY")


if __name__ == "__main__":
    unittest.main()