# WriteTrace Clean

This folder contains the runnable WriteTrace app. WriteTrace is an academic integrity checker that combines writing-behaviour analysis with offline content-pattern analysis.

The tool is designed to support manual review. It should not be presented as a system that proves AI authorship or automatically decides misconduct.

## Structure

```text
writetrace-clean/
├── backend/
│   ├── main.py
│   ├── app.py
│   ├── Procfile
│   ├── requirements.txt
│   └── writetrace_api/
│       ├── analysis.py
│       ├── main.py
│       ├── models.py
│       ├── routes.py
│       ├── settings.py
│       └── storage.py
├── frontend/
│   ├── index.html
│   ├── editor.css
│   ├── editor.js
│   ├── package.json
│   ├── runtime-config.js
│   ├── student/
│   │   └── index.html
│   └── teacher/
│       └── index.html
├── DEPLOYMENT.md
├── README.md
└── run_demo.sh
```

Frontend roles:

- `frontend/index.html` - landing page
- `frontend/student/index.html` - student dashboard
- `frontend/teacher/index.html` - teacher dashboard
- `frontend/editor.css` - shared styling for all pages
- `frontend/editor.js` - shared dashboard logic
- `frontend/runtime-config.js` - generated/deployed API URL configuration
- `backend/writetrace_api/storage.py` - JSON-backed assignment/submission store

## Analysis Layers

- Behaviour analysis checks typing events, paste ratio, sudden insertions, writing speed, pauses, and time spent.
- Content-pattern analysis checks structured academic phrasing, filler phrases, transition phrases, abstract vocabulary clusters, suspicious phrase+noun combinations, sentence-length uniformity, lexical variety, repeated phrases, repeated sentence openings, and concrete detail markers.
- The combined score gives more weight to behaviour evidence than content evidence because content-only AI detection can be unreliable.

## Workflow

- Teachers create assignments in the teacher dashboard.
- Students select an assignment, draft, and submit.
- Teachers review submissions, including paste evidence and flagged text sections.

## Run

```bash
cd writetrace-clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
./run_demo.sh
```

## URLs

- Landing page: `http://127.0.0.1:5500/`
- Student dashboard: `http://127.0.0.1:5500/student/`
- Teacher dashboard: `http://127.0.0.1:5500/teacher/`
- Backend: `http://127.0.0.1:8000`

## Runtime

Use `./run_demo.sh` from inside `writetrace-clean` to start both servers. The script serves the `frontend/` directory as the web root, so the dashboard URLs above work directly.

## Deploy

Use `DEPLOYMENT.md` for the production checklist. The recommended setup is Vercel for the static frontend and Render for the FastAPI backend.

## Timing Model

- The session clock starts on the first editor input/paste (not on page load).
- The backend still receives `startTime`, `endTime`, and `duration_seconds` from the frontend, plus the raw event log for manual review.

## Notes

- Ensure all dependencies are installed before running the demo.
- Assignments and submissions are stored in `backend/data/writetrace-store.json` by default. On hosted backends, set `WRITETRACE_DATA_FILE` to a writable persistent path.
- Content-pattern analysis is heuristic and offline. It does not send student writing to an external AI service.
