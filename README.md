# WriteTrace

WriteTrace is an academic integrity checker for written submissions. It records how a user writes inside the editor, sends the final text and writing-event data to a FastAPI backend, and returns a risk report based on both drafting behaviour and content-pattern analysis.

The project is designed as a review-support tool, not as an automatic misconduct decision system. Its output should be treated as a signal for manual review.

## What It Checks

- Typing activity and key-event patterns
- Paste events and pasted-content ratio
- Sudden large insertions
- Long pauses during the writing session
- Writing speed and basic submission metrics
- Content-pattern signals such as over-structured reasoning phrases, filler generalizations, flow-control transitions, abstract vocabulary clusters, suspicious phrase+noun combinations, low lexical variety, unusually even sentence rhythm, repeated phrase patterns, and limited concrete detail
- A combined risk score with separate behaviour and content explanations

## How The Scoring Works

WriteTrace separates the analysis into two layers:

- Behaviour analysis checks the writing process: typing events, paste ratio, sudden insertions, writing speed, pauses, and time spent.
- Content-pattern analysis checks the final text: structured academic phrasing, filler phrases, transition phrases, abstract vocabulary density, suspicious phrase+noun combinations, sentence-length uniformity, lexical variety, repeated phrases, repeated sentence openings, and concrete detail markers such as numbers, quotes, or citation-style references.

The final score is a weighted combination that gives more importance to behaviour evidence than content evidence. This is intentional because content-only AI detection can produce false positives, especially with formal academic writing. The project should be presented as a review-support system, not a tool that proves AI authorship.

## Project Structure

```text
.
+-- writetrace-clean/
|   +-- backend/
|   |   +-- main.py
|   |   +-- app.py
|   |   +-- requirements.txt
|   |   +-- writetrace_api/
|   +-- frontend/
|   |   +-- index.html
|   |   +-- editor.css
|   |   +-- editor.js
|   |   +-- package.json
|   +-- README.md
|   +-- DEPLOYMENT.md
|   +-- run_demo.sh
|-- render.yaml
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

## Deploy

Use `writetrace-clean/DEPLOYMENT.md` for the full checklist. The recommended production-ish setup is:

- Vercel static frontend from `writetrace-clean/frontend`
- Render FastAPI backend from `writetrace-clean/backend`

The whole app can technically run on Vercel only if you replace local JSON storage with an external database. For this project demo, splitting frontend/backend is simpler and more reliable.

## Backend API

- `GET /health` checks whether the backend is running.
- `POST /submit` accepts the final text, timing data, and writing events, then returns extracted metrics, behaviour analysis, content-pattern analysis, combined risk score, risk level, and explanation signals. (Scoring endpoint used for standalone analysis.)
- Assignment workflow endpoints (used by the student/teacher dashboards):
  - `GET /assignments/public`
  - `POST /teacher/assignments`
  - `GET /teacher/assignments`
  - `POST /assignments/{assignment_id}/submit`
  - `GET /teacher/assignments/{assignment_id}/submissions`
  - `GET /teacher/submissions/{submission_id}`

## Notes

- The backend is built with FastAPI and split into settings, routes, storage, models, and analysis modules.
- The frontend is plain HTML, CSS, and JavaScript.
- Assignment/submission data is stored in `writetrace-clean/backend/data/writetrace-store.json` locally and can be pointed at a persistent deploy path with `WRITETRACE_DATA_FILE`.
- For the demo, the session clock starts on the first editor input/paste (not on page load).
- The content-pattern analysis is heuristic and offline. It does not send student writing to an external AI service.
