# VaidyaSetu: Local Run Guide

This guide covers each project folder in the repository. Commands are for Windows PowerShell. Use one terminal per running app.

## Before you start

Install:

- Git for Windows (to clone the repository)
- Python 3.10 or newer, with Python added to `PATH`
- Ollama, if you want to run VaidyaSathi or VaidyaSaransh
- Tesseract OCR with English language data, if you want scanned-report OCR in VaidyaSaransh
- OpenSSL, if you want to run VaidyaSamvaad's local HTTPS server

Clone the GitHub repository, then enter its folder:

```powershell
git clone https://github.com/<USERNAME>/<REPOSITORY>.git
cd <REPOSITORY>
```

Each app is independent and has its own virtual environment. From the repository root, enter that app's folder, create/activate its environment, install requirements, and copy its example settings:

```powershell
cd <APP_FOLDER>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Replace placeholder values in the local `.env` when a section below requires them. Never commit `.env`; commit only `.env.example`.

To leave an activated environment, run `deactivate`. To run a different app, open another terminal and create a separate environment in that app's folder.

## 1. VaidyaSathi — healthcare assistant

1. If Ollama is not installed, install and start it.
2. Download a model locally (this does not add model weights to the GitHub repository):

   ```powershell
   ollama pull llama3.1
   ```

3. Set up and start the app:

   ```powershell
   cd VaidyaSathi
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   python app.py
   ```

   The example selects `OLLAMA_MODEL=llama3.1`. If you downloaded a different model, set `OLLAMA_MODEL` in `.env` to the exact installed model name.

4. Open `http://127.0.0.1:5003`.

No Gemini/API key is needed when using local Ollama. Image interpretation requires a separate vision-capable Ollama model; the default text model does not analyze images.

## 2. VaidyaSamvaad — video consultation

1. OpenSSL must be installed and available as `openssl` in PowerShell.
2. Set up the app and copy its settings template:

   ```powershell
   cd VaidyaSamvaad
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. Set `FLASK_SECRET_KEY` in `.env` to a private random value. Generate a local self-signed certificate and key:

   ```powershell
   openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
   ```

   Keep `key.pem`, `cert.pem`, and `.env` local; the repository ignores them.

4. Start the app and open `https://127.0.0.1:5000`:

   ```powershell
   python app.py
   ```

   The browser will show a warning because the certificate is self-signed; this is expected for local development.

## 3. VaidyaSanchay — medication schedule organizer

This app requires a Gemini API key. Create one through Google AI Studio and put it in your local `VaidyaSanchay\.env` as `GEMINI_API_KEY`. Do not put a real key in GitHub or share it publicly.

```powershell
cd VaidyaSanchay
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace `GEMINI_API_KEY=replace-with-your-own-key`. Then run:

```powershell
python app.py
```

Open `http://127.0.0.1:5001`.

## 4. VaidyaSaransh — medical report explainer

1. Install Ollama and Tesseract OCR. Ensure `tesseract.exe` is available on `PATH`. Text-based PDFs do not need OCR.
2. Download a compatible Ollama model locally:

   ```powershell
   ollama pull llama3.1
   ```

3. Set up and start the app:

   ```powershell
   cd VaidyaSaransh
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   python app.py
   ```

   The example selects `OLLAMA_MODEL=llama3.1`. If you downloaded a different model, set `OLLAMA_MODEL` in `.env` to that exact installed model name. No model weights are stored in the repository.

4. Open `http://127.0.0.1:5002`.

## 5. VaidyaDrishti

The current `VaidyaDrishti` folder contains empty `Dataset` and `models` directories only. It has no application source, dependency file, or entry point, so there is not yet a command to run. Add the actual application code and its setup instructions before treating it as runnable.

## Troubleshooting

- **`python` or `pip` is not recognized:** install Python and enable the installer option to add it to `PATH`, then reopen PowerShell.
- **Ollama connection error:** make sure the Ollama app/service is running and `OLLAMA_BASE_URL` in the app's local `.env` is correct.
- **Ollama says model not found:** run `ollama list`; pull a model with `ollama pull <model-name>` and make `.env`'s `OLLAMA_MODEL` match that name.
- **PowerShell blocks activation:** use `.\.venv\Scripts\python.exe app.py` and `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, or follow your organization's PowerShell policy.
- **OpenSSL is not recognized:** install OpenSSL or use a terminal that provides it, then create the certificate from inside `VaidyaSamvaad`.
- **Gemini is not configured:** check that a valid key is set in `VaidyaSanchay\.env`; restart the app after editing it.

These are local-development instructions, not production deployment instructions. Medical report and medication tools can make mistakes; verify important information with a qualified healthcare professional.
