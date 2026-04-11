# WriteTrace Clean

This folder is a cleaned-up copy of the current working project files only.

## Structure

- `backend/app.py` - FastAPI backend
- `frontend/index.html` - main frontend entry
- `frontend/editor.css` - frontend styles
- `frontend/editor.js` - frontend logic
- `requirements.txt` - Python dependencies
- `run_demo.sh` - starts backend and frontend together

## Run

```bash
cd writetrace-clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run_demo.sh
```

## URLs

- Frontend: `http://127.0.0.1:5500`
- Backend: `http://127.0.0.1:8000`

## Notes

- This folder was created for review and cleanup.
- The older prototype folders and extra repo files were intentionally left untouched outside this folder.
- Ensure all dependencies are installed before running the demo.
