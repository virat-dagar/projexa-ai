# WriteTrace

WriteTrace is a behavioural academic integrity checker for written submissions. It records how a user writes inside the editor, sends the final text and writing-event data to a FastAPI backend, and returns a risk report based on drafting behaviour.

The project is designed as a review-support tool, not as an automatic misconduct decision system. Its output should be treated as a signal for manual review.

## What It Checks

- Typing activity and key-event patterns
- Paste events and pasted-content ratio
- Sudden large insertions
- Long pauses during the writing session
- Writing speed and basic submission metrics
- A combined risk score with explanatory signals

## Project Structure

```text
.
+-- writetrace-clean/
|   +-- backend/
|   |   +-- app.py
|   |   +-- requirements.txt
|   +-- frontend/
|   |   +-- index.html
|   |   +-- editor.css
|   |   +-- editor.js
|   +-- README.md
|   +-- run_demo.sh
+-- documents/
|   +-- Design-and-Development-of-a-Behavioural-Academic-Integrity-Checker.pdf
|   +-- Design-and-Development-of-a-Behavioural-Academic-Integrity-Checker.pptx
|   +-- Minor Project Synopsis Report.pdf
|   +-- project-ai  -  Repaired.pptx
|   +-- notes.txt
+-- requirements.txt
```

The main runnable application is inside `writetrace-clean/`. The `documents/` folder contains project documentation and submission materials.

## Run The Demo

```bash
cd writetrace-clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
./run_demo.sh
```

After starting the demo:

- Frontend: `http://127.0.0.1:5500`
- Backend: `http://127.0.0.1:8000`
- Backend health check: `http://127.0.0.1:8000/health`

## Backend API

- `GET /health` checks whether the backend is running.
- `POST /submit` accepts the final text, timing data, and writing events, then returns extracted metrics, risk score, risk level, and explanation signals.

## Notes

- The backend is built with FastAPI.
- The frontend is plain HTML, CSS, and JavaScript.
- The current scoring focuses on writing behaviour. A future extension can add content-pattern analysis as a separate signal alongside the behavioural score.
