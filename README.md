# Truck Utilization Tracker

A Streamlit web app that replaces the manual Excel tracker: field users log DV
(Dedicated Vehicle) numbers per plant twice a day — 1st Half (Morning) and 2nd Half
(Evening) — with the ability to correct mistakes, and anyone can view a live
dashboard with the latest report, a full audit log, and day-wise history. Styled
with a dark/light toggle and works cleanly on phone, laptop, or a big screen.

## What's inside

| File | Purpose |
|---|---|
| `app.py` | The Streamlit app — landing page, login, add/edit/delete entries, dashboard, professional analytics |
| `db.py` | SQLite database setup and all read/write queries |
| `analytics.py` | Weekly/monthly aggregation, plant/region averages, and auto-generated highlights for the Professional Dashboard |
| `excel_export.py` | Builds the region-grouped + subtotal + grand-total Excel report |
| `requirements.txt` | Python packages needed |
| `data/tracker.db` | The SQLite database file — created automatically the first time you run the app |

**IMPORTANT — database backend change:** This version replaces the local SQLite
file with a hosted Postgres database (via Supabase's free tier). This is a
required setup step, not optional — **see section 6.5 below before running this
version.** The switch happened because the local SQLite file was living on the
app server's disk, which the hosting platform wiped during a routine
restart/redeploy, silently deleting all previously entered data. A hosted
database is independent of the app server, so this cannot happen again.

**Note:** The plant list is fixed and pre-loaded from the official 60-plant master list
(region, site code, plant name) — users select Region, then Plant (searchable dropdown),
and Site Code auto-fills. Three plant names legitimately repeat under different site
codes (GEO NUTRI, OZPURE, SILVASSA), so the app keys plants by site code internally and
shows `Plant Name (SITE_CODE)` in the dropdown to keep them unambiguous.

**Schema change notice:** This version changed `plants_master` to be keyed by `site_code`
instead of `plant_name` (to support the duplicate names above), and re-seeds the official
plant list on startup.

**Schema change notice:** This version added a `dv_type` column to `entries` (DV Type:
10PP/12PP/18PP/9MT/18MT/12MT — a plant can have separate entries per DV Type, shown as
segregated rows in reports), and a `trips_completed` field (used only for the Trend
Dashboard's "Trips / DV / Month" KPI). It also removed 2 duplicate rows from the plant
master list (GEO NUTRI and OZPURE are no longer duplicated; SILVASSA still legitimately
has two sites). A self-healing migration in `db.py` applies this automatically on
startup, safely reassigning any historical entries rather than losing them.

## 1. Prerequisites

- Python 3.10+ installed (check with `python --version` in a terminal)
- VS Code with the **Python extension** installed

## 2. Setup (one-time)

Open this folder in VS Code (`File → Open Folder...`), then open a terminal inside VS Code
(`` Ctrl+` `` / `` Cmd+` ``) and run:

```bash
python -m venv venv

# Activate it
# Windows (PowerShell):
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## 3. Run it

```bash
streamlit run app.py
```

Opens automatically at `http://localhost:8501`.

## 4. How the app works

**Landing page** — three options:
- **Update Data** — requires login, takes you to add/edit/delete entries
- **View Report** — no login needed, anyone can open it
- **Trend Dashboard** — no login needed, weekly/monthly trend analytics for leadership review

Once inside any of these three, small icon shortcuts in the top-right corner let you
jump directly to either of the other two — no need to return to the landing page.

**Update Data → Add Entry tab:**
1. Pick the **Date** and **Shift** (1st Half / Morning, or 2nd Half / Evening) —
   recorded on the backend, but the visible report always shows only the latest
   submission per day (see "View Report" below)
2. Enter your name, pick the **Region**, then pick the **Plant** from a dropdown filtered
   to that region (type to search) — **Site Code auto-fills** as soon as a plant is chosen
3. Pick the **DV Type** (10PP, 12PP, 18PP, 9MT, 18MT, or 12MT) — submitting again for the
   same plant with a different DV Type creates a separate, segregated entry rather than
   overwriting the first
4. Enter Total DV, DV Available Today, DV Utilised, DV Inroute
5. Submit — Unutilized Balance and Utilization % are always calculated, never typed
6. After a successful submit, a **"View Dashboard"** button appears so you can jump
   straight to the report

**Update Data → Edit / Delete Entries tab:**
- Pick a date, and every individual entry submitted for that date appears in an
  expandable list (both shifts, all DV Types — nothing is merged here, so you can
  correct any specific submission)
- Open any entry to correct its numbers in place (an audit trail keeps the original
  submission time; edits update "Updated By" and the save time)
- Or delete it entirely, with a confirm step so it's not accidental

**View Report** (tab order matches how you'd actually use it — the day's numbers
first, then the full history, then a single plant's trend):
- **Day-wise Report** tab (shown first) — pick any date and see one merged result per
  plant per DV Type. 1st Half and 2nd Half are **not** shown as separate sections —
  whichever shift was submitted most recently for that plant/DV Type wins, matching
  how the data is actually meant to be reviewed
- **All Updates Log** tab — every single update ever made, across every plant/date/shift/
  DV Type, newest first, with its own Excel download — this is the full audit trail
  (this one *does* show every individual shift submission, since it's a raw log)
- **Plant History** tab — every submission for one plant, including date/shift/DV Type

**Trend Dashboard** — a supply-chain-style analytics view, separate from the raw
report above:
- **Weekly** mode gives you a real calendar **From/To date range picker** — pick any
  custom range to see the trend for exactly those days
- **Monthly** mode gives you a **month dropdown** built from whichever months actually
  have data, so you can review any past month's trend, not just the current one
- Three KPI cards: **Avg Fleet Size** (average daily Total DV across the period),
  **Utilization vs Available DV**, and **Opening DV %** (DV Available ÷ Total DV,
  target ≥ 50%)
- **Top Performing Plants** and **Plants Needing Focus** — ranked by average daily
  Utilization %, top/bottom 5 shown with a "See all plants" expander for the full list
  (also showing each plant's Opening DV % and Effective Utilization %)
- **Region Scorecard** — average Utilization %, Opening DV %, and Effective Utilization
  (Utilization % × Opening DV %) per region over the selected period
- **Key Highlights** — auto-generated callouts: which regions are converting nearly all
  their available DVs, whether Opening DV % is missing the 50% target, and which plants
  have the most underutilized capacity

**Note:** the source PDF also tracked a "Trips/DV/Month" KPI against a target of 15 —
that isn't included because the app doesn't currently collect a trip-count field. Ask if
you'd like that added as a new input on the entry form; it's a small addition once the
data exists to calculate it from.

## 5. Dark / Light mode

A toggle button sits in the top-right corner of every screen. It switches between a
light theme and a high-contrast dark theme — text color, backgrounds, buttons, form
labels, KPI cards, and Streamlit's built-in alert boxes are all explicitly handled so
nothing goes invisible in either mode.

## 6. Default login credentials

Only needed to reach **Update Data** — the dashboard has no login.

| Username | Password |
|---|---|
| `rcplcampa` | `campa@123` |

**Change this before giving the app to your team:**
Open `db.py`, find this block inside `init_db()`:

```python
cur.execute(
    "INSERT INTO users (username, password_hash) VALUES (?,?)",
    ("rcplcampa", _hash("campa@123")),
)
```

Change the username/password, then delete `data/tracker.db` and restart the app.

## 6.5. Connecting to Postgres (Supabase) — required, do this before running

**This app no longer uses a local SQLite file.** It previously did, and that file
got wiped when the hosting platform reset its filesystem (this happened once —
see the note at the top of this README). The app now uses a free hosted Postgres
database via Supabase, which is independent of whichever host runs the app code,
so it survives restarts, redeploys, and even switching hosts entirely.

**Step 1 — Create a free Supabase project**
1. Go to [supabase.com](https://supabase.com) → sign up (free, no credit card needed)
2. "New project" → give it a name → set a database password (**save this password
   somewhere** — you'll need it in Step 2) → choose the region closest to you → Create

**Step 2 — Get your connection string**
1. In your new project, go to **Settings → Database**
2. Under "Connection string," choose the **URI** tab
3. Copy the string — it looks like:
   `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with the real password you set in Step 1

**Step 3 — Add it locally (for testing on your own machine)**
1. Copy `.streamlit/secrets.toml.example` to a new file: `.streamlit/secrets.toml`
   (same folder, drop the `.example`)
2. Paste your real connection string in as `DATABASE_URL`
3. This file is excluded by `.gitignore` — it will never get pushed to GitHub

**Step 4 — Test locally before deploying**
```bash
streamlit run app.py
```
Log in, add a test entry, check the dashboard. If this works locally, it'll work
live too — this is the most important step, since it catches any issue before
your team ever sees it.

**Step 5 — Add the same secret to your live deployment**
- **Streamlit Community Cloud:** your app → hamburger menu (⋮) or "Manage app" →
  **Settings → Secrets** → paste the same `DATABASE_URL = "..."` line → Save
  (this triggers an automatic redeploy)
- **Render:** your service → **Environment** tab → add an environment variable
  named `DATABASE_URL` with the same connection string as the value

**Note:** `.streamlit/secrets.toml` (your real one) is never pushed to GitHub —
only `.streamlit/secrets.toml.example` (the template, with no real password) is.

## 7. Pushing to GitHub

```bash
git init
git add .
git commit -m "Truck utilization tracker"
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

## 8. Deploying for free

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub
3. "New app" → pick this repo and `app.py` as the entry point → Deploy
4. Add your `DATABASE_URL` secret (see section 6.5, Step 5) before or right after
   the first deploy

**Your data is now safe from host resets.** Since it lives in Supabase rather
than on the app server's disk, redeploys, restarts, reboots, or even switching
to a different host entirely (Render, etc.) will not affect your stored entries.

## 9. Roadmap / possible next steps

- Add validation rules specific to your ops (e.g. DV Inroute + DV Utilised shouldn't
  exceed Total DV, if that's a real constraint)
- Persist the dark/light theme choice across restarts (currently resets to light)
- Per-user logins if you want stronger accountability beyond the free-text
  "updater name" / "corrected by" fields
- Move hosting to Render or Hugging Face Spaces if you want to remove the
  "Hosted with Streamlit" badge (now safe to do any time, since your data
  no longer lives on the app server)

