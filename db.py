"""
db.py
All database access for the Truck Utilization Tracker.

Uses Postgres (a free hosted Supabase project) instead of a local SQLite file.
This matters: a local file lives on the app server's disk, which free hosting
tiers (Streamlit Community Cloud, Render, etc.) can wipe on restart, redeploy,
or after a period of inactivity -- that's what caused the data loss. A hosted
Postgres database is independent of the app server, so it survives all of that.

Every function below has the exact same name and signature as before, so
app.py, analytics.py, and excel_export.py did not need any changes for this swap.

SETUP REQUIRED: this file needs a DATABASE_URL to connect. See README.md
section "Connecting to Postgres (Supabase)" for how to create the free
database and where to put the connection string.
"""

import os
import hashlib
import psycopg2
import psycopg2.extras
import streamlit as st

REGIONS = ["North", "South", "East", "West"]
SHIFTS = ["1st Half (Morning)", "2nd Half (Evening)"]
DV_TYPES = ["10PP", "12PP", "18PP", "9MT", "18MT", "12MT"]

# Official plant master list: (region, site_code, plant_name).
# site_code is the true unique key -- SILVASSA legitimately appears twice under
# two different sites, so plant_name alone cannot be the unique identifier.
PLANTS_MASTER_SEED = [
    ("South", "S4PH", "ABHIRAMI"),
    ("South", "S4UZ", "PARAG"),
    ("East", "S4UP", "KL BEVERAGES"),
    ("North", "S4PC/S4QS", "BD"),
    ("South", "S5AH", "BELLBERRIES"),
    ("North", "S4QD", "BHARATIYAM"),
    ("South", "S4RD", "CFA-CHAMRAJNAGAR"),
    ("South", "S4QN", "CHENNAI CFA"),
    ("North", "S4SN/S4PN", "CRD"),
    ("East", "S4PV", "EPIC AGRO"),
    ("South", "S4PF", "FAVORICH"),
    ("East", "S4SM", "GEO NUTRI"),
    ("West", "S4PR", "GHODAWAT"),
    ("North", "S4PZ", "GREEN HAWK"),
    ("East", "S4PJ", "GREENFIZZ"),
    ("East", "SAN4", "GUWAHATI WAREHOUSE"),
    ("West", "S4QH", "HERSHEY'S"),
    ("South", "SAO6", "HYDERABAD WAREHOUSE"),
    ("West", "S4SD", "JAIN IRRIGATION"),
    ("North", "S4PT", "JALLAN"),
    ("South", "S5AM", "JDM FRUIT PRODUCTS"),
    ("East", "S4PK", "JERICHO"),
    ("West", "S4QQ", "JR FOODS"),
    ("East", "SAK5", "KHORDA WAREHOUSE"),
    ("East", "SAM6", "KOLKATA WAREHOUSE"),
    ("South", "S4RO", "KOVAI AGRO"),
    ("South", "SAJ1", "KURNOOL PLANT"),
    ("North", "SAQ8", "LUCKNOW WAREHOUSE"),
    ("South", "S4PB", "MBCPL"),
    ("North", "S4PI", "NATURE FRESH"),
    ("West", "SARO", "OZPURE"),
    ("North", "S4TJ", "PATNA CFA"),
    ("West", "S4QE", "PUSHPAM"),
    ("North", "S4RP", "RASIK REFRESHMENT"),
    ("West", "SAT8", "CFA-BHIWANDI CSD"),
    ("South", "SAYO", "ICE DROPS"),
    ("West", "S4QV", "SAGAR RATNA"),
    ("West", "S4SV", "SILVASSA"),
    ("West", "SAR6", "SURAT WAREHOUSE"),
    ("West", "S5AA", "SURAT PLANT"),
    ("West", "S5AG", "SURE AND PURE"),
    ("East", "S4PG", "SURYA"),
    ("South", "S4QM", "TIRUMALAGIRI  CFA"),
    ("East", "S4UH", "TRIJAL"),
    ("South", "S4PE", "TRUKSHA"),
    ("South", "SAM4", "CFA-VIJAYAWADA"),
    ("South", "S4PL", "VINAYAKA"),
    ("East", "S4PU", "ZION AQUA"),
    ("North", "SARQ", "DASNA WAREHOUSE"),
    ("West", "S4ST", "BHIWANDI CSD CANS"),
    ("North", "SAO0", "BHAPARODA"),
    ("West", "S4UM", "SILVASSA"),
    ("East", "S4RF", "AMTA WB CFA"),
    ("North", "S4RE", "VARANASI CFA"),
    ("North", "S4TD", "LUCKNOW CFA"),
]


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_database_url() -> str:
    """Reads the Postgres connection string from Streamlit secrets (works on
    Streamlit Cloud and locally via .streamlit/secrets.toml), falling back to
    a plain environment variable DATABASE_URL (works on Render or anywhere
    else that lets you set env vars)."""
    url = st.secrets.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Locally: add it to .streamlit/secrets.toml. "
            "On Streamlit Cloud: add it under your app's Settings -> Secrets. "
            "On Render or elsewhere: set it as an environment variable. "
            "See README.md for the exact connection string to use."
        )
    return url


@st.cache_resource(show_spinner=False)
def _get_shared_conn():
    """One Postgres connection, reused for the lifetime of the app process
    instead of reconnecting over the network on every single query. This is
    the standard Streamlit pattern for external databases (see Streamlit
    docs: 'Connect to a database'). Opening a fresh connection per query was
    the actual cause of the multi-second delays -- each new connection has
    to do a full network round-trip + SSL handshake to Supabase, which is
    fine once, but very slow if repeated for every query on every click."""
    conn = psycopg2.connect(_get_database_url(), cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    return conn


def get_conn():
    """Kept for compatibility -- returns the shared cached connection."""
    return _get_shared_conn()


def _run(fn):
    """Runs fn(conn) against the shared connection. If the connection has
    gone stale (e.g. Supabase's pooler dropped an idle connection), clears
    the cache and retries once with a fresh connection. Any other error
    rolls back so the shared connection isn't left in a broken transaction
    state for the next query."""
    conn = _get_shared_conn()
    try:
        return fn(conn)
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        _get_shared_conn.clear()
        conn = _get_shared_conn()
        return fn(conn)
    except Exception:
        conn.rollback()
        raise


def _fetchall(query, params=()):
    def run(conn):
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    return _run(run)


def _fetchone(query, params=()):
    def run(conn):
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return dict(row) if row else None
    return _run(run)


def _execute(query, params=()):
    def run(conn):
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    return _run(run)


def _executemany(query, param_list):
    def run(conn):
        with conn.cursor() as cur:
            cur.executemany(query, param_list)
        conn.commit()
    return _run(run)


def init_db():
    _execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)

    _execute("""
        CREATE TABLE IF NOT EXISTS plants_master (
            id SERIAL PRIMARY KEY,
            region TEXT NOT NULL,
            site_code TEXT NOT NULL UNIQUE,
            plant_name TEXT NOT NULL
        )
    """)

    _execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            plant_id INTEGER NOT NULL REFERENCES plants_master(id),
            entry_date TEXT NOT NULL,
            shift TEXT NOT NULL,
            dv_type TEXT NOT NULL DEFAULT '',
            total_dv INTEGER NOT NULL,
            dv_available INTEGER NOT NULL,
            dv_utilised INTEGER NOT NULL,
            dv_inroute INTEGER NOT NULL,
            trips_completed INTEGER NOT NULL DEFAULT 0,
            updated_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    _execute("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Seed default credential for the data-update login (CHANGE THIS before real use)
    existing = _fetchone("SELECT COUNT(*) AS c FROM users")
    if existing["c"] == 0:
        _execute(
            "INSERT INTO users (username, password_hash) VALUES (%s,%s)",
            ("rcplcampa", _hash("campa@123")),
        )

    # Seed the official plant master list (safe to re-run: keyed by site_code)
    _executemany(
        "INSERT INTO plants_master (region, site_code, plant_name) VALUES (%s,%s,%s) "
        "ON CONFLICT (site_code) DO NOTHING",
        PLANTS_MASTER_SEED,
    )

    _migrate_consolidate_bd_crd()


def _migrate_consolidate_bd_crd():
    """One-time, idempotent migration: merges the old individual 'BD BEVERAGES' /
    'BD FOODS' / 'BD VENTURES NEW' plants into the single combined 'BD' plant
    (site_code S4PC/S4QS), and the old 'CRD BF' / 'CRD GF' into the single 'CRD'
    (site_code S4SN/S4PN). Any historical entries logged against the old plants
    are reassigned to the new combined plant first, so no data is lost."""
    done = _fetchone("SELECT value FROM schema_meta WHERE key='migrated_bd_crd_v1'")
    if done:
        return

    def _consolidate(old_codes, new_code):
        new_row = _fetchone("SELECT id FROM plants_master WHERE site_code=%s", (new_code,))
        if not new_row:
            return
        new_id = new_row["id"]

        placeholders = ",".join(["%s"] * len(old_codes))
        old_rows = _fetchall(
            f"SELECT id FROM plants_master WHERE site_code IN ({placeholders})", old_codes
        )
        old_ids = [r["id"] for r in old_rows if r["id"] != new_id]
        if not old_ids:
            return

        id_placeholders = ",".join(["%s"] * len(old_ids))
        _execute(
            f"UPDATE entries SET plant_id=%s WHERE plant_id IN ({id_placeholders})",
            [new_id] + old_ids,
        )
        _execute(
            f"DELETE FROM plants_master WHERE id IN ({id_placeholders})", old_ids
        )

    _consolidate(["S4QS", "S4PD", "S4PC"], "S4PC/S4QS")   # -> BD
    _consolidate(["S4PN", "S4SN"], "S4SN/S4PN")             # -> CRD

    _execute(
        "INSERT INTO schema_meta (key, value) VALUES ('migrated_bd_crd_v1', '1') "
        "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value"
    )


def check_login(username: str, password: str):
    row = _fetchone("SELECT * FROM users WHERE username=%s", (username,))
    if row and row["password_hash"] == _hash(password):
        return True
    return False


def get_plants_by_region(region: str):
    """Used to populate the Plant dropdown once a region is chosen."""
    return _fetchall(
        "SELECT * FROM plants_master WHERE region=%s ORDER BY plant_name", (region,)
    )


def get_plant_id_by_site_code(site_code: str):
    row = _fetchone("SELECT id FROM plants_master WHERE site_code=%s", (site_code,))
    return row["id"] if row else None


def entry_exists(plant_id, entry_date, shift, dv_type) -> bool:
    """Checks whether this plant already has an entry for this exact date+shift+DV
    Type combination. Used to block accidental duplicate submissions in Add Entry --
    the user should use Edit/Delete Entries to correct an existing one instead."""
    row = _fetchone(
        """SELECT 1 AS found FROM entries
           WHERE plant_id=%s AND entry_date=%s AND shift=%s AND dv_type=%s
           LIMIT 1""",
        (plant_id, entry_date, shift, dv_type),
    )
    return row is not None


def add_entry(plant_id, entry_date, shift, dv_type, total_dv, dv_available, dv_utilised,
              dv_inroute, updated_by, updated_at, trips_completed=0):
    _execute(
        """INSERT INTO entries
           (plant_id, entry_date, shift, dv_type, total_dv, dv_available, dv_utilised,
            dv_inroute, trips_completed, updated_by, updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (plant_id, entry_date, shift, dv_type, total_dv, dv_available, dv_utilised,
         dv_inroute, trips_completed, updated_by, updated_at),
    )


def update_entry(entry_id, total_dv, dv_available, dv_utilised, dv_inroute,
                  updated_by, updated_at):
    """Corrects an existing entry in place (used by the Edit flow). trips_completed
    is intentionally left untouched -- it's a legacy column, no longer collected
    since Trips/DV/Month is now calculated from Effective Utilization instead."""
    _execute(
        """UPDATE entries
           SET total_dv=%s, dv_available=%s, dv_utilised=%s, dv_inroute=%s,
               updated_by=%s, updated_at=%s
           WHERE id=%s""",
        (total_dv, dv_available, dv_utilised, dv_inroute, updated_by, updated_at, entry_id),
    )


def delete_entry(entry_id):
    _execute("DELETE FROM entries WHERE id=%s", (entry_id,))


def get_entry(entry_id):
    return _fetchone("""
        SELECT e.*, p.region, p.site_code, p.plant_name
        FROM entries e JOIN plants_master p ON p.id = e.plant_id
        WHERE e.id=%s
    """, (entry_id,))


def get_latest_entries():
    """One row per plant+DV type: the most recent entry submitted for it (any date/shift)."""
    return _fetchall("""
        SELECT p.region, p.site_code, p.plant_name,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at, e.entry_date, e.shift, e.dv_type
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.id IN (
            SELECT MAX(id) FROM entries GROUP BY plant_id, dv_type
        )
        ORDER BY p.region, p.plant_name
    """)


def get_entry_history(plant_name: str):
    return _fetchall("""
        SELECT e.* FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE p.plant_name = %s
        ORDER BY e.updated_at DESC
    """, (plant_name,))


def get_all_entries_log():
    """Every single submission ever made, newest first -- the full audit log."""
    return _fetchall("""
        SELECT e.id, p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        ORDER BY e.id DESC
    """)


def get_dates_with_entries():
    """Distinct entry dates that have data, newest first -- for date pickers."""
    rows = _fetchall("SELECT DISTINCT entry_date FROM entries ORDER BY entry_date DESC")
    return [r["entry_date"] for r in rows]


def get_entries_for_date(date_str: str):
    """All entries (both shifts, all DV types) logged for a given date -- raw rows,
    used by the Edit/Delete screen so every individual submission is editable."""
    return _fetchall("""
        SELECT e.id, p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date = %s
        ORDER BY e.shift, p.region, p.plant_name
    """, (date_str,))


def get_latest_entries_for_date(date_str: str):
    """One row per plant+DV type for a given date -- collapses 1st Half / 2nd Half
    into a single 'latest submission wins' result, per the requirement that the
    report should not segregate by shift, only show the most recent value.
    Still segregates by DV type, since that's an intentional dimension."""
    return _fetchall("""
        SELECT p.region, p.site_code, p.plant_name, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at, e.entry_date, e.shift
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date = %s
        AND e.id IN (
            SELECT MAX(id) FROM entries WHERE entry_date = %s GROUP BY plant_id, dv_type
        )
        ORDER BY p.region, p.plant_name, e.dv_type
    """, (date_str, date_str))


def get_entries_since(start_date_str: str):
    """All entries from start_date_str through today (inclusive), one row per
    plant+date+shift+dv_type (dedupes edits so corrections are reflected, not
    double-counted, without collapsing different DV types into each other).
    Used by the Professional Dashboard's weekly/monthly trend analytics."""
    return _fetchall("""
        SELECT p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date >= %s
        AND e.id IN (
            SELECT MAX(id) FROM entries GROUP BY plant_id, entry_date, shift, dv_type
        )
        ORDER BY e.entry_date, p.region, p.plant_name
    """, (start_date_str,))


def get_entries_between(start_date_str: str, end_date_str: str):
    """All entries between two dates (inclusive), same dedupe rule as get_entries_since.
    Used for the custom weekly date-range picker and the monthly month picker."""
    return _fetchall("""
        SELECT p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date >= %s AND e.entry_date <= %s
        AND e.id IN (
            SELECT MAX(id) FROM entries GROUP BY plant_id, entry_date, shift, dv_type
        )
        ORDER BY e.entry_date, p.region, p.plant_name
    """, (start_date_str, end_date_str))
