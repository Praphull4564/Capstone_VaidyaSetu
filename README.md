# VaidyaSetu

VaidyaSetu is a capstone project containing four runnable standalone Flask applications:

- **VaidyaSathi** — healthcare assistant chat.
- **VaidyaSamvaad** — video consultation interface.
- **VaidyaSanchay** — medication schedule organizer.
- **VaidyaSaransh** — medical report explainer.

Each application has its own `requirements.txt`, `.env.example`, and README. The complete setup instructions are in [RUN_GUIDE.md](RUN_GUIDE.md). These tools are prototypes and are not a replacement for professional medical care.

VaidyaSaransh and VaidyaSathi use Ollama; model weights are not included and must be downloaded separately. VaidyaSanchay needs a Gemini API key supplied in a local `.env`. VaidyaSamvaad needs a locally generated self-signed certificate and key. None of these private/generated files should be committed.

`VaidyaDrishti` currently contains only empty `Dataset` and `models` directories; no runnable source code or dependency manifest is present there yet.


