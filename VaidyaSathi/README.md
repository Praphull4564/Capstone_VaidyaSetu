# VaidyaSathi

Standalone Flask AI Healthcare Assistant for VaidyaSetu. It uses the existing local Ollama service, streams assistant tokens to the browser, keeps bounded conversation history in memory, and follows the VaidyaSamvaad/VaidyaSaransh visual language.

## Run

```powershell
cd VaidyaSathi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5003`. Ollama must be running at `http://127.0.0.1:11434`, and the model named by `OLLAMA_MODEL` in `.env` must already be installed (for example, run `ollama pull llama3.1`). No API key is needed for local Ollama use.

## Images

JPG, JPEG, PNG, and WEBP files up to 8 MB are validated, normalized in memory, previewed locally, and never saved by this app. The default `llama3.1` model is text-only, so image selection is supported but image interpretation is intentionally not claimed. To enable actual image analysis, configure `OLLAMA_VISION_MODEL` to an explicitly installed vision-capable Ollama model; the backend will then send normalized base64 image data through Ollama's image message field.

## Conversation behavior

Conversation history is bounded to the latest 20 messages and kept only in the running process. There is no authentication or database in the existing standalone architecture, so conversations are not persistent across restarts and are not logged. Ollama responses stream as newline-delimited JSON events so the first generated text appears before completion. `DELETE /api/vaidya-sathi/conversations/<conversationId>` clears a conversation.

## Safety

VaidyaSathi provides general health information. It does not diagnose, prescribe, or recommend medication changes. Emergency language receives urgent-care guidance. Verify important information with a qualified healthcare professional.