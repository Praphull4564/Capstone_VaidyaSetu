# VaidyaSetu

VaidyaSetu is a capstone project containing four runnable standalone Flask applications:

- **VaidyaSathi** — healthcare assistant chat.
- **VaidyaSamvaad** — video consultation interface.
- **VaidyaSanchay** — medication schedule organizer.
- **VaidyaSaransh** — medical report explainer.

Each application has its own `requirements.txt`, `.env.example`, and README. The complete setup instructions are in [RUN_GUIDE.md](RUN_GUIDE.md). These tools are prototypes and are not a replacement for professional medical care.

VaidyaSaransh and VaidyaSathi use Ollama; model weights are not included and must be downloaded separately. VaidyaSanchay needs a Gemini API key supplied in a local `.env`. VaidyaSamvaad needs a locally generated self-signed certificate and key. None of these private/generated files should be committed.

`VaidyaDrishti` currently contains only empty `Dataset` and `models` directories; no runnable source code or dependency manifest is present there yet.

## Upload to GitHub

Before publishing, inspect the files you intend to share, especially `Documents`, media, and any sample data. The root `.gitignore` excludes local virtual environments, `.env` files, private keys/certificates, databases, and downloaded model weights. Only `.env.example` templates should be committed. Keep real API keys and passwords out of GitHub.

1. Create a repository on GitHub. If you already have this local README, choose **not** to initialize the new repository with a README, `.gitignore`, or license.
2. Open PowerShell in this project folder and initialize Git:

   ```powershell
   cd D:\Projects\Capstone_VaidyaSetu
   git init -b main
   ```

3. Check what Git will include before staging:

   ```powershell
   git status --short
   ```

   If any secret, `.env`, private certificate/key, database, `.venv`, or model file appears as an untracked file, stop and check the ignore rules. Do not upload it.

4. Stage and inspect the upload, then commit:

   ```powershell
   git add .
   git status --short
   git commit -m "Initial project upload"
   ```

5. Copy the HTTPS repository URL from GitHub, substitute your account and repository name below, and push:

   ```powershell
   git remote add origin https://github.com/<USERNAME>/<REPOSITORY>.git
   git push -u origin main
   ```

Sign in when GitHub prompts you. If `git` is not recognized, install Git for Windows first. If you accidentally stage a secret, do not push; remove it from staging, keep it ignored, and rotate/revoke the exposed credential.

No license is included. Choose and add a license only if you have the right to license all included code and assets.
