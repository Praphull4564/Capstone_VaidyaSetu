import io
import json
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Request, Response, jsonify, render_template, request, stream_with_context
from werkzeug.exceptions import RequestEntityTooLarge

from services.image_handler import ImageValidationError, validate_image
from services.ollama_chat import OllamaChatError, chat_with_ollama, stream_chat_with_ollama

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY_MESSAGES = 20
MAX_CONVERSATIONS = 100


class InMemoryUploadRequest(Request):
    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        return io.BytesIO()


app = Flask(__name__)
app.request_class = InMemoryUploadRequest
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES + 256 * 1024
conversations = {}


@app.get("/")
def index():
    return render_template("index.html")


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    return _error_response("IMAGE_TOO_LARGE", "This image exceeds the maximum supported size of 8 MB.", 413)


@app.post("/api/vaidya-sathi/chat")
def chat():
    body = request.form if request.form else (request.get_json(silent=True) or {})
    message = str(body.get("message", "")).strip()
    conversation_id = str(body.get("conversationId", "")).strip()
    image = request.files.get("image")

    if len(message) > MAX_MESSAGE_LENGTH:
        return _error_response("MESSAGE_TOO_LONG", "Please shorten your message to 4,000 characters.", 413)
    if not message and image is None:
        return _error_response("EMPTY_MESSAGE", "Write a question or attach an image first.", 400)

    if not conversation_id or conversation_id not in conversations:
        conversation_id = secrets.token_urlsafe(16)
        if len(conversations) >= MAX_CONVERSATIONS:
            conversations.pop(next(iter(conversations)))
        conversations[conversation_id] = []

    image_payload = None
    image_notice = ""
    if image is not None:
        try:
            image_payload = validate_image(image.filename, image.stream.read(MAX_IMAGE_BYTES + 1))
        except ImageValidationError as error:
            return _error_response(error.code, error.message, error.status_code)
        if not os.getenv("OLLAMA_VISION_MODEL", "").strip():
            image_notice = "I can see that you attached an image, but the currently configured local model is text-only. I can't reliably interpret this image yet. Please configure a vision-capable Ollama model or describe what you need help with in text."

    user_content = message or "The user attached an image without a text question."
    conversations[conversation_id].append({"role": "user", "content": user_content})
    history = conversations[conversation_id][-MAX_HISTORY_MESSAGES:]

    if image_notice:
        conversations[conversation_id].append({"role": "assistant", "content": image_notice})
        return jsonify({
            "success": True,
            "conversationId": conversation_id,
            "message": {"role": "assistant", "content": image_notice},
            "imageSupported": False,
        })

    def generate_response():
        assistant_parts = []
        try:
            for chunk in stream_chat_with_ollama(
                history,
                base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                model=os.getenv("OLLAMA_MODEL", "vaidya-saransh"),
                vision_model=os.getenv("OLLAMA_VISION_MODEL", "").strip(),
                image=image_payload,
            ):
                assistant_parts.append(chunk)
                yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
            conversations[conversation_id].append({"role": "assistant", "content": "".join(assistant_parts)})
            yield json.dumps({"type": "done", "conversationId": conversation_id, "imageSupported": bool(os.getenv("OLLAMA_VISION_MODEL", "").strip())}) + "\n"
        except OllamaChatError as error:
            conversations[conversation_id].pop()
            yield json.dumps({"type": "error", "code": error.code, "message": error.message}) + "\n"

    return Response(stream_with_context(generate_response()), mimetype="application/x-ndjson")


@app.delete("/api/vaidya-sathi/conversations/<conversation_id>")
def delete_conversation(conversation_id):
    conversations.pop(conversation_id, None)
    return jsonify({"success": True})


def _error_response(code, message, status_code):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status_code


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5003")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )