# Relay — Frontend (React + Vite + TypeScript + Tailwind)

Real login (username/password against your FastAPI backend, JWT-based), live
inbox, live Claude-generated replies, live bulk-job polling, live analytics.
No mock data.

## Quickstart

```powershell
cd frontend
npm install
copy .env.example .env      # only needed if your backend isn't at 127.0.0.1:8000
npm run dev
```

Open **http://localhost:5173**. Make sure your backend (`uvicorn app.main:app`)
is running first, and that in `backend/.env` you have:

```
ALLOWED_ORIGINS=http://localhost:5173
```

(then restart uvicorn if you changed it).

## Logging in

- **Demo account**: pre-filled as `demo@relay.ai` / `demo1234` — this only
  works if you ran `python seed.py` in `backend/` first.
- **Or create your own account**: click "Create account" on the login screen
  to register a new user directly against `POST /auth/register`. New accounts
  start with an empty inbox — you'd need to connect a mailbox or seed data to
  see emails.

The JWT is stored in `localStorage` (`relay_token`) so you stay signed in
across page reloads; "Sign out" in the sidebar clears it.

## Structure

```
src/
  main.tsx              Router + AuthProvider setup
  App.tsx                Route table, auth guard (redirects to /login if no token)
  context/AuthContext.tsx  Login/register/logout + token state
  lib/api.ts              Typed fetch wrapper for every backend endpoint
  types.ts                 TypeScript mirrors of the backend's Pydantic schemas
  pages/
    Login.tsx              Real email/password form, login or register toggle
    Dashboard.tsx           Live stats + recent emails from GET /emails
    Inbox.tsx               Searchable table of all emails
    EmailDetail.tsx         Calls POST /emails/{id}/generate-replies (live Claude call)
    Bulk.tsx                Starts a real job, polls GET /emails/bulk-status/{id}
    Analytics.tsx           GET /analytics
  components/Sidebar.tsx
```

## Notes

- `VITE_API_BASE` (in `.env`) controls which backend it talks to — defaults
  to `http://127.0.0.1:8000`.
- Generating replies for an email is a real, live call to Claude via your
  backend — expect a few seconds of loading, not instant.
- This was verified with `npm install`, `npx tsc -b` (clean), `npm run build`
  (clean), and `npm run dev` (boots on :5173) before being handed to you.
