# Task Manager

Daily tasks + long-term goals. Django + DRF + SQLite backend; vanilla HTML/CSS/JS frontend served by Django (same origin, so no CORS needed).

## Features
Register/login/logout (JWT in HTTP-only cookie, CSRF-protected, bcrypt) · tasks (CRUD, priority, tag, status, recurring, Today/Upcoming/Overdue, search/filter/sort, pagination) · goals with milestones and linked tasks (auto progress %) · dashboard (today, overdue, goal progress, weekly chart, streak) · in-app reminders (bell) · dark/light mode · responsive & keyboard accessible · throttling (60/min anon, 600/min user, 10/min auth).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set SECRET_KEY
python manage.py migrate
python manage.py seed           # optional: demo / demo12345
python manage.py runserver      # http://localhost:8000
python manage.py test           # run tests
```

## Env variables
`SECRET_KEY`, `DEBUG` (1/0), `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `TIME_ZONE`, `JWT_TTL_HOURS`.

## API (all under /api, JSON, errors as `{"error":{"status","message","details"}}`)
| Method | Route | Notes |
|---|---|---|
| GET | /auth/csrf/ | sets csrftoken cookie |
| POST | /auth/register/, /auth/login/ | sets auth cookie |
| POST | /auth/logout/ | clears cookie |
| GET | /auth/me/ | current user |
| GET/POST | /tasks/ | `view=today\|upcoming\|overdue`, `priority`, `status`, `category`, `goal`, `search`, `ordering`, `page`, `page_size` |
| GET/PATCH/PUT/DELETE | /tasks/{id}/ | marking `done` spawns next occurrence if recurring |
| GET/POST, GET/PATCH/DELETE | /goals/, /goals/{id}/ | includes `progress` + `milestones` |
| GET/POST, PATCH/DELETE | /milestones/, /milestones/{id}/ | `?goal=` filter |
| GET | /dashboard/, /reminders/ | |

## Data model
User 1─* Goal 1─* Milestone · User 1─* Task *─0..1 Goal. Progress = done(tasks+milestones) / total.

## Deployment (Render, single service)
Frontend is served by Django, so deploy one Render web service: build `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`, start `gunicorn config.wsgi`. Set `DEBUG=0`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS=https://<your-app>.onrender.com`. Production also needs `gunicorn` and `whitenoise` (not included in requirements.txt per the "no extra libraries" rule) and a persistent disk or Postgres, since SQLite on Render's ephemeral disk resets on deploy. Vercel isn't needed unless you split the frontend out (then add CORS + SameSite=None cookies).

## Screenshots
`docs/dashboard.png` · `docs/tasks.png` · `docs/goals.png` (placeholders)
