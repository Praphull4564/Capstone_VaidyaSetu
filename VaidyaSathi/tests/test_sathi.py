import io
import json
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from app import app, conversations
from services.image_handler import ImageValidationError, validate_image
from services.ollama_chat import OllamaChatError, chat_with_ollama


def stream_events(response):
    return [json.loads(line) for line in response.data.decode().splitlines() if line]


def make_png():
    image = Image.new("RGB", (20, 20), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class ImageTests(unittest.TestCase):
    def test_normalizes_supported_image(self):
        result = validate_image("photo.png", make_png())
        self.assertEqual(result["mime_type"], "image/jpeg")
        self.assertTrue(result["content"].startswith(b"\xff\xd8"))

    def test_rejects_unsupported_image(self):
        with self.assertRaises(ImageValidationError) as raised:
            validate_image("file.exe", b"bad")
        self.assertEqual(raised.exception.code, "UNSUPPORTED_IMAGE")


class ChatProviderTests(unittest.TestCase):
    def test_sends_text_history_to_ollama(self):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"message": {"content": "General information only."}}
        with patch("services.ollama_chat.requests.post", return_value=response) as post:
            result = chat_with_ollama([{"role": "user", "content": "I have a headache."}], "http://127.0.0.1:11434", "vaidya-saransh")
        self.assertEqual(result, "General information only.")
        payload = post.call_args.kwargs["json"]
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["model"], "vaidya-saransh")

    def test_maps_ollama_connection_failure(self):
        import requests

        with patch("services.ollama_chat.requests.post", side_effect=requests.ConnectionError):
            with self.assertRaises(OllamaChatError) as raised:
                chat_with_ollama([], "http://127.0.0.1:11434", "vaidya-saransh")
        self.assertEqual(raised.exception.code, "OLLAMA_UNAVAILABLE")


class ApiTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        conversations.clear()
        self.client = app.test_client()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"VaidyaSathi", response.data)

    @patch("app.stream_chat_with_ollama", side_effect=lambda *args, **kwargs: iter(["Some possible causes include tension", " or dehydration."]))
    def test_text_chat_preserves_follow_up_history(self, _chat):
        first = self.client.post("/api/vaidya-sathi/chat", data={"message": "I have a headache."})
        conversation_id = stream_events(first)[-1]["conversationId"]
        second = self.client.post("/api/vaidya-sathi/chat", data={"message": "Since yesterday.", "conversationId": conversation_id})
        self.assertEqual(second.status_code, 200)
        active_id = next(
            key for key, messages in conversations.items()
            if any(item["content"] == "Since yesterday." for item in messages)
        )
        active_messages = conversations[active_id]
        self.assertGreaterEqual(len(active_messages), 3)
        self.assertTrue(any(item["content"] == "I have a headache." for item in active_messages))
        self.assertIn(b'"type": "chunk"', second.data)
        self.assertIn(b'"type": "done"', second.data)
        self.assertEqual(_chat.call_args.args[0][-1]["content"], "Since yesterday.")

    def test_image_without_vision_model_is_honest(self):
        response = self.client.post("/api/vaidya-sathi/chat", data={"message": "What is this?", "image": (io.BytesIO(make_png()), "photo.png")}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text-only", response.json["message"]["content"])

    def test_empty_message_rejected(self):
        response = self.client.post("/api/vaidya-sathi/chat", data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["code"], "EMPTY_MESSAGE")

    def test_clear_conversation(self):
        response = self.client.post("/api/vaidya-sathi/chat", data={"message": "Hello"})
        conversation_id = stream_events(response)[-1]["conversationId"]
        deleted = self.client.delete(f"/api/vaidya-sathi/conversations/{conversation_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertNotIn(conversation_id, conversations)


if __name__ == "__main__":
    unittest.main()