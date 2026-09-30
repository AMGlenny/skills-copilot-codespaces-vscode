"""Capacity planning: how big each list gets, whether every query stays
inside SharePoint's limits, and how much flow capacity the system uses.

These are estimates from a usage profile, not a load test against a real
tenant. The query catalogue is exact: every filter the apps and flows use
is listed here, and tests/test_capacity.py checks each one against the
schema's indexes.
"""
from dataclasses import dataclass, field

from .schema import LISTS_BY_NAME

LIST_VIEW_THRESHOLD = 5000
POWER_APPS_ROW_LIMIT = 2000


# ---------------------------------------------------------------------------
# Query catalogue. Each entry: where it runs, the list, and the columns it
# filters on (first one = the column SharePoint uses to narrow the list).
# "key" means the list's key (Title) column.
# ---------------------------------------------------------------------------
@dataclass
class Query:
    where: str
    list: str
    columns: list
    returns: str  # rough size of the result, for the report


QUERIES = [
    # Weekly app
    Query("Weekly app: who am I", "people", ["key"], "1 row"),
    Query("Weekly app: has reports", "people", ["line_manager_email", "active"], "a few rows"),
    Query("Weekly app: people list", "people", ["active"], "all active people"),
    Query("Weekly app: teams", "org_units", ["active"], "all teams"),
    Query("Weekly app: contributes-to list", "groups", ["active"], "all groups"),
    Query("Weekly app: contributes-to list", "measures", ["status"], "active measures"),
    Query("Weekly app: my update", "weekly_updates", ["key"], "1 row"),
    Query("Weekly app: my check-in", "wellbeing_checkins", ["key"], "1 row"),
    Query("Weekly app: team tasks", "tasks", ["org_unit_key", "status", "completed_date"], "one team's open tasks"),
    Query("Weekly app: team problems", "problems", ["org_unit_key", "status", "closed_date"], "one team's open problems"),
    Query("Weekly app: team updates", "weekly_updates", ["org_unit_key", "week_start"], "one team, one week"),
    Query("Weekly app: task by code", "tasks", ["key"], "1 row"),
    # Measures app
    Query("Measures app: my roles", "measure_roles", ["email", "active"], "my roles"),
    Query("Measures app: active measures", "measures", ["status"], "active measures"),
    Query("Measures app: open work", "submissions", ["period_end", "status"], "open submissions from the last 13 months"),
    Query("Measures app: period labels", "periods", ["key"], "1 row each"),
    Query("Measures app: export year list", "periods", ["period_type"], "a few rows"),
    Query("Measures app: export quarter list", "periods", ["period_type", "end_date"], "a few rows"),
    Query("Measures app: one value", "submissions", ["key"], "1 row"),
    Query("Measures app: versions", "submission_versions", ["submission_key"], "a few rows"),
    Query("Measures app: comments", "review_comments", ["submission_key"], "a few rows"),
    Query("Measures app: targets", "reference_values", ["measure_code", "period_key", "active"], "up to 4 rows"),
    Query("Measures app: recent values", "rpt_values", ["measure_code"], "one measure's history"),
    Query("Measures app: latest value", "rpt_values", ["measure_code", "is_latest"], "1 row"),
    Query("Measures app: targets screen periods", "periods", ["period_type", "start_date", "end_date"], "one year of periods"),
    Query("Measures app: targets screen existing", "reference_values", ["key"], "1 row"),
    # Flows
    Query("Flows: read one item by key", "submissions", ["key"], "1 row"),
    Query("Flows: read one item by key", "submission_versions", ["key"], "1 row"),
    Query("Flows: read one item by key", "measures", ["key"], "1 row"),
    Query("Flows: read one item by key", "people", ["key"], "1 row"),
    Query("Flows: read one item by key", "periods", ["key"], "1 row"),
    Query("Flows: read one item by key", "settings", ["key"], "1 row"),
    Query("Flows: read one item by key", "rpt_values", ["key"], "1 row"),
    Query("Flows: caller's role", "measure_roles", ["key", "active"], "1 row"),
    Query("Flows: approvers/updaters/owner", "measure_roles", ["measure_code", "role", "active"], "a few rows"),
    Query("Flows: all updaters (reminders)", "measure_roles", ["role", "active"], "all updater roles"),
    Query("PMSReview: targets", "reference_values", ["measure_code", "period_key", "active"], "up to 4 rows"),
    Query("PMSReview: open comments", "review_comments", ["submission_key", "resolved"], "a few rows"),
    Query("PMSReview: current latest", "rpt_values", ["measure_code", "is_latest"], "1 row"),
    Query("PMSCreateExpected: periods just ended", "periods", ["end_date"], "a few rows"),
    Query("PMSCreateExpected: measures by frequency", "measures", ["frequency", "status"], "measures of one frequency"),
    Query("PMSCreateExpected: existing for a period", "submissions", ["period_key"], "up to one per measure"),
    Query("PMSReminders: due soon", "submissions", ["expected_by", "status"], "values due soon"),
    Query("PMSWellbeingView: team", "wellbeing_checkins", ["org_unit_key", "week_start"], "one team, one week"),
    Query("PMSWellbeingView: my reports", "wellbeing_checkins", ["line_manager_email", "week_start"], "a manager's reports, one week"),
    Query("PMSExportScheduler: active jobs", "export_jobs", ["active"], "a few rows"),
    Query("Exports: approved versions", "submission_versions", ["version_status"], "paged"),
    Query("Exports: quarter values", "rpt_values", ["financial_quarter"], "one quarter"),
    Query("Exports: latest values", "rpt_values", ["is_latest"], "one per measure"),
    Query("Exports: measure values by year", "rpt_values", ["financial_year"], "one year"),
    Query("Exports: quarter tasks", "tasks", ["completed_date", "status"], "one quarter plus open"),
    Query("Exports: quarter problems", "problems", ["raised_on", "closed_date", "status"], "one quarter plus open"),
    Query("Exports: quarter updates", "weekly_updates", ["week_start"], "one quarter"),
    Query("Exports: team work", "weekly_updates", ["org_unit_key"], "one team"),
    Query("Exports: team work", "tasks", ["org_unit_key"], "one team"),
    Query("Exports: team work", "problems", ["org_unit_key"], "one team"),
]


def column(list_name, name):
    lst = LISTS_BY_NAME[list_name]
    if name == "key":
        return lst.all_columns[0]
    return next(c for c in lst.columns if c.name == name)


# ---------------------------------------------------------------------------
# Growth estimate
# ---------------------------------------------------------------------------
PERIODS_PER_YEAR = {"daily": 365, "weekly": 52, "fortnightly": 26, "monthly": 12, "quarterly": 4,
                    "annual": 1, "calendar_year": 1, "academic_year": 1, "term": 3}


@dataclass
class Profile:
    """Default usage: a little above the 300+ measures and 100+ users given."""
    measures_by_frequency: dict = field(default_factory=lambda: dict(
        daily=10, weekly=30, fortnightly=10, monthly=150, quarterly=80, annual=35,
        calendar_year=5, academic_year=5, term=10))
    users: int = 130
    teams: int = 25
    years: int = 5
    versions_per_value: float = 1.2       # returns create extra versions
    comments_per_value: float = 0.2
    audit_rows_per_value: float = 9       # creates, edits and status changes
    roles_per_measure: float = 3.5
    groups_per_measure: float = 1.5
    targets_share: float = 0.6            # share of measure-periods with a target
    tolerance_share: float = 0.3          # share with a tolerance (KPIs and OKRs)
    weekly_update_rate: float = 0.85      # share of people updating each week
    tasks_per_person_week: float = 1.5
    problems_per_team_week: float = 0.6
    exports_per_week: int = 20            # on-demand plus scheduled

    @property
    def measures(self):
        return sum(self.measures_by_frequency.values())

    @property
    def values_per_year(self):
        return sum(PERIODS_PER_YEAR[f] * n for f, n in self.measures_by_frequency.items())


def rows_per_year(p):
    v = p.values_per_year
    return {
        "periods": sum(PERIODS_PER_YEAR.values()),
        "submissions": v,
        "submission_versions": round(v * p.versions_per_value),
        "review_comments": round(v * p.comments_per_value),
        "reference_values": round(v * (p.targets_share + p.tolerance_share)),
        "rpt_values": v,
        "audit_log": round(v * p.audit_rows_per_value),
        "weekly_updates": round(p.users * 52 * p.weekly_update_rate),
        "wellbeing_checkins": round(p.users * 52 * p.weekly_update_rate),
        "tasks": round(p.users * 52 * p.tasks_per_person_week),
        "problems": round(p.teams * 52 * p.problems_per_team_week),
        "export_requests": p.exports_per_week * 52,
    }


def fixed_rows(p):
    return {
        "measures": p.measures, "measure_roles": round(p.measures * p.roles_per_measure),
        "measure_links": round(p.measures * p.groups_per_measure), "people": p.users,
        "org_units": p.teams + 10, "groups": 30, "lookups": 40, "settings": 20, "export_jobs": 5,
    }


def open_submissions(p):
    """Rough count of open (not approved) submissions at any time: about two
    periods per measure are open, plus a week of daily values."""
    daily = p.measures_by_frequency.get("daily", 0)
    return (p.measures - daily) * 2 + daily * 7


# ---------------------------------------------------------------------------
# Flow usage estimate (actions per day), to compare with licence limits
# ---------------------------------------------------------------------------
def full_export_rows(p, year=None):
    """Rows in the nightly full_model export after `year` years (default: the horizon)."""
    y = year or p.years
    r = rows_per_year(p)
    per_year = (r["submissions"] + r["submissions"] + r["rpt_values"] + r["reference_values"]
                + r["weekly_updates"] + r["tasks"] + r["problems"] + r["periods"])  # approved_values ~ one per submission
    return per_year * y + sum(fixed_rows(p).values())


def flow_actions_per_day(p):
    v_per_day = p.values_per_year / 365
    # Each value: one save and one submit (~30 actions each), one review (~60).
    entry = v_per_day * p.versions_per_value * (30 + 30 + 60)
    # Expected submissions: per ending period, one read of existing rows plus a create
    # and an audit row per measure; spread over the year.
    expected = v_per_day * 3 + 40
    reminders = (p.users * 8 + 20) / 7
    # Nightly full export: about five actions and one script run per 1,000 rows per table.
    export_pages = full_export_rows(p) / 1000 + 14
    exports = export_pages * 5 + 60 + p.exports_per_week / 7 * 40
    weekly_app = p.users * 0.3 * 12  # wellbeing view calls
    return {
        "Value entry and review (PMSSaveValue, PMSReview)": round(entry),
        "Expected submissions (PMSCreateExpected)": round(expected),
        "Reminders (PMSReminders)": round(reminders),
        "Exports (PMSExportRun, PMSExportScheduler)": round(exports),
        "Wellbeing view (PMSWellbeingView)": round(weekly_app),
    }, round(export_pages + p.exports_per_week / 7 * 6)


def report(p=None):
    p = p or Profile()
    per_year = rows_per_year(p)
    fixed = fixed_rows(p)
    lines = [
        "# Capacity and limits", "",
        "_Generated by `python -m pms build` from `pms/capacity.py`. These are estimates from a usage profile, "
        "not a load test against your tenant. Change the profile in that file to match reality and rebuild._", "",
        "## Usage profile", "",
        f"- {p.measures} measures: " + ", ".join(f"{n} {f.replace('_', ' ')}" for f, n in p.measures_by_frequency.items()),
        f"- {p.users} people in {p.teams} teams",
        f"- {p.values_per_year:,} values a year",
        f"- Planning horizon: {p.years} years", "",
        "## How big each list gets", "",
        f"SharePoint's list view threshold is {LIST_VIEW_THRESHOLD:,} items. Going over it is fine **as long as every "
        "query filters on an indexed column first** (checked below). Indexes are created at setup, while lists are "
        "empty; that matters because SharePoint won't add an index through the browser once a list passes 20,000 items.", "",
        "| List | Rows a year | After " + f"{p.years} years | Over {LIST_VIEW_THRESHOLD:,}? |", "|---|---:|---:|---|",
    ]
    for name, n in sorted(per_year.items(), key=lambda kv: -kv[1]):
        total = n * p.years
        year_over = next((y for y in range(1, p.years + 1) if n * y > LIST_VIEW_THRESHOLD), None)
        lines.append(f"| {name} | {n:,} | {total:,} | {'from year ' + str(year_over) if year_over else 'no'} |")
    for name, n in fixed.items():
        lines.append(f"| {name} | (fixed) | {n:,} | no |")
    lines += ["", "SharePoint allows 30 million items per list, so size itself is never the problem; queries are.", "",
              "## Every query, checked against the indexes", "",
              "Every filter the apps and flows use. A query is safe on a big list when the first column it filters on "
              "is indexed and narrows the result well below 5,000 rows. `tests/test_capacity.py` fails if any "
              "column here isn't indexed.", "",
              "| Where | List | Filters on | Returns |", "|---|---|---|---|"]
    for q in QUERIES:
        cols = ", ".join(f"`{column(q.list, c).name}`" for c in q.columns)
        lines.append(f"| {q.where} | {q.list} | {cols} | {q.returns} |")
    open_now = open_submissions(p)
    lines += ["", "## Power Apps row limit", "",
              f"The apps' data row limit is {POWER_APPS_ROW_LIMIT:,}. The only collection that could approach it is the "
              f"measures app's open work list. At this profile about **{open_now:,}** submissions are open at any "
              "time. The app only loads open submissions for periods that ended in the last 13 months "
              "(`period_end`), so values abandoned long ago can't push it over the limit. Admins can see those in "
              "the `expected_not_received` view in SharePoint.", "",
              f"Active measures ({p.measures}), people ({p.users}) and teams are all well under the limit.", ""]
    actions, script_runs = flow_actions_per_day(p)
    total = sum(actions.values())
    lines += ["## Power Automate usage", "",
              "Rough actions per day, averaged over a year:", "",
              "| Flow | Actions a day |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |" for k, v in actions.items()]
    lines += [f"| **Total** | **{total:,}** |", "",
              f"Office Script runs: about {script_runs:,} a day, against a limit of about 1,600 a day per account.", "",
              f"These figures are for year {p.years}. The nightly full export grows with history: about "
              f"{full_export_rows(p, 1):,} rows after one year and {full_export_rows(p):,} after {p.years}. If that ever "
              "becomes a problem, change EXP-FULL-NIGHTLY in `export_jobs` to weekly. That cuts its share by six "
              "sevenths, and nothing else needs to change.", "",
              "Microsoft sets daily limits on Power Platform requests per licence, and changes them from time to time. "
              f"At this profile the system uses roughly {total:,} actions a day. Some of these count against the person "
              "using the app and some against the flow owner, depending on how the flow is triggered. Check the current "
              "limits for your licences with IT. If the service account gets throttled (flows slow down rather than "
              "fail), the fix is a Power Automate Process licence for the busiest flows, not a redesign.", ""]
    return "\n".join(lines)
