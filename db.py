"""
db.py
All database access for the Truck Utilization Tracker.
Uses SQLite (file-based, zero setup) so you can run this entirely locally in VS Code.
When you're ready to deploy for multiple simultaneous users, swap the sqlite3 calls
here for a Postgres/Supabase connection -- the function signatures below can stay the same.
"""

import sqlite3
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "tracker.db"
DB_PATH.parent.mkdir(exist_ok=True)

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
    ("North", "S4QS", "BD BEVERAGES"),
    ("North", "S4PD", "BD FOODS"),
    ("North", "S4PC", "BD VENTURES NEW"),
    ("South", "S5AH", "BELLBERRIES"),
    ("North", "S4QD", "BHARATIYAM"),
    ("South", "S4RD", "CFA-CHAMRAJNAGAR"),
    ("South", "S4QN", "CHENNAI CFA"),
    ("North", "S4PN", "CRD BF"),
    ("North", "S4SN", "CRD GF"),
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


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plants_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL,
            site_code TEXT NOT NULL,
            plant_name TEXT NOT NULL,
            UNIQUE(site_code)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    # Seed default credential for the data-update login (CHANGE THIS before real use)
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?,?)",
            ("rcplcampa", _hash("campa@123")),
        )

    # Seed the official plant master list (safe to re-run: keyed by site_code)
    cur.executemany(
        "INSERT OR IGNORE INTO plants_master (region, site_code, plant_name) VALUES (?,?,?)",
        PLANTS_MASTER_SEED,
    )

    conn.commit()
    conn.close()


def check_login(username: str, password: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()
    conn.close()
    if row and row["password_hash"] == _hash(password):
        return True
    return False


def get_plants_by_region(region: str):
    """Used to populate the Plant dropdown once a region is chosen."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM plants_master WHERE region=? ORDER BY plant_name", (region,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_plant_id_by_site_code(site_code: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM plants_master WHERE site_code=?", (site_code,)
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def add_entry(plant_id, entry_date, shift, dv_type, total_dv, dv_available, dv_utilised,
              dv_inroute, trips_completed, updated_by, updated_at):
    conn = get_conn()
    conn.execute(
        """INSERT INTO entries
           (plant_id, entry_date, shift, dv_type, total_dv, dv_available, dv_utilised,
            dv_inroute, trips_completed, updated_by, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (plant_id, entry_date, shift, dv_type, total_dv, dv_available, dv_utilised,
         dv_inroute, trips_completed, updated_by, updated_at),
    )
    conn.commit()
    conn.close()


def update_entry(entry_id, total_dv, dv_available, dv_utilised, dv_inroute, trips_completed,
                  updated_by, updated_at):
    """Corrects an existing entry in place (used by the Edit flow)."""
    conn = get_conn()
    conn.execute(
        """UPDATE entries
           SET total_dv=?, dv_available=?, dv_utilised=?, dv_inroute=?, trips_completed=?,
               updated_by=?, updated_at=?
           WHERE id=?""",
        (total_dv, dv_available, dv_utilised, dv_inroute, trips_completed,
         updated_by, updated_at, entry_id),
    )
    conn.commit()
    conn.close()


def delete_entry(entry_id):
    conn = get_conn()
    conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()


def get_entry(entry_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT e.*, p.region, p.site_code, p.plant_name
        FROM entries e JOIN plants_master p ON p.id = e.plant_id
        WHERE e.id=?
    """, (entry_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_entries():
    """One row per plant+DV type: the most recent entry submitted for it (any date/shift)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.region, p.site_code, p.plant_name,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at, e.entry_date, e.shift, e.dv_type
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.id IN (
            SELECT MAX(id) FROM entries GROUP BY plant_id, dv_type
        )
        ORDER BY p.region, p.plant_name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_entry_history(plant_name: str):
    conn = get_conn()
    rows = conn.execute("""
        SELECT e.* FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE p.plant_name = ?
        ORDER BY e.updated_at DESC
    """, (plant_name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_entries_log():
    """Every single submission ever made, newest first -- the full audit log."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT e.id, p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        ORDER BY e.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dates_with_entries():
    """Distinct entry dates that have data, newest first -- for date pickers."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT entry_date FROM entries ORDER BY entry_date DESC"
    ).fetchall()
    conn.close()
    return [r["entry_date"] for r in rows]


def get_entries_for_date(date_str: str):
    """All entries (both shifts, all DV types) logged for a given date -- raw rows,
    used by the Edit/Delete screen so every individual submission is editable."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT e.id, p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date = ?
        ORDER BY e.shift, p.region, p.plant_name
    """, (date_str,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_entries_for_date(date_str: str):
    """One row per plant+DV type for a given date -- collapses 1st Half / 2nd Half
    into a single 'latest submission wins' result, per the requirement that the
    report should not segregate by shift, only show the most recent value.
    Still segregates by DV type, since that's an intentional dimension."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.region, p.site_code, p.plant_name, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed,
               e.updated_by, e.updated_at, e.entry_date, e.shift
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date = ?
        AND e.id IN (
            SELECT MAX(id) FROM entries WHERE entry_date = ? GROUP BY plant_id, dv_type
        )
        ORDER BY p.region, p.plant_name, e.dv_type
    """, (date_str, date_str)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_entries_since(start_date_str: str):
    """All entries from start_date_str through today (inclusive), one row per
    plant+date+shift+dv_type (dedupes edits so corrections are reflected, not
    double-counted, without collapsing different DV types into each other).
    Used by the Professional Dashboard's weekly/monthly trend analytics."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date >= ?
        AND e.id IN (
            SELECT MAX(id) FROM entries GROUP BY plant_id, entry_date, shift, dv_type
        )
        ORDER BY e.entry_date, p.region, p.plant_name
    """, (start_date_str,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_entries_between(start_date_str: str, end_date_str: str):
    """All entries between two dates (inclusive), same dedupe rule as get_entries_since.
    Used for the custom weekly date-range picker and the monthly month picker."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.region, p.site_code, p.plant_name, e.entry_date, e.shift, e.dv_type,
               e.total_dv, e.dv_available, e.dv_utilised, e.dv_inroute, e.trips_completed
        FROM entries e
        JOIN plants_master p ON p.id = e.plant_id
        WHERE e.entry_date >= ? AND e.entry_date <= ?
        AND e.id IN (
            SELECT MAX(id) FROM entries GROUP BY plant_id, entry_date, shift, dv_type
        )
        ORDER BY e.entry_date, p.region, p.plant_name
    """, (start_date_str, end_date_str)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
