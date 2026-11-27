import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_PIXELS = 20_000_000
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MIME_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageValidationError(Exception):
    def __init__(self, code, message, status_code=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def validate_image(filename, content):
    extension = Path(filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ImageValidationError("UNSUPPORTED_IMAGE", "This image type is not supported. Please upload a JPG, JPEG, PNG, or WEBP.", 415)
    if not content:
        raise ImageValidationError("EMPTY_IMAGE", "The selected image is empty. Choose another image.")
    if len(content) > 8 * 1024 * 1024:
        raise ImageValidationError("IMAGE_TOO_LARGE", "This image exceeds the maximum supported size of 8 MB.", 413)

    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise ImageValidationError("INVALID_IMAGE", "This image could not be read. Please upload a clearer image.", 422) from error
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ImageValidationError("IMAGE_TOO_LARGE", "This image has too many pixels to process safely.", 413)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True)
    return {"content": output.getvalue(), "mime_type": "image/jpeg"}