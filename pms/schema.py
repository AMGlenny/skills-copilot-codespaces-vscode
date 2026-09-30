"""Single source of truth for the SharePoint data model.

Every list, column, choice value and view is defined here once. The setup
requests, PnP script, seed files, data dictionary and diagram are all
generated from this file, so change it here and rebuild.

Naming rules
- List names and column names are snake_case.
- Column internal names AND display names are the same snake_case value, so
  SharePoint's own "Export to CSV", the Power BI SharePoint connector and
  Power Apps all show the export column names without renaming.
- Each list's built-in Title column is renamed to that list's key column
  (for example measure_code), so no value is stored twice.
- Tables link through text keys, never SharePoint lookup columns.
"""
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Choice values (codes are stored; the app shows friendly labels)
# ---------------------------------------------------------------------------
FREQUENCIES = [
    "daily", "weekly", "fortnightly", "monthly", "quarterly",
    "annual", "calendar_year", "academic_year", "term",
]
UNITS = ["number", "percent", "gbp", "count", "yes_no", "text"]
POLARITIES = ["higher_is_better", "lower_is_better", "neither"]
MEASURE_CLASSES = ["measure", "kpi", "okr"]
MEASURE_TYPES = ["summary", "output", "outcome"]
AGGREGATION_METHODS = ["sum", "average", "latest", "max", "min", "none"]
MEASURE_STATUSES = ["active", "retired"]
ROLES = ["owner", "updater", "approver"]
APP_ROLES = ["admin", "standard", "viewer"]
GROUP_TYPES = ["theme", "programme", "objective"]
RELATIONSHIP_TYPES = ["primary", "contributes_to", "related"]
REF_TYPES = ["target", "tolerance", "baseline", "capacity"]
SUBMISSION_STATUSES = ["not_started", "draft", "submitted", "returned", "approved"]
VERSION_STATUSES = ["draft", "submitted", "returned", "approved", "superseded"]
DATA_QUALITY = ["verified", "provisional", "estimated", "unverified"]
RAG_STATUSES = ["green", "amber", "red", "no_target", "no_data", "not_applicable"]
REVIEW_ACTIONS = ["returned", "approved", "comment"]
AUDIT_ACTIONS = ["create", "edit", "status_change", "reopen", "retire"]
UNIT_LEVELS = ["workstream", "team", "sub_team"]
WORKLOAD = ["light", "manageable", "heavy", "overloaded"]
WELLBEING = ["thriving", "ok", "struggling"]
PRIORITIES = ["must", "should", "could"]
TASK_STATUSES = ["open", "complete", "cancelled"]
PROBLEM_STATUSES = ["open", "closed"]
LEVELS = ["low", "medium", "high"]
CONTRIBUTES_TO_TYPES = ["group", "measure", "none"]
LOOKUP_TYPES = ["category", "data_source"]
EXPORT_DATASETS = ["full_model", "measures", "weekly_work", "quarter_pack"]
EXPORT_FORMATS = ["csv", "xlsx", "both"]
EXPORT_FREQUENCIES = ["daily", "weekly", "monthly", "quarterly"]


@dataclass
class Col:
    name: str
    type: str  # text, note, number, integer, bool, date, datetime, choice
    description: str
    required: bool = False
    indexed: bool = False
    choices: list = None
    default: object = None
    ref: str = None  # "list.key_column" this column points to


@dataclass
class View:
    name: str
    columns: list
    where: str  # CAML <Where> inner XML, "" for none
    order_by: str = "Title"
    ascending: bool = True


@dataclass
class ListDef:
    name: str
    domain: str  # measures, weekly_work, shared, reporting
    description: str
    key: str  # the renamed Title column
    key_description: str
    columns: list
    unique_key: bool = True
    key_required: bool = True
    views: list = field(default_factory=list)
    restricted: bool = False  # extra permissions step, excluded from search/AI
    generated: bool = False  # written only by flows, never by people
    exported: bool = True  # included in standard exports and AI snapshots

    @property
    def all_columns(self):
        key = Col(self.key, "text", self.key_description,
                  required=self.key_required, indexed=True)
        return [key] + self.columns


def _eq(col, value, type_="Choice"):
    return (f"<Eq><FieldRef Name='{col}'/>"
            f"<Value Type='{type_}'>{value}</Value></Eq>")


LISTS = [
    # ------------------------------------------------------------------
    # Measures domain
    # ------------------------------------------------------------------
    ListDef(
        "measures", "measures",
        "One row per measure. Retired measures stay, with their history.",
        "measure_code", "System key, e.g. PM-0001. Unique. Every other table links on this.",
        [
            Col("measure_name", "text", "Short name of the measure.", required=True),
            Col("source_ref", "text", "Reference used in the source document, e.g. 1.01. Not unique: parent and child can share it.", indexed=True),
            Col("source_document", "text", "Document or framework the measure comes from."),
            Col("parent_measure_code", "text", "measure_code of the parent summary measure. Blank for top-level measures.", indexed=True, ref="measures.measure_code"),
            Col("description", "note", "What the measure tells you, in plain English."),
            Col("definition", "note", "Definition and calculation method."),
            Col("measure_class", "choice", "measure, kpi or okr. Tolerance only applies to kpi and okr.", required=True, choices=MEASURE_CLASSES, default="measure", indexed=True),
            Col("measure_type", "choice", "summary, output or outcome.", required=True, choices=MEASURE_TYPES, default="output"),
            Col("unit", "choice", "Unit of the value. percent is stored as 0 to 100 (58 means 58%). gbp is pounds. yes_no is stored as 1 or 0.", required=True, choices=UNITS),
            Col("decimal_places", "integer", "Decimal places to show. Does not change the stored value.", default=0),
            Col("polarity", "choice", "Which direction is good. Used for RAG.", required=True, choices=POLARITIES),
            Col("frequency", "choice", "How often a value is recorded.", required=True, choices=FREQUENCIES, indexed=True),
            Col("aggregation_method", "choice", "How to roll values up to a longer period, e.g. monthly to quarterly.", required=True, choices=AGGREGATION_METHODS, default="none"),
            Col("expected_lag_days", "integer", "Usual days after period end before data is available. Blank means no expectation, so it is never flagged as late."),
            Col("category", "text", "Category code from the lookups list.", indexed=True, ref="lookups.code"),
            Col("data_source", "text", "Where the data comes from."),
            Col("org_unit_key", "text", "Team that owns the measure.", indexed=True, ref="org_units.org_unit_key"),
            Col("status", "choice", "active or retired. Measures are never deleted.", required=True, choices=MEASURE_STATUSES, default="active", indexed=True),
            Col("retired_date", "date", "Date the measure was retired."),
            Col("retired_reason", "note", "Why the measure was retired."),
        ],
        views=[
            View("active_measures", ["Title", "measure_name", "source_ref", "measure_class", "unit", "frequency", "category", "org_unit_key"], _eq("status", "active")),
            View("retired_measures", ["Title", "measure_name", "retired_date", "retired_reason"], _eq("status", "retired")),
        ],
    ),
    ListDef(
        "periods", "measures",
        "Central calendar. Every value joins to one period. Term rows are edited here by admins.",
        "period_key", "Period key, e.g. M-2026-09, Q-2026-27-Q2, T-2026-27-AUT.",
        [
            Col("period_type", "choice", "Matches a measure frequency.", required=True, choices=FREQUENCIES, indexed=True),
            Col("period_label", "text", "Display label, e.g. Q2 2026-27 or Autumn Term 2026.", required=True),
            Col("start_date", "date", "First day of the period.", required=True, indexed=True),
            Col("end_date", "date", "Last day of the period.", required=True, indexed=True),
            Col("financial_year", "text", "UK financial year (April to March) containing the start date, e.g. 2026-27.", indexed=True),
            Col("financial_quarter", "text", "Financial quarter containing the start date, e.g. 2026-27 Q2. Blank for periods longer than a quarter."),
            Col("academic_year", "text", "Academic year (September to August) containing the start date."),
            Col("calendar_year", "integer", "Calendar year containing the start date."),
        ],
        views=[
            View("term_dates", ["Title", "period_label", "start_date", "end_date", "academic_year"], _eq("period_type", "term"), order_by="start_date"),
        ],
    ),
    ListDef(
        "measure_roles", "measures",
        "Who owns, updates and approves each measure. A measure can have several updaters.",
        "role_key", "measure_code|email|role. Unique.",
        [
            Col("measure_code", "text", "Measure.", required=True, indexed=True, ref="measures.measure_code"),
            Col("email", "text", "Person.", required=True, indexed=True, ref="people.email"),
            Col("role", "choice", "owner, updater or approver.", required=True, choices=ROLES, indexed=True),
            Col("active", "bool", "Only active roles give access.", default=True, indexed=True),
            Col("start_date", "date", "Role start."),
            Col("end_date", "date", "Role end."),
        ],
    ),
    ListDef(
        "groups", "measures",
        "Themes, programmes and objectives that measures and work contribute to.",
        "group_key", "Group key, e.g. TH-JOBS. Unique.",
        [
            Col("group_name", "text", "Name of the theme, programme or objective.", required=True),
            Col("group_type", "choice", "theme, programme or objective.", required=True, choices=GROUP_TYPES, indexed=True),
            Col("description", "note", "What it covers."),
            Col("active", "bool", "Inactive groups are hidden from new entries.", default=True),
        ],
    ),
    ListDef(
        "measure_links", "measures",
        "Many-to-many links between measures and groups.",
        "link_key", "measure_code|group_key. Unique.",
        [
            Col("measure_code", "text", "Measure.", required=True, indexed=True, ref="measures.measure_code"),
            Col("group_key", "text", "Group.", required=True, indexed=True, ref="groups.group_key"),
            Col("relationship_type", "choice", "primary, contributes_to or related.", required=True, choices=RELATIONSHIP_TYPES),
            Col("active", "bool", "Inactive links are kept for history.", default=True),
        ],
    ),
    ListDef(
        "reference_values", "measures",
        "Optional targets, tolerances, baselines and capacities. Zero or more per measure per period.",
        "ref_key", "measure_code|period_key|ref_type. Unique.",
        [
            Col("measure_code", "text", "Measure.", required=True, indexed=True, ref="measures.measure_code"),
            Col("period_key", "text", "Period.", required=True, indexed=True, ref="periods.period_key"),
            Col("ref_type", "choice", "target, tolerance, baseline or capacity. tolerance only for kpi and okr measures.", required=True, choices=REF_TYPES),
            Col("ref_value", "number", "The reference value, in the measure's unit.", required=True),
            Col("notes", "note", "Where the value came from."),
            Col("active", "bool", "Inactive values are ignored.", default=True),
        ],
    ),
    ListDef(
        "submissions", "measures",
        "One row per measure per period. Created as not_started when the period ends.",
        "submission_key", "measure_code|period_key. Unique.",
        [
            Col("measure_code", "text", "Measure.", required=True, indexed=True, ref="measures.measure_code"),
            Col("period_key", "text", "Period the data relates to.", required=True, indexed=True, ref="periods.period_key"),
            Col("status", "choice", "not_started, draft, submitted, returned or approved.", required=True, choices=SUBMISSION_STATUSES, default="not_started", indexed=True),
            Col("expected_by", "date", "Period end plus the measure's expected lag. Blank if no lag is set.", indexed=True),
            Col("current_version", "integer", "Latest version number. 0 before anything is entered.", default=0),
            Col("approved_version", "integer", "Version used in reports. Blank until first approval."),
            Col("submitted_date", "datetime", "When the latest version was submitted."),
            Col("approved_by", "text", "Email of the approver.", ref="people.email"),
            Col("approved_date", "datetime", "When it was approved."),
        ],
        views=[
            View("awaiting_review", ["Title", "measure_code", "period_key", "current_version", "submitted_date"], _eq("status", "submitted"), order_by="submitted_date"),
            View("returned", ["Title", "measure_code", "period_key", "current_version"], _eq("status", "returned")),
            View("expected_not_received",
                 ["Title", "measure_code", "period_key", "status", "expected_by"],
                 "<And><Or>" + _eq("status", "not_started") + _eq("status", "draft") + "</Or>"
                 "<Lt><FieldRef Name='expected_by'/><Value Type='DateTime'><Today/></Value></Lt></And>",
                 order_by="expected_by"),
        ],
    ),
    ListDef(
        "submission_versions", "measures",
        "Every version of every value. Drafts are edited in place; each resubmission after a return is a new version.",
        "version_key", "submission_key|v<version_no>. Unique.",
        [
            Col("submission_key", "text", "Submission.", required=True, indexed=True, ref="submissions.submission_key"),
            Col("measure_code", "text", "Measure (copied from the submission for filtering).", required=True, indexed=True, ref="measures.measure_code"),
            Col("period_key", "text", "Period (copied from the submission for filtering).", required=True, indexed=True, ref="periods.period_key"),
            Col("version_no", "integer", "1, 2, 3 and so on.", required=True),
            Col("value_number", "number", "The value for all units except text. percent 0 to 100, yes_no 1 or 0."),
            Col("value_text", "note", "The value for text measures only."),
            Col("value_missing", "bool", "Yes if no value could be provided. Narrative then required.", default=False),
            Col("narrative", "note", "Updater's commentary. Required if the value is missing or off track."),
            Col("data_quality", "choice", "verified, provisional, estimated or unverified.", required=True, choices=DATA_QUALITY, default="unverified"),
            Col("entered_by", "text", "Email of the updater.", required=True, indexed=True, ref="people.email"),
            Col("entered_date", "datetime", "When the value was first entered.", required=True),
            Col("submitted_date", "datetime", "When this version was submitted."),
            Col("version_status", "choice", "draft, submitted, returned, approved or superseded. Only approved versions flow into reports.", required=True, choices=VERSION_STATUSES, default="draft", indexed=True),
            Col("rag_status", "choice", "RAG worked out at approval using polarity and the period's target and tolerance.", choices=RAG_STATUSES),
        ],
        views=[
            View("approved_versions", ["Title", "measure_code", "period_key", "version_no", "value_number", "value_text", "rag_status"], _eq("version_status", "approved")),
        ],
    ),
    ListDef(
        "review_comments", "measures",
        "Reviewer feedback, kept apart from the narrative. Internal only: excluded from standard exports.",
        "comment_ref", "Reference, e.g. RC-00001.",
        [
            Col("submission_key", "text", "Submission.", required=True, indexed=True, ref="submissions.submission_key"),
            Col("version_no", "integer", "Version the comment was made on.", required=True),
            Col("reviewer_email", "text", "Reviewer.", required=True, indexed=True, ref="people.email"),
            Col("action", "choice", "returned, approved or comment.", required=True, choices=REVIEW_ACTIONS),
            Col("comment", "note", "The comment. Required when returning."),
            Col("comment_date", "datetime", "When the comment was made.", required=True),
            Col("resolved", "bool", "Yes once the updater has dealt with it.", default=False, indexed=True),
            Col("resolved_by", "text", "Who marked it resolved.", ref="people.email"),
            Col("resolved_date", "datetime", "When it was resolved."),
        ],
        exported=False,
    ),
    # ------------------------------------------------------------------
    # Weekly work domain
    # ------------------------------------------------------------------
    ListDef(
        "org_units", "weekly_work",
        "Workstream, team and sub-team hierarchy. Feeds every team dropdown.",
        "org_unit_key", "Key, e.g. WS-JOBS, TM-SDS, ST-SDS-A. Unique.",
        [
            Col("unit_name", "text", "Name as people know it.", required=True),
            Col("unit_level", "choice", "workstream, team or sub_team.", required=True, choices=UNIT_LEVELS, indexed=True),
            Col("parent_key", "text", "Parent unit. Blank for workstreams.", indexed=True, ref="org_units.org_unit_key"),
            Col("active", "bool", "Inactive units are hidden from new entries.", default=True),
        ],
    ),
    ListDef(
        "people", "shared",
        "Everyone who uses the system.",
        "email", "Work email, lower case. Unique.",
        [
            Col("display_name", "text", "Name shown in the app.", required=True),
            Col("org_unit_key", "text", "Default team. Pre-fills the weekly update.", indexed=True, ref="org_units.org_unit_key"),
            Col("line_manager_email", "text", "Line manager. Only they can see this person's individual wellbeing responses.", indexed=True, ref="people.email"),
            Col("app_role", "choice", "admin, standard or viewer. Measure rights come from measure_roles.", required=True, choices=APP_ROLES, default="standard"),
            Col("active", "bool", "Leavers are made inactive, never deleted.", default=True, indexed=True),
        ],
    ),
    ListDef(
        "weekly_updates", "weekly_work",
        "One row per person per week: successes, communication and workload.",
        "update_key", "email|week_start. Unique.",
        [
            Col("email", "text", "Person.", required=True, indexed=True, ref="people.email"),
            Col("week_start", "date", "Monday of the week.", required=True, indexed=True),
            Col("org_unit_key", "text", "Team at the time of the update.", required=True, indexed=True, ref="org_units.org_unit_key"),
            Col("successes", "note", "Successes had or heard about."),
            Col("communication", "note", "Anything that would help if more widely known."),
            Col("workload", "choice", "light, manageable, heavy or overloaded.", choices=WORKLOAD),
            Col("submitted_at", "datetime", "When it was saved.", required=True),
        ],
    ),
    ListDef(
        "wellbeing_checkins", "weekly_work",
        "RESTRICTED. Individual wellbeing, visible only to the person's line manager. People see team counts only. Never exported or sent to AI.",
        "checkin_key", "email|week_start. Unique.",
        [
            Col("email", "text", "Person.", required=True, indexed=True, ref="people.email"),
            Col("line_manager_email", "text", "Line manager at the time of the check-in. Controls who can see it.", required=True, indexed=True, ref="people.email"),
            Col("org_unit_key", "text", "Team at the time, for team counts.", required=True, indexed=True, ref="org_units.org_unit_key"),
            Col("week_start", "date", "Monday of the week.", required=True, indexed=True),
            Col("wellbeing", "choice", "thriving, ok or struggling.", required=True, choices=WELLBEING),
            Col("comments", "note", "Optional comments."),
            Col("submitted_at", "datetime", "When it was saved.", required=True),
        ],
        restricted=True, exported=False,
    ),
    ListDef(
        "tasks", "weekly_work",
        "One row per task for its whole life. Open tasks carry over each week; nobody re-enters them.",
        "task_code", "Key, e.g. TSK-00001. Unique.",
        [
            Col("task_name", "text", "What needs doing.", required=True),
            Col("priority", "choice", "must, should or could.", required=True, choices=PRIORITIES),
            Col("org_unit_key", "text", "Team.", required=True, indexed=True, ref="org_units.org_unit_key"),
            Col("contributes_to_type", "choice", "group, measure or none.", required=True, choices=CONTRIBUTES_TO_TYPES, default="none"),
            Col("contributes_to_key", "text", "group_key or measure_code this work supports.", indexed=True),
            Col("contributes_to_note", "note", "Optional extra detail on the aim."),
            Col("raised_by", "text", "Who added it.", required=True, indexed=True, ref="people.email"),
            Col("date_raised", "date", "When it was added.", required=True, indexed=True),
            Col("assigned_to", "text", "Who is doing it.", indexed=True, ref="people.email"),
            Col("status", "choice", "open, complete or cancelled.", required=True, choices=TASK_STATUSES, default="open", indexed=True),
            Col("completed_by", "text", "Who completed it.", ref="people.email"),
            Col("completed_date", "date", "When it was completed or cancelled.", indexed=True),
            Col("notes", "note", "Notes."),
        ],
        views=[
            View("open_tasks", ["Title", "task_name", "priority", "org_unit_key", "assigned_to", "date_raised"], _eq("status", "open"), order_by="date_raised"),
        ],
    ),
    ListDef(
        "problems", "weekly_work",
        "One row per problem for its whole life. Open problems carry over each week.",
        "problem_code", "Key, e.g. PRB-00001. Unique.",
        [
            Col("problem_title", "text", "Short title.", required=True),
            Col("problem_statement", "note", "What the problem is."),
            Col("org_unit_key", "text", "Team.", required=True, indexed=True, ref="org_units.org_unit_key"),
            Col("raised_by", "text", "Who raised it.", required=True, indexed=True, ref="people.email"),
            Col("raised_on", "date", "When it was raised.", required=True, indexed=True),
            Col("problem_owner", "text", "Who owns resolving it.", indexed=True, ref="people.email"),
            Col("impact", "choice", "low, medium or high.", required=True, choices=LEVELS),
            Col("urgency", "choice", "low, medium or high.", required=True, choices=LEVELS),
            Col("target_resolution_date", "date", "When it should be resolved by."),
            Col("status", "choice", "open or closed.", required=True, choices=PROBLEM_STATUSES, default="open", indexed=True),
            Col("closed_date", "date", "When it was closed.", indexed=True),
            Col("resolution", "note", "How it was resolved."),
            Col("contributes_to_type", "choice", "group, measure or none.", required=True, choices=CONTRIBUTES_TO_TYPES, default="none"),
            Col("contributes_to_key", "text", "group_key or measure_code affected.", indexed=True),
            Col("notes", "note", "Context."),
        ],
        views=[
            View("open_problems", ["Title", "problem_title", "impact", "urgency", "problem_owner", "raised_on"], _eq("status", "open"), order_by="raised_on"),
        ],
    ),
    # ------------------------------------------------------------------
    # Shared
    # ------------------------------------------------------------------
    ListDef(
        "lookups", "shared",
        "Editable pick lists that change over time, such as categories.",
        "lookup_key", "lookup_type|code. Unique.",
        [
            Col("lookup_type", "choice", "Which pick list.", required=True, choices=LOOKUP_TYPES, indexed=True),
            Col("code", "text", "Stored code.", required=True, indexed=True),
            Col("label", "text", "Label shown to people.", required=True),
            Col("sort_order", "integer", "Order in dropdowns."),
            Col("active", "bool", "Inactive values are hidden from new entries.", default=True),
        ],
    ),
    ListDef(
        "settings", "shared",
        "System settings that admins can change without editing flows.",
        "setting_key", "Setting name. Unique.",
        [
            Col("setting_value", "text", "Value.", required=True),
            Col("description", "note", "What the setting does."),
        ],
    ),
    ListDef(
        "audit_log", "shared",
        "Every create, edit and status change: who, when, old and new value. Written only by flows.",
        "audit_ref", "Reference, e.g. AUD-0000001.",
        [
            Col("list_name", "text", "List that changed.", required=True, indexed=True),
            Col("item_key", "text", "Key of the item that changed.", required=True, indexed=True),
            Col("action", "choice", "create, edit, status_change, reopen or retire.", required=True, choices=AUDIT_ACTIONS),
            Col("field_name", "text", "Column that changed. Blank for create."),
            Col("old_value", "note", "Value before."),
            Col("new_value", "note", "Value after."),
            Col("changed_by", "text", "Who made the change.", required=True, indexed=True, ref="people.email"),
            Col("changed_at", "datetime", "When.", required=True, indexed=True),
        ],
        generated=True, exported=False,
    ),
    ListDef(
        "export_jobs", "shared",
        "Scheduled snapshot exports. Admins edit these; a flow runs them.",
        "job_code", "Key, e.g. EXP-FULL-NIGHTLY. Unique.",
        [
            Col("job_name", "text", "Name.", required=True),
            Col("dataset", "choice", "full_model, measures, weekly_work or quarter_pack.", required=True, choices=EXPORT_DATASETS),
            Col("format", "choice", "csv, xlsx or both.", required=True, choices=EXPORT_FORMATS, default="both"),
            Col("frequency", "choice", "daily, weekly, monthly or quarterly.", required=True, choices=EXPORT_FREQUENCIES),
            Col("run_day", "integer", "Weekly: 1 (Mon) to 7. Monthly or quarterly: day of month. Ignored for daily."),
            Col("folder_path", "text", "Folder in the snapshots library.", required=True),
            Col("keep_history", "bool", "Also keep a dated copy as well as /latest.", default=True),
            Col("active", "bool", "Only active jobs run.", default=True),
            Col("last_run_at", "datetime", "Written by the flow."),
            Col("last_run_status", "text", "Written by the flow."),
        ],
    ),
    # ------------------------------------------------------------------
    # Reporting (generated)
    # ------------------------------------------------------------------
    ListDef(
        "rpt_values", "reporting",
        "Flat, read-only reporting table: one row per approved measure per period with every lookup filled in. Rebuilt by flows; export straight from here.",
        "submission_key", "measure_code|period_key. Unique.",
        [
            Col("measure_code", "text", "Measure.", required=True, indexed=True, ref="measures.measure_code"),
            Col("measure_name", "text", "Measure name."),
            Col("source_ref", "text", "Source document reference."),
            Col("parent_measure_code", "text", "Parent measure."),
            Col("measure_class", "text", "measure, kpi or okr."),
            Col("measure_type", "text", "summary, output or outcome."),
            Col("category", "text", "Category code."),
            Col("unit", "text", "Unit."),
            Col("polarity", "text", "Polarity."),
            Col("frequency", "text", "Frequency."),
            Col("aggregation_method", "text", "How to roll up."),
            Col("owner_name", "text", "Measure owner."),
            Col("owner_email", "text", "Measure owner email."),
            Col("org_unit_key", "text", "Owning team."),
            Col("period_key", "text", "Period.", required=True, indexed=True, ref="periods.period_key"),
            Col("period_type", "text", "Period type."),
            Col("period_label", "text", "Period label."),
            Col("period_start", "date", "Period start date."),
            Col("period_end", "date", "Period end date.", indexed=True),
            Col("financial_year", "text", "Financial year.", indexed=True),
            Col("financial_quarter", "text", "Financial quarter."),
            Col("value_number", "number", "Approved value (not text measures)."),
            Col("value_text", "note", "Approved value (text measures)."),
            Col("value_missing", "bool", "Yes if no value was provided."),
            Col("narrative", "note", "Approved narrative."),
            Col("data_quality", "text", "Data quality flag."),
            Col("version_no", "integer", "Approved version number."),
            Col("approved_by", "text", "Approver email."),
            Col("approved_date", "datetime", "Approval time."),
            Col("target_value", "number", "Target for the period."),
            Col("tolerance_value", "number", "Tolerance for the period (kpi and okr only)."),
            Col("baseline_value", "number", "Baseline for the period."),
            Col("capacity_value", "number", "Capacity or throughput for the period."),
            Col("rag_status", "text", "green, amber, red, no_target, no_data or not_applicable."),
            Col("is_latest", "bool", "Yes on the most recent approved period for the measure.", indexed=True),
            Col("refreshed_at", "datetime", "When this row was last rebuilt."),
        ],
        generated=True,
        views=[
            View("latest_values", ["Title", "measure_name", "period_label", "value_number", "rag_status"], _eq("is_latest", "1", "Boolean")),
        ],
    ),
]

# Document library for scheduled snapshot files.
LIBRARIES = [
    ("snapshots", "Scheduled export files. /latest is overwritten each run; dated folders keep history."),
]

LISTS_BY_NAME = {lst.name: lst for lst in LISTS}


def columns(list_name):
    return {c.name: c for c in LISTS_BY_NAME[list_name].all_columns}
