# Deploy WriteTrace

Recommended deployment:

- Frontend: Vercel static site from `writetrace-clean/frontend`
- Backend: Render FastAPI web service from `writetrace-clean/backend`

This keeps the frontend fast and simple while giving the API a normal long-running process and a writable data file for assignments/submissions.

## Local Smoke Run

```bash
cd writetrace-clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
./run_demo.sh
```

Open:

- Frontend: `http://127.0.0.1:5500`
- Backend health: `http://127.0.0.1:8000/health`

## Backend On Render

You can use the root `render.yaml` blueprint, or create the service manually.

Manual settings:

- Service type: Web Service
- Root Directory: `writetrace-clean/backend`
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

Environment variables:

```text
WRITETRACE_CORS_ORIGINS=https://your-vercel-app.vercel.app
WRITETRACE_DATA_FILE=/var/data/writetrace-store.json
```

If you use the blueprint, it also attaches a small persistent disk at `/var/data`. Without a persistent disk, Render's filesystem can reset on redeploys, so assignment/submission data should be treated as temporary.

## Frontend On Vercel

Create a Vercel project with:

- Root Directory: `writetrace-clean/frontend`
- Framework Preset: Other
- Build Command: `npm run build`
- Output Directory: `dist`

Set this Vercel environment variable:

```text
WRITETRACE_API_BASE_URL=https://your-render-api.onrender.com
```

After Vercel gives you the final frontend URL, add that exact URL to `WRITETRACE_CORS_ORIGINS` on Render and redeploy the backend.

## Can Everything Go On Vercel?

Technically yes: Vercel supports FastAPI/Python deployments. For this project, I would not make that the default because assignments and submissions need durable storage. Vercel's Python/FastAPI app runs as a function, which is good for stateless API work, but not a good place to rely on local JSON files for persistent classroom data.

Use all-Vercel only if you also move storage to an external database. If you do that later, set the frontend runtime API base to `/` for same-origin API calls:

```text
WRITETRACE_API_BASE_URL=/
```

## Current References

- Vercel FastAPI docs: https://vercel.com/docs/frameworks/backend/fastapi
- Vercel Python runtime docs: https://vercel.com/docs/functions/runtimes/python
- Render FastAPI docs: https://render.com/docs/deploy-fastapi
