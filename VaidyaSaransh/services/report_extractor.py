import io
import re
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pytesseract import TesseractNotFoundError

MAX_PDF_PAGES = 40
MAX_EXTRACTED_CHARACTERS = 100_000
MIN_READABLE_CHARACTERS = 12
MAX_IMAGE_PIXELS = 40_000_000


class ReportExtractionError(Exception):
    def __init__(self, code, message, status_code=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def extract_report_text(filename, content):
    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise ReportExtractionError(
            "UNSUPPORTED_FILE",
            "This file type is not supported. Please upload a PDF, JPG, JPEG, or PNG.",
            415,
        )

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise _unreadable()
        text, notes = _extract_pdf(content)
    else:
        expected = b"\x89PNG\r\n\x1a\n" if extension == ".png" else b"\xff\xd8\xff"
        if not content.startswith(expected):
            raise _unreadable()
        text = _extract_image(content)
        notes = []

    normalized = _normalize_text(text)
    if len(re.sub(r"\s", "", normalized)) < MIN_READABLE_CHARACTERS:
        raise ReportExtractionError(
            "EMPTY_EXTRACTION",
            "No readable medical information was found in this document.",
            422,
        )
    if len(normalized) > MAX_EXTRACTED_CHARACTERS:
        raise ReportExtractionError(
            "REPORT_TOO_LONG",
            "This report contains too much text to analyze in one request. Upload a shorter report.",
            413,
        )
    return normalized, notes


def _extract_pdf(content):
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        if reader.is_encrypted:
            raise ReportExtractionError(
                "ENCRYPTED_PDF",
                "This PDF is password-protected. Upload an unlocked copy of the report.",
                422,
            )
        if not reader.pages:
            raise _unreadable()
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ReportExtractionError(
                "TOO_MANY_PAGES",
                f"This report has more than {MAX_PDF_PAGES} pages. Upload a shorter report.",
                413,
            )

        render_document = pymupdf.open(stream=content, filetype="pdf")
        pages = []
        used_ocr = False
        for index, pdf_page in enumerate(reader.pages):
            page_text = pdf_page.extract_text() or ""
            if len(re.sub(r"\s", "", page_text)) < MIN_READABLE_CHARACTERS:
                try:
                    pixmap = render_document[index].get_pixmap(
                        matrix=pymupdf.Matrix(2, 2), alpha=False
                    )
                    page_image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                    page_text = pytesseract.image_to_string(page_image, lang="eng")
                    used_ocr = True
                except TesseractNotFoundError as error:
                    raise _ocr_unavailable() from error
                except Exception as error:
                    raise _unreadable() from error
            pages.append(page_text)
        render_document.close()
    except ReportExtractionError:
        raise
    except Exception as error:
        raise _unreadable() from error

    notes = ["Some pages required OCR; extracted text may contain recognition errors."] if used_ocr else []
    return "\n\n".join(pages), notes


def _extract_image(content):
    try:
        image = Image.open(io.BytesIO(content))
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ReportExtractionError(
                "IMAGE_TOO_LARGE",
                "This image has too many pixels to process safely. Upload a smaller image.",
                413,
            )
        image.verify()
        image = Image.open(io.BytesIO(content)).convert("RGB")
        return pytesseract.image_to_string(image, lang="eng")
    except ReportExtractionError:
        raise
    except TesseractNotFoundError as error:
        raise _ocr_unavailable() from error
    except (UnidentifiedImageError, OSError) as error:
        raise _unreadable() from error
    except Exception as error:
        raise _unreadable() from error


def _normalize_text(text):
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", text).strip()


def _unreadable():
    return ReportExtractionError(
        "UNREADABLE_REPORT",
        "We couldn't reliably read this report. Please upload a clearer copy.",
        422,
    )


def _ocr_unavailable():
    return ReportExtractionError(
        "OCR_NOT_INSTALLED",
        "This report needs OCR, but Tesseract is not installed. Install Tesseract OCR and restart VaidyaSaransh, or upload a text-based PDF.",
        503,
    )