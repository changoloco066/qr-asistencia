# QR Asistencia

A QR-based attendance system for a university class (Facultad de Arquitectura). The professor projects a rotating QR code each session; students scan it and check in with their student ID (matrícula). No app install required — everything runs in the browser.

## Why this exists

Attendance is normally taken by roll call or a sign-in sheet, which is slow and easy to fake (a photo of a paper sheet or a static QR can be passed around to absent students). This project solves that with:

- A **rotating QR token** that expires every ~20–30 seconds, so a screenshot goes stale before it's useful.
- **Roster validation** — a student can only check in if their matrícula is on the professor's pre-loaded class list, and only once per session.
- A **live dashboard** the professor watches during class, updating automatically as students check in.
- **Stats** per student and per class (attendance %, absences) computed from accumulated session data.

## Scope (current)

- One professor, one subject, one group. No multi-tenant support yet — if this expands to more professors later, the data model will need an `owner` column and per-account scoping, but that's out of scope for now.
- The professor's roster (matrícula + name) is uploaded once per semester, manually maintained by her.
- Students only ever interact with the QR check-in page — they never see or touch the roster upload.

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌───────────────┐
│  Student phone   │──scan─▶│  checkin.html (JS)    │──POST─▶│  /api/checkin │
└─────────────────┘        └──────────────────────┘        └──────┬────────┘
                                                                    │
┌─────────────────┐        ┌──────────────────────┐               ▼
│ Professor screen │◀─poll─│  dashboard.html (JS)  │◀───────  Postgres (Neon/Supabase)
└─────────────────┘        └──────────────────────┘               ▲
                                     │                              │
                                     └───POST /api/session/token────┘
```

- **Backend:** Python (Flask) deployed as Vercel serverless functions under `/api`. Vercel functions are stateless and short-lived — there's no persistent process, so there's no native WebSocket support here.
- **Live updates:** handled with **polling** instead of WebSockets. The dashboard asks `/api/session/status` every few seconds for the latest check-ins. This is a deliberate choice, not a limitation we're working around — polling fits Vercel's execution model and a classroom doesn't need sub-second latency.
- **Rotating QR:** the dashboard requests a new token from `/api/session/token` every ~20–30 seconds and re-renders the QR client-side (`qrcode.js`). `/api/checkin` rejects any token outside its valid window.
- **Database:** Postgres, hosted externally (Neon or Supabase — both have a free tier and work well with Vercel; Vercel no longer offers its own managed Postgres). Connection string lives in an environment variable, never committed.
- **Auth:** the professor's dashboard sits behind a simple login (session/JWT). The check-in page is intentionally public — anyone with the current QR can reach it — but it can only write a single attendance record for the matrícula it's given, never read anyone else's data.

## Folder structure

```
qr-asistencia/
├── api/                  # Flask app, deployed as Vercel functions
│   ├── index.py          # entrypoint Vercel detects
│   ├── auth.py           # professor login/session
│   ├── roster.py         # upload/manage student list (professor only)
│   ├── sessions.py       # create session, generate rotating token
│   ├── checkin.py        # student check-in endpoint
│   └── stats.py          # attendance percentages, per-student/per-class
├── frontend/
│   ├── login.html        # professor login
│   ├── dashboard.html    # live QR + roll call view
│   ├── checkin.html      # what students see after scanning
│   ├── css/style.css
│   └── js/
│       ├── dashboard.js  # QR rendering + polling
│       └── checkin.js
├── db/
│   └── schema.sql        # table definitions
├── requirements.txt
├── vercel.json           # routes Vercel to the Flask app
└── .gitignore
```

## Data model (planned)

- `students` — matrícula (PK), full_name
- `sessions` — id, date, created_at
- `attendance` — session_id (FK), matrícula (FK), checked_in_at
- `session_tokens` — session_id (FK), token, expires_at

## Roadmap

1. **Roster management** — professor logs in, uploads/edits the class list once per semester. *(build first — everything else depends on it)*
2. **QR check-in** — rotating token, live dashboard, roster validation, one check-in per student per session.
3. **Stats** — attendance % per student, per-class summary, flag students below an attendance threshold.

## Local development

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# environment variables needed:
# DATABASE_URL=postgresql://...
# SECRET_KEY=...

vercel dev                      # runs the Flask functions + static frontend locally
```

## Deployment

Deployed on Vercel (free Hobby tier). Push to `main` → Vercel auto-deploys. Database is external (Neon/Supabase) — set `DATABASE_URL` and `SECRET_KEY` in the Vercel project's environment variables, not in this repo.

## Adding a collaborator

GitHub repo → **Settings → Collaborators and teams → Add people** → enter their GitHub username or email. They'll get an invite email and need to accept it before they can push.

## Getting a database running

1. Create a free Postgres database on [Neon](https://neon.tech) or [Supabase](https://supabase.com).
2. Run `db/schema.sql` against it (both providers have a SQL editor in their dashboard, or use `psql "$DATABASE_URL" -f db/schema.sql`).
3. Copy `.env.example` to `.env` and fill in `DATABASE_URL` and `SECRET_KEY` (`SECRET_KEY` can be any long random string — it signs the login tokens).
4. Seed the one teacher account:
   ```bash
   DATABASE_URL=... python scripts/seed_teacher.py mama_username her-password
   ```
   There's no signup flow on purpose — one professor, one account, created once.

## Status

- ✅ **Phase 1 — Roster management.** Login + roster CRUD/CSV upload, tested end-to-end.
- ✅ **Phase 2 — QR check-in.** Rotating token, live dashboard, roster validation, tested end-to-end.
- ✅ **Phase 3 — Stats.** `api/stats.py` computes attendance % per student (based on how many of the sessions held so far they attended), flags anyone under 80% as at-risk, and gives a session-by-session breakdown per student on click. `frontend/stats.html` shows summary cards (classes held, students, average attendance) plus the sortable-by-risk table. Not yet tested end-to-end.

### How the rotating QR actually works

There's no background process generating tokens on a timer — Vercel functions don't support that. Instead:
1. The dashboard (running in the professor's browser) asks `/api/sessions/<id>/token` for a new token every 20 seconds and re-renders the QR itself.
2. Each token is stored with a 25-second expiry (`TOKEN_LIFETIME_SECONDS` in `api/sessions.py`).
3. `/api/checkin` only accepts a token that still exists and hasn't expired.

The 20s/25s gap is deliberate breathing room so a checked-in student's request doesn't get rejected by a token that expired mid-flight.