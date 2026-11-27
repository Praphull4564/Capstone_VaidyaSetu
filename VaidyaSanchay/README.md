# VaidyaSanchay

Standalone medication scheduling module for VaidyaSetu. It extracts the doctor's stated instructions with Gemini, flags missing or conflicting information, and prepares a patient-friendly timetable. It does not store submitted prescriptions.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
4. Run `python app.py` and open `http://127.0.0.1:5001`.

`GEMINI_MODEL`, `FLASK_SECRET_KEY`, `HOST`, `PORT`, and `FLASK_DEBUG` can also be set in `.env`. Keep `.env` private and never commit API keys.

## Google Calendar

After a schedule is prepared, choose a date and use the per-reminder Google Calendar links. Each link opens a prefilled, one-time event in the user's Google account. The app does not need Calendar API credentials or access to the user's account, and it does not invent recurring events. Only reminders with an exact clock time can be added.

## Safety

Gemini output is an organizational aid, not medical advice. Always compare it with the original prescription. Missing or ambiguous instructions should be confirmed with the prescribing doctor or pharmacist. Do not use this app to change medication or manage an emergency reaction.