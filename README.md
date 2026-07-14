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

**Note:** The plant list is fixed and pre-loaded from the official 60-plant master list
(region, site code, plant name) — users select Region, then Plant (searchable dropdown),
and Site Code auto-fills. Three plant names legitimately repeat under different site
codes (GEO NUTRI, OZPURE, SILVASSA), so the app keys plants by site code internally and
shows `Plant Name (SITE_CODE)` in the dropdown to keep them unambiguous.

**Schema change notice:** This version changed `plants_master` to be keyed by `site_code`
instead of `plant_name` (to support the duplicate names above), and re-seeds the official
plant list on startup. If you have a `data/tracker.db` from an earlier version of this
app, delete it before running — the app will recreate it fresh with the new structure.

**Schema change notice:** This version added a `dv_type` column to `entries` (DV Type:
10PP/12PP/18PP/9MT/18MT/12MT — a plant can have separate entries per DV Type, shown as
segregated rows in reports), and a `trips_completed` field (used only for the Trend
Dashboard's "Trips / DV / Month" KPI). It also removed 2 duplicate rows from the plant
master list (GEO NUTRI and OZPURE are no longer duplicated; SILVASSA still legitimately
has two sites). If you have a `data/tracker.db` from an earlier version of this app,
delete it before running — the app will recreate it fresh with the new structure.

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

## 7. Pushing to GitHub

```bash
git init
git add .
git commit -m "Truck utilization tracker"
git remote add origin https://github.com/<your-username>/<your-repo>.git
git branch -M main
git push -u origin main
```

`data/tracker.db` is excluded via `.gitignore` so your live data never gets pushed.

## 8. Deploying for free

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub
3. "New app" → pick this repo and `app.py` as the entry point → Deploy

**Limitation to know:** Streamlit Community Cloud's filesystem can reset on
redeploy/sleep, wiping the SQLite file. For always-on production use with real
concurrent users, the next step is swapping `db.py`'s sqlite3 calls for a hosted
Postgres database (e.g. Supabase's free tier) — the function signatures are written
so this swap only touches one file. Ask me when you're ready for that step.

## 9. Roadmap / possible next steps

- Move from SQLite to Supabase/Postgres for production multi-user use
- Add validation rules specific to your ops (e.g. DV Inroute + DV Utilised shouldn't
  exceed Total DV, if that's a real constraint)
- Persist the dark/light theme choice across restarts (currently resets to light)
- Per-user logins if you want stronger accountability beyond the free-text
  "updater name" / "corrected by" fields
