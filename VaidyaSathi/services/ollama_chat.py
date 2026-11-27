import base64
import json
import os

import requests

SYSTEM_PROMPT = """You are VaidyaSathi, the AI Healthcare Assistant of VaidyaSetu.

Provide general healthcare information, help users understand health-related information, organize symptoms, explain medical terminology, and guide users toward appropriate professional healthcare support.

You are an AI assistant, NOT a doctor. Never claim a definitive diagnosis, prescribe medication, or recommend starting, stopping, increasing, decreasing, or substituting medication. Never invent medical information.

Distinguish between information provided by the user, general medical information, possible explanations, and situations requiring professional evaluation. For symptoms, ask only useful follow-up questions. Use possibilities such as 'Some possible causes include...' and never say 'You have...' as an independent diagnosis.

If an image is provided, describe only what can reasonably be observed. Do not diagnose from an image. If it is unclear, say so. For prescriptions or medicine labels, explain only visible information and do not modify instructions. For reports, preserve values and units and do not invent ranges; detailed simplification is available in VaidyaSaransh.

If the user describes severe difficulty breathing, severe chest pain, loss of consciousness, sudden severe neurological symptoms, uncontrolled bleeding, severe allergic reaction, serious poisoning, or suicidal/self-harm emergency, prioritize: 'Please seek urgent medical attention or contact local emergency services.' Do not attempt to manage the emergency or diagnose it.

Medication changes must be discussed with the prescribing healthcare professional or pharmacist. Be calm, empathetic, concise, clear, and honest about uncertainty. You do not replace healthcare professionals."""


class OllamaChatError(Exception):
    def __init__(self, code, message, status_code=502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def chat_with_ollama(history, base_url, model, vision_model="", image=None):
    response = _post_chat(
        history,
        base_url,
        model,
        vision_model,
        image,
        stream=False,
    )
    try:
        content = response.json()["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty assistant response")
        return content.strip()
    except (ValueError, KeyError, TypeError) as error:
        raise OllamaChatError("INVALID_AI_RESPONSE", "The assistant returned an invalid response. Try again.", 502) from error


def stream_chat_with_ollama(history, base_url, model, vision_model="", image=None):
    response = _post_chat(
        history,
        base_url,
        model,
        vision_model,
        image,
        stream=True,
    )
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            item = json.loads(line)
            content = item.get("message", {}).get("content", "")
        except (json.JSONDecodeError, AttributeError, TypeError) as error:
            raise OllamaChatError("INVALID_AI_RESPONSE", "The assistant returned an invalid response. Try again.", 502) from error
        if content:
            yield content


def _post_chat(history, base_url, model, vision_model, image, stream):
    selected_model = vision_model if image and vision_model else model
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in history)
    if image:
        messages[-1]["images"] = [base64.b64encode(image["content"]).decode("ascii")]

    body = {
        "model": selected_model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": 0.2,
            "num_ctx": int(os.getenv("OLLAMA_CHAT_CONTEXT_TOKENS", "2048")),
            "num_predict": int(os.getenv("OLLAMA_CHAT_OUTPUT_TOKENS", "500")),
        },
        "keep_alive": "10m",
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json=body,
            stream=stream,
            timeout=(5, int(os.getenv("OLLAMA_CHAT_TIMEOUT_SECONDS", "600"))),
        )
    except requests.Timeout as error:
        raise OllamaChatError("AI_TIMEOUT", "The local assistant took too long to respond. Try again.", 504) from error
    except requests.ConnectionError as error:
        raise OllamaChatError("OLLAMA_UNAVAILABLE", "Ollama is currently unavailable. Start Ollama and try again.", 503) from error
    except requests.RequestException as error:
        raise OllamaChatError("OLLAMA_UNAVAILABLE", "The local assistant is temporarily unavailable. Try again.", 503) from error

    if response.status_code == 404:
        raise OllamaChatError("MODEL_NOT_FOUND", f"The local model '{selected_model}' is not installed. Check OLLAMA_MODEL and Ollama.", 503)
    if response.status_code >= 500:
        raise OllamaChatError("OLLAMA_UNAVAILABLE", "The local assistant is temporarily unavailable. Try again.", 503)
    if not response.ok:
        raise OllamaChatError("MODEL_REQUEST_FAILED", "The local assistant could not process that request.", 502)
    return response