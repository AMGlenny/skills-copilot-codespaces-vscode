"""Generates rows for the periods list.

Rules
- Financial year runs 1 April to 31 March. Quarters: Q1 Apr-Jun ... Q4 Jan-Mar.
- "annual" means the financial year. "calendar_year" is January to December.
- Academic year runs 1 September to 31 August.
- Weeks run Monday to Sunday and are keyed by their Monday.
- Fortnights run continuously from FORTNIGHT_ANCHOR (a Monday), so they never
  overlap across year boundaries.
- Term dates come from TERM_DATES below. After setup they live only in the
  periods list, where admins edit them.
"""
from datetime import date, timedelta

FORTNIGHT_ANCHOR = date(2025, 4, 7)  # first Monday of FY 2025-26

# Sample Greater Manchester style term dates. Check against your local
# authority calendar and edit the term rows in the periods list.
TERM_DATES = [
    ("2025-26", "AUT", "Autumn Term 2025", date(2025, 9, 3), date(2025, 12, 19)),
    ("2025-26", "SPR", "Spring Term 2026", date(2026, 1, 5), date(2026, 3, 27)),
    ("2025-26", "SUM", "Summer Term 2026", date(2026, 4, 13), date(2026, 7, 22)),
    ("2026-27", "AUT", "Autumn Term 2026", date(2026, 9, 2), date(2026, 12, 18)),
    ("2026-27", "SPR", "Spring Term 2027", date(2027, 1, 4), date(2027, 3, 26)),
    ("2026-27", "SUM", "Summer Term 2027", date(2027, 4, 12), date(2027, 7, 21)),
]


def fy_start_year(d):
    return d.year if d.month >= 4 else d.year - 1


def fy_label(start_year):
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def financial_year(d):
    return fy_label(fy_start_year(d))


def financial_quarter_no(d):
    return ((d.month - 4) % 12) // 3 + 1


def academic_year(d):
    start = d.year if d.month >= 9 else d.year - 1
    return fy_label(start)


def _month_end(year, month):
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return nxt - timedelta(days=1)


def _row(key, ptype, label, start, end):
    short = ptype in ("daily", "weekly", "fortnightly", "monthly", "quarterly")
    return {
        "period_key": key,
        "period_type": ptype,
        "period_label": label,
        "start_date": start,
        "end_date": end,
        "financial_year": financial_year(start),
        "financial_quarter": f"{financial_year(start)} Q{financial_quarter_no(start)}" if short else None,
        "academic_year": academic_year(start),
        "calendar_year": start.year,
    }


def generate(first_fy, last_fy, daily_from_fy=None):
    """Periods for financial years first_fy..last_fy (start years, inclusive).

    Daily periods are only made from daily_from_fy onwards (defaults to
    first_fy) because they are the bulk of the rows.
    """
    rows = []
    range_start = date(first_fy, 4, 1)
    range_end = date(last_fy + 1, 3, 31)

    daily_start = date(daily_from_fy or first_fy, 4, 1)
    d = daily_start
    while d <= range_end:
        rows.append(_row(f"D-{d.isoformat()}", "daily", d.strftime("%d %b %Y"), d, d))
        d += timedelta(days=1)

    # Weeks starting within the range.
    d = range_start + timedelta(days=(7 - range_start.weekday()) % 7)
    while d <= range_end:
        rows.append(_row(f"W-{d.isoformat()}", "weekly", f"w/c {d.strftime('%d %b %Y')}", d, d + timedelta(days=6)))
        d += timedelta(days=7)

    d = FORTNIGHT_ANCHOR
    while d < range_start:
        d += timedelta(days=14)
    while d <= range_end:
        rows.append(_row(f"F-{d.isoformat()}", "fortnightly", f"Fortnight w/c {d.strftime('%d %b %Y')}", d, d + timedelta(days=13)))
        d += timedelta(days=14)

    for fy in range(first_fy, last_fy + 1):
        for i in range(12):
            month = (3 + i) % 12 + 1
            year = fy if month >= 4 else fy + 1
            start = date(year, month, 1)
            rows.append(_row(f"M-{year}-{month:02d}", "monthly", start.strftime("%b %Y"), start, _month_end(year, month)))
        for q in range(1, 5):
            m = 4 + (q - 1) * 3
            year = fy if m <= 12 else fy + 1
            m = (m - 1) % 12 + 1
            start = date(year, m, 1)
            end_month = m + 2
            rows.append(_row(f"Q-{fy_label(fy)}-Q{q}", "quarterly", f"Q{q} {fy_label(fy)}", start, _month_end(year, end_month)))
        rows.append(_row(f"FY-{fy_label(fy)}", "annual", f"FY {fy_label(fy)}", date(fy, 4, 1), date(fy + 1, 3, 31)))

    # Calendar and academic years from the year before the range, so the most
    # recent full year is available for lagged annual data.
    for year in range(first_fy - 1, last_fy + 1):
        rows.append(_row(f"CY-{year}", "calendar_year", str(year), date(year, 1, 1), date(year, 12, 31)))
        ay = fy_label(year)
        rows.append(_row(f"AY-{ay}", "academic_year", f"AY {ay}", date(year, 9, 1), date(year + 1, 8, 31)))

    first_ay, last_ay = fy_label(first_fy), fy_label(last_fy)
    for ay, code, label, start, end in TERM_DATES:
        if first_ay <= ay <= last_ay:
            rows.append(_row(f"T-{ay}-{code}", "term", label, start, end))

    rows.sort(key=lambda r: (r["start_date"], r["period_type"]))
    return rows
