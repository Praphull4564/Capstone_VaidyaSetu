# VaidyaSamvaad

Standalone Flask video consultation interface.

## Run locally (Windows PowerShell)

From the repository root:

```powershell
cd VaidyaSamvaad
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a self-signed certificate for local development. OpenSSL must be installed and available on `PATH`:

```powershell
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

Set `FLASK_SECRET_KEY` in `.env` to a random private value, then run:

```powershell
python app.py
```

Open `https://127.0.0.1:5000`. The browser will warn that the local certificate is self-signed. The app creates its SQLite database in Flask's instance directory; do not commit that database or the generated certificate and key.

This development setup is not production deployment guidance.
