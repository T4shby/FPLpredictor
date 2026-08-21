# Frontend

Next.js dashboard for Model B xPts. It reads FastAPI (`/api/v1/status`, `/picks`, `/rankings`, `/players/{id}`).

```bash
cd frontend
npm install
npm run dev
```

Run the API first:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Then open http://localhost:3000
