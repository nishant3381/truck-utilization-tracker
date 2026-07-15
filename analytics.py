"""
analytics.py
Calculation engine for the Professional Dashboard.

Definitions (as specified):
    Opening DV %          = DV Available for the day / Total DV
    Utilization %          = DV Utilised / DV Available for the day
    Effective Utilization  = Utilization % * Opening DV %
    Trips / DV / Month     = Effective Utilization % * 30
        (a formula-based projection -- no trip-count data is collected;
        this assumes one potential "trip" per DV per day at full effective
        utilization, scaled to a 30-day month)

All percentages are computed at the DAILY level first (summing both shifts'
numbers for that plant/day, or across all plants/regions for pan-India figures),
then averaged across the days in the selected period. This mirrors how a
5-day / weekly / monthly ops review is normally read: an average of daily
snapshots, not a single blended ratio across the whole period.
"""

import pandas as pd


def _safe_ratio(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def build_dashboard_data(entries):
    """entries: list of dicts from db.get_entries_since(), each with
    region, site_code, plant_name, entry_date, shift, total_dv, dv_available, dv_utilised.
    Returns None if there's no data in the period."""
    if not entries:
        return None

    df = pd.DataFrame(entries)

    # ---- Pan-India daily aggregates (combines all plants + both shifts per day) ----
    daily = df.groupby("entry_date").agg(
        total_dv=("total_dv", "sum"),
        dv_available=("dv_available", "sum"),
        dv_utilised=("dv_utilised", "sum"),
    ).reset_index()
    daily["util_pct"] = daily.apply(lambda r: _safe_ratio(r["dv_utilised"], r["dv_available"]), axis=1)
    daily["opening_pct"] = daily.apply(lambda r: _safe_ratio(r["dv_available"], r["total_dv"]), axis=1)
    daily["eff_util"] = daily["util_pct"] * daily["opening_pct"]

    avg_fleet_size = daily["total_dv"].mean()
    avg_utilization_pct = daily["util_pct"].mean() * 100
    avg_opening_pct = daily["opening_pct"].mean() * 100
    avg_eff_util_frac = daily["eff_util"].mean()
    avg_trips_per_dv_month = avg_eff_util_frac * 30  # Effective Utilization % * 30
    days_count = len(daily)

    # ---- Per-plant daily aggregates (combines both shifts for that plant/day) ----
    plant_daily = df.groupby(["plant_name", "region", "site_code", "entry_date"]).agg(
        total_dv=("total_dv", "sum"),
        dv_available=("dv_available", "sum"),
        dv_utilised=("dv_utilised", "sum"),
    ).reset_index()
    plant_daily["util_pct"] = plant_daily.apply(lambda r: _safe_ratio(r["dv_utilised"], r["dv_available"]), axis=1)
    plant_daily["opening_pct"] = plant_daily.apply(lambda r: _safe_ratio(r["dv_available"], r["total_dv"]), axis=1)
    plant_daily["eff_util"] = plant_daily["util_pct"] * plant_daily["opening_pct"]

    plant_avg = plant_daily.groupby(["plant_name", "region", "site_code"]).agg(
        util_pct=("util_pct", "mean"),
        opening_pct=("opening_pct", "mean"),
        eff_util=("eff_util", "mean"),
    ).reset_index().sort_values("util_pct", ascending=False).reset_index(drop=True)

    top5 = plant_avg.head(5)
    bottom5 = plant_avg.tail(5).sort_values("util_pct").reset_index(drop=True)

    # ---- Region scorecard (combines all plants in a region, per day) ----
    region_daily = df.groupby(["region", "entry_date"]).agg(
        total_dv=("total_dv", "sum"),
        dv_available=("dv_available", "sum"),
        dv_utilised=("dv_utilised", "sum"),
    ).reset_index()
    region_daily["util_pct"] = region_daily.apply(lambda r: _safe_ratio(r["dv_utilised"], r["dv_available"]), axis=1)
    region_daily["opening_pct"] = region_daily.apply(lambda r: _safe_ratio(r["dv_available"], r["total_dv"]), axis=1)
    region_daily["eff_util"] = region_daily["util_pct"] * region_daily["opening_pct"]

    region_avg = region_daily.groupby("region").agg(
        util_pct=("util_pct", "mean"),
        opening_pct=("opening_pct", "mean"),
        eff_util=("eff_util", "mean"),
    ).reset_index()

    return dict(
        avg_fleet_size=avg_fleet_size,
        avg_utilization_pct=avg_utilization_pct,
        avg_opening_pct=avg_opening_pct,
        avg_trips_per_dv_month=avg_trips_per_dv_month,
        days_count=days_count,
        daily=daily,
        plant_avg=plant_avg,
        top5=top5,
        bottom5=bottom5,
        region_avg=region_avg,
    )


def generate_highlights(data):
    """Rule-based, PDF-style key highlights. Returns list of (kind, text) tuples,
    kind in {"good", "warning"}."""
    highlights = []
    region_avg = data["region_avg"]

    # Regions converting almost all available DV (order availability isn't the constraint)
    strong = region_avg[region_avg["util_pct"] >= 0.90].sort_values("util_pct", ascending=False)
    if not strong.empty:
        names = " & ".join(strong["region"].tolist())
        vals = " / ".join(f"{v*100:.0f}%" for v in strong["util_pct"])
        highlights.append((
            "good",
            f"{names} convert almost every available DV ({vals}) — order availability is NOT the constraint there."
        ))

    # Opening DV% target check (target: >=50%)
    if data["avg_opening_pct"] < 50:
        mn = data["daily"]["opening_pct"].min() * 100
        mx = data["daily"]["opening_pct"].max() * 100
        trips = data.get("avg_trips_per_dv_month")
        trip_clause = (
            f" ~{trips:.0f} trips/DV/month vs the 15 needed to keep fixed cost per trip on track."
            if trips is not None else ""
        )
        highlights.append((
            "warning",
            f"Opening DV % never reached the 50% target during this period ({mn:.0f}–{mx:.0f}%) — "
            f"DV availability, not order flow, is the binding constraint on fixed-cost recovery."
            f"{trip_clause}"
        ))

    # Idle capacity: weakest plants
    weak = data["bottom5"]
    if not weak.empty:
        names = ", ".join(weak["plant_name"].tolist())
        highlights.append((
            "warning",
            f"{names} left available DVs underutilized this period — placement and order "
            f"alignment at these plants needs immediate focus."
        ))

    return highlights
