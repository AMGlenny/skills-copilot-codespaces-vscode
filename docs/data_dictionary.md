# Data dictionary

_Generated from `pms/schema.py`. Do not edit by hand: change the schema and run `python -m pms build`._

## Measures

### measures

One row per measure. Retired measures stay, with their history.

| column | type | required | notes |
|---|---|---|---|
| `measure_code` | text | yes | **Key** (SharePoint Title column). System key, e.g. PM-0001. Unique. Every other table links on this. |
| `measure_name` | text | yes | Short name of the measure. |
| `source_ref` | text |  | Reference used in the source document, e.g. 1.01. Not unique: parent and child can share it. |
| `source_document` | text |  | Document or framework the measure comes from. |
| `parent_measure_code` | text |  | measure_code of the parent summary measure. Blank for top-level measures. Links to `measures.measure_code`. |
| `description` | long text |  | What the measure tells you, in plain English. |
| `definition` | long text |  | Definition and calculation method. |
| `measure_class` | choice | yes | measure, kpi or okr. Tolerance only applies to kpi and okr. Values: `measure`, `kpi`, `okr`. |
| `measure_type` | choice | yes | summary, output or outcome. Values: `summary`, `output`, `outcome`. |
| `unit` | choice | yes | Unit of the value. percent is stored as 0 to 100 (58 means 58%). gbp is pounds. yes_no is stored as 1 or 0. Values: `number`, `percent`, `gbp`, `count`, `yes_no`, `text`. |
| `decimal_places` | whole number |  | Decimal places to show. Does not change the stored value. |
| `polarity` | choice | yes | Which direction is good. Used for RAG. Values: `higher_is_better`, `lower_is_better`, `neither`. |
| `frequency` | choice | yes | How often a value is recorded. Values: `daily`, `weekly`, `fortnightly`, `monthly`, `quarterly`, `annual`, `calendar_year`, `academic_year`, `term`. |
| `aggregation_method` | choice | yes | How to roll values up to a longer period, e.g. monthly to quarterly. do_not_combine for values that must not be added or averaged. Values: `sum`, `average`, `latest`, `max`, `min`, `do_not_combine`. |
| `expected_lag_days` | whole number |  | Usual days after period end before data is available. Blank means no expectation, so it is never flagged as late. |
| `category` | text |  | Category code from the lookups list. Links to `lookups.code`. |
| `data_source` | text |  | Where the data comes from. |
| `org_unit_key` | text |  | Team that owns the measure. Links to `org_units.org_unit_key`. |
| `status` | choice | yes | active or retired. Measures are never deleted. Values: `active`, `retired`. |
| `retired_date` | date (YYYY-MM-DD) |  | Date the measure was retired. |
| `retired_reason` | long text |  | Why the measure was retired. |

### periods

Central calendar. Every value joins to one period. Term rows are edited here by admins.

| column | type | required | notes |
|---|---|---|---|
| `period_key` | text | yes | **Key** (SharePoint Title column). Period key, e.g. M-2026-09, Q-2026-27-Q2, T-2026-27-AUT. |
| `period_type` | choice | yes | Matches a measure frequency. Values: `daily`, `weekly`, `fortnightly`, `monthly`, `quarterly`, `annual`, `calendar_year`, `academic_year`, `term`. |
| `period_label` | text | yes | Display label, e.g. Q2 2026-27 or Autumn Term 2026. |
| `start_date` | date (YYYY-MM-DD) | yes | First day of the period. |
| `end_date` | date (YYYY-MM-DD) | yes | Last day of the period. |
| `financial_year` | text |  | UK financial year (April to March) containing the start date, e.g. 2026-27. |
| `financial_quarter` | text |  | Financial quarter containing the start date, e.g. 2026-27 Q2. Blank for periods longer than a quarter. |
| `academic_year` | text |  | Academic year (September to August) containing the start date. |
| `calendar_year` | whole number |  | Calendar year containing the start date. |

### measure_roles

Who owns, updates and approves each measure. A measure can have several updaters.

| column | type | required | notes |
|---|---|---|---|
| `role_key` | text | yes | **Key** (SharePoint Title column). measure_code\|email\|role. Unique. |
| `measure_code` | text | yes | Measure. Links to `measures.measure_code`. |
| `email` | text | yes | Person. Links to `people.email`. |
| `role` | choice | yes | owner, updater or approver. Values: `owner`, `updater`, `approver`. |
| `active` | true/false |  | Only active roles give access. |
| `start_date` | date (YYYY-MM-DD) |  | Role start. |
| `end_date` | date (YYYY-MM-DD) |  | Role end. |

### groups

Themes, programmes and objectives that measures and work contribute to.

| column | type | required | notes |
|---|---|---|---|
| `group_key` | text | yes | **Key** (SharePoint Title column). Group key, e.g. TH-JOBS. Unique. |
| `group_name` | text | yes | Name of the theme, programme or objective. |
| `group_type` | choice | yes | theme, programme or objective. Values: `theme`, `programme`, `objective`. |
| `description` | long text |  | What it covers. |
| `active` | true/false |  | Inactive groups are hidden from new entries. |

### measure_links

Many-to-many links between measures and groups.

| column | type | required | notes |
|---|---|---|---|
| `link_key` | text | yes | **Key** (SharePoint Title column). measure_code\|group_key. Unique. |
| `measure_code` | text | yes | Measure. Links to `measures.measure_code`. |
| `group_key` | text | yes | Group. Links to `groups.group_key`. |
| `relationship_type` | choice | yes | primary, contributes_to or related. Values: `primary`, `contributes_to`, `related`. |
| `active` | true/false |  | Inactive links are kept for history. |

### reference_values

Optional targets, tolerances, baselines and capacities. Zero or more per measure per period.

| column | type | required | notes |
|---|---|---|---|
| `ref_key` | text | yes | **Key** (SharePoint Title column). measure_code\|period_key\|ref_type. Unique. |
| `measure_code` | text | yes | Measure. Links to `measures.measure_code`. |
| `period_key` | text | yes | Period. Links to `periods.period_key`. |
| `ref_type` | choice | yes | target, tolerance, baseline or capacity. tolerance only for kpi and okr measures. Values: `target`, `tolerance`, `baseline`, `capacity`. |
| `ref_value` | number | yes | The reference value, in the measure's unit. |
| `notes` | long text |  | Where the value came from. |
| `active` | true/false |  | Inactive values are ignored. |

### submissions

One row per measure per period. Created as not_started when the period ends.

| column | type | required | notes |
|---|---|---|---|
| `submission_key` | text | yes | **Key** (SharePoint Title column). measure_code\|period_key. Unique. |
| `measure_code` | text | yes | Measure. Links to `measures.measure_code`. |
| `period_key` | text | yes | Period the data relates to. Links to `periods.period_key`. |
| `status` | choice | yes | not_started, draft, submitted, returned or approved. Values: `not_started`, `draft`, `submitted`, `returned`, `approved`. |
| `expected_by` | date (YYYY-MM-DD) |  | Period end plus the measure's expected lag. Blank if no lag is set. |
| `current_version` | whole number |  | Latest version number. 0 before anything is entered. |
| `approved_version` | whole number |  | Version used in reports. Blank until first approval. |
| `submitted_date` | date-time (UTC, ISO 8601) |  | When the latest version was submitted. |
| `approved_by` | text |  | Email of the approver. Links to `people.email`. |
| `approved_date` | date-time (UTC, ISO 8601) |  | When it was approved. |

### submission_versions

Every version of every value. Drafts are edited in place; each resubmission after a return is a new version.

| column | type | required | notes |
|---|---|---|---|
| `version_key` | text | yes | **Key** (SharePoint Title column). submission_key\|v<version_no>. Unique. |
| `submission_key` | text | yes | Submission. Links to `submissions.submission_key`. |
| `measure_code` | text | yes | Measure (copied from the submission for filtering). Links to `measures.measure_code`. |
| `period_key` | text | yes | Period (copied from the submission for filtering). Links to `periods.period_key`. |
| `version_no` | whole number | yes | 1, 2, 3 and so on. |
| `value_number` | number |  | The value for all units except text. percent 0 to 100, yes_no 1 or 0. |
| `value_text` | long text |  | The value for text measures only. |
| `value_missing` | true/false |  | Yes if no value could be provided. Narrative then required. |
| `narrative` | long text |  | Updater's commentary. Required if the value is missing or off track. |
| `data_quality` | choice | yes | verified, provisional, estimated or unverified. Values: `verified`, `provisional`, `estimated`, `unverified`. |
| `entered_by` | text | yes | Email of the updater. Links to `people.email`. |
| `entered_date` | date-time (UTC, ISO 8601) | yes | When the value was first entered. |
| `submitted_date` | date-time (UTC, ISO 8601) |  | When this version was submitted. |
| `version_status` | choice | yes | draft, submitted, returned, approved or superseded. Only approved versions flow into reports. Values: `draft`, `submitted`, `returned`, `approved`, `superseded`. |
| `rag_status` | choice |  | RAG worked out at approval using polarity and the period's target and tolerance. Values: `green`, `amber`, `red`, `no_target`, `no_data`, `not_applicable`. |

### review_comments

Reviewer feedback, kept apart from the narrative. Internal only: excluded from standard exports. (excluded from standard exports and AI snapshots)

| column | type | required | notes |
|---|---|---|---|
| `comment_ref` | text | yes | **Key** (SharePoint Title column). Reference, e.g. RC-00001. |
| `submission_key` | text | yes | Submission. Links to `submissions.submission_key`. |
| `version_no` | whole number | yes | Version the comment was made on. |
| `reviewer_email` | text | yes | Reviewer. Links to `people.email`. |
| `action` | choice | yes | returned, approved, reopened or comment. Returning and reopening need a comment. Values: `returned`, `approved`, `reopened`, `comment`. |
| `comment` | long text |  | The comment. Required when returning. |
| `comment_date` | date-time (UTC, ISO 8601) | yes | When the comment was made. |
| `resolved` | true/false |  | Yes once the updater has dealt with it. |
| `resolved_by` | text |  | Who marked it resolved. Links to `people.email`. |
| `resolved_date` | date-time (UTC, ISO 8601) |  | When it was resolved. |

## Weekly work

### org_units

Workstream, team and sub-team hierarchy. Feeds every team dropdown.

| column | type | required | notes |
|---|---|---|---|
| `org_unit_key` | text | yes | **Key** (SharePoint Title column). Key, e.g. WS-JOBS, TM-SDS, ST-SDS-A. Unique. |
| `unit_name` | text | yes | Name as people know it. |
| `unit_level` | choice | yes | workstream, team or sub_team. Values: `workstream`, `team`, `sub_team`. |
| `parent_key` | text |  | Parent unit. Blank for workstreams. Links to `org_units.org_unit_key`. |
| `active` | true/false |  | Inactive units are hidden from new entries. |

### weekly_updates

One row per person per week: successes, communication and workload.

| column | type | required | notes |
|---|---|---|---|
| `update_key` | text | yes | **Key** (SharePoint Title column). email\|week_start. Unique. |
| `email` | text | yes | Person. Links to `people.email`. |
| `week_start` | date (YYYY-MM-DD) | yes | Monday of the week. |
| `org_unit_key` | text | yes | Team at the time of the update. Links to `org_units.org_unit_key`. |
| `successes` | long text |  | Successes had or heard about. |
| `communication` | long text |  | Anything that would help if more widely known. |
| `workload` | choice |  | light, manageable, heavy or overloaded. Values: `light`, `manageable`, `heavy`, `overloaded`. |
| `submitted_at` | date-time (UTC, ISO 8601) | yes | When it was saved. |

### wellbeing_checkins

RESTRICTED. Individual wellbeing, visible only to the person's line manager. People see team counts only. Never exported or sent to AI. (restricted; excluded from standard exports and AI snapshots)

| column | type | required | notes |
|---|---|---|---|
| `checkin_key` | text | yes | **Key** (SharePoint Title column). email\|week_start. Unique. |
| `email` | text | yes | Person. Links to `people.email`. |
| `line_manager_email` | text |  | Line manager at the time of the check-in. Only they can see it. Blank if the person has no line manager, so only they see it. Links to `people.email`. |
| `org_unit_key` | text | yes | Team at the time, for team counts. Links to `org_units.org_unit_key`. |
| `week_start` | date (YYYY-MM-DD) | yes | Monday of the week. |
| `wellbeing` | choice | yes | thriving, ok or struggling. Values: `thriving`, `ok`, `struggling`. |
| `comments` | long text |  | Optional comments. |
| `submitted_at` | date-time (UTC, ISO 8601) | yes | When it was saved. |

### tasks

One row per task for its whole life. Open tasks carry over each week; nobody re-enters them.

| column | type | required | notes |
|---|---|---|---|
| `task_code` | text | yes | **Key** (SharePoint Title column). Key, e.g. TSK-00001. Unique. |
| `task_name` | text | yes | What needs doing. |
| `priority` | choice | yes | must, should or could. Values: `must`, `should`, `could`. |
| `org_unit_key` | text | yes | Team. Links to `org_units.org_unit_key`. |
| `contributes_to_type` | choice |  | group or measure. Blank if it doesn't contribute to anything specific. Values: `group`, `measure`. |
| `contributes_to_key` | text |  | group_key or measure_code this work supports. |
| `contributes_to_note` | long text |  | Optional extra detail on the aim. |
| `raised_by` | text | yes | Who added it. Links to `people.email`. |
| `date_raised` | date (YYYY-MM-DD) | yes | When it was added. |
| `assigned_to` | text |  | Who is doing it. Links to `people.email`. |
| `status` | choice | yes | open, complete or cancelled. Values: `open`, `complete`, `cancelled`. |
| `completed_by` | text |  | Who completed it. Links to `people.email`. |
| `completed_date` | date (YYYY-MM-DD) |  | When it was completed or cancelled. |
| `notes` | long text |  | Notes. |

### problems

One row per problem for its whole life. Open problems carry over each week.

| column | type | required | notes |
|---|---|---|---|
| `problem_code` | text | yes | **Key** (SharePoint Title column). Key, e.g. PRB-00001. Unique. |
| `problem_title` | text | yes | Short title. |
| `problem_statement` | long text |  | What the problem is. |
| `org_unit_key` | text | yes | Team. Links to `org_units.org_unit_key`. |
| `raised_by` | text | yes | Who raised it. Links to `people.email`. |
| `raised_on` | date (YYYY-MM-DD) | yes | When it was raised. |
| `problem_owner` | text |  | Who owns resolving it. Links to `people.email`. |
| `impact` | choice | yes | low, medium or high. Values: `low`, `medium`, `high`. |
| `urgency` | choice | yes | low, medium or high. Values: `low`, `medium`, `high`. |
| `target_resolution_date` | date (YYYY-MM-DD) |  | When it should be resolved by. |
| `status` | choice | yes | open or closed. Values: `open`, `closed`. |
| `closed_date` | date (YYYY-MM-DD) |  | When it was closed. |
| `resolution` | long text |  | How it was resolved. |
| `contributes_to_type` | choice |  | group or measure. Blank if it doesn't contribute to anything specific. Values: `group`, `measure`. |
| `contributes_to_key` | text |  | group_key or measure_code affected. |
| `notes` | long text |  | Context. |

## Shared

### people

Everyone who uses the system.

| column | type | required | notes |
|---|---|---|---|
| `email` | text | yes | **Key** (SharePoint Title column). Work email, lower case. Unique. |
| `display_name` | text | yes | Name shown in the app. |
| `org_unit_key` | text |  | Default team. Pre-fills the weekly update. Links to `org_units.org_unit_key`. |
| `line_manager_email` | text |  | Line manager. Only they can see this person's individual wellbeing responses. Links to `people.email`. |
| `app_role` | choice | yes | admin, standard or viewer. Measure rights come from measure_roles. Values: `admin`, `standard`, `viewer`. |
| `active` | true/false |  | Leavers are made inactive, never deleted. |

### lookups

Editable pick lists that change over time, such as categories.

| column | type | required | notes |
|---|---|---|---|
| `lookup_key` | text | yes | **Key** (SharePoint Title column). lookup_type\|code. Unique. |
| `lookup_type` | choice | yes | Which pick list. Values: `category`, `data_source`. |
| `code` | text | yes | Stored code. |
| `label` | text | yes | Label shown to people. |
| `sort_order` | whole number |  | Order in dropdowns. |
| `active` | true/false |  | Inactive values are hidden from new entries. |

### settings

System settings that admins can change without editing flows.

| column | type | required | notes |
|---|---|---|---|
| `setting_key` | text | yes | **Key** (SharePoint Title column). Setting name. Unique. |
| `setting_value` | text | yes | Value. |
| `description` | long text |  | What the setting does. |

### audit_log

Every create, edit and status change: who, when, old and new value. Written only by flows. (written by flows only; excluded from standard exports and AI snapshots)

| column | type | required | notes |
|---|---|---|---|
| `audit_ref` | text | yes | **Key** (SharePoint Title column). Reference. Flows use AUD- plus a GUID. |
| `list_name` | text | yes | List that changed. |
| `item_key` | text | yes | Key of the item that changed. |
| `action` | choice | yes | create, edit, status_change, reopen or retire. Values: `create`, `edit`, `status_change`, `reopen`, `retire`. |
| `field_name` | text |  | Column that changed. Blank for create. |
| `old_value` | long text |  | Value before. |
| `new_value` | long text |  | Value after. |
| `changed_by` | text | yes | Who made the change. Links to `people.email`. |
| `changed_at` | date-time (UTC, ISO 8601) | yes | When. |

### export_jobs

Scheduled snapshot exports. Admins edit these; a flow runs them.

| column | type | required | notes |
|---|---|---|---|
| `job_code` | text | yes | **Key** (SharePoint Title column). Key, e.g. EXP-FULL-NIGHTLY. Unique. |
| `job_name` | text | yes | Name. |
| `dataset` | choice | yes | full_model, measures, weekly_work or quarter_pack. Values: `full_model`, `measures`, `weekly_work`, `quarter_pack`. |
| `format` | choice | yes | csv, xlsx or both. Values: `csv`, `xlsx`, `both`. |
| `frequency` | choice | yes | daily, weekly, monthly or quarterly. Values: `daily`, `weekly`, `monthly`, `quarterly`. |
| `run_day` | whole number |  | Weekly: 1 (Mon) to 7. Monthly or quarterly: day of month. Ignored for daily. |
| `folder_path` | text | yes | Folder in the snapshots library. |
| `keep_history` | true/false |  | Keep dated copies as well as /latest. Dated copies are always kept for now; automatic clean-up is a later feature. |
| `active` | true/false |  | Only active jobs run. |
| `last_run_at` | date-time (UTC, ISO 8601) |  | Written by the flow. |
| `last_run_status` | text |  | Written by the flow. |

### export_requests

Queue of exports. The apps and the scheduler add a row; the PMSExportRun flow picks it up, writes the files and fills in the link. (excluded from standard exports and AI snapshots)

| column | type | required | notes |
|---|---|---|---|
| `request_ref` | text | yes | **Key** (SharePoint Title column). Reference, e.g. REQ-20261001-0930-ab12. Unique. |
| `dataset` | choice | yes | full_model, measures, weekly_work or quarter_pack. Values: `full_model`, `measures`, `weekly_work`, `quarter_pack`. |
| `job_code` | text |  | The export_jobs row that asked for it. Blank for on-demand exports. Links to `export_jobs.job_code`. |
| `quarter_label` | text |  | For quarter packs: the financial quarter, e.g. 2026-27 Q2. |
| `odata_filter` | long text |  | Optional filter applied to the dataset's main tables, e.g. financial_year eq '2026-27'. |
| `filter_label` | text |  | The filter in plain English, shown in the email and README. |
| `folder_path` | text | yes | Folder in the snapshots library. |
| `requested_by` | text |  | Who asked for it. Blank for scheduled jobs. |
| `requested_at` | date-time (UTC, ISO 8601) | yes | When it was asked for. |
| `status` | choice | yes | queued, running, done or failed. Values: `queued`, `running`, `done`, `failed`. |
| `output_url` | long text |  | Link to the folder holding the files. |
| `message` | long text |  | What happened, including any error. |
| `completed_at` | date-time (UTC, ISO 8601) |  | When it finished. |

## Reporting

### rpt_values

Flat, read-only reporting table: one row per approved measure per period with every lookup filled in. Rebuilt by flows; export straight from here. (written by flows only)

| column | type | required | notes |
|---|---|---|---|
| `submission_key` | text | yes | **Key** (SharePoint Title column). measure_code\|period_key. Unique. |
| `measure_code` | text | yes | Measure. Links to `measures.measure_code`. |
| `measure_name` | text |  | Measure name. |
| `source_ref` | text |  | Source document reference. |
| `parent_measure_code` | text |  | Parent measure. |
| `measure_class` | text |  | measure, kpi or okr. |
| `measure_type` | text |  | summary, output or outcome. |
| `category` | text |  | Category code. |
| `unit` | text |  | Unit. |
| `polarity` | text |  | Polarity. |
| `frequency` | text |  | Frequency. |
| `aggregation_method` | text |  | How to roll up. |
| `owner_name` | text |  | Measure owner. |
| `owner_email` | text |  | Measure owner email. |
| `org_unit_key` | text |  | Owning team. |
| `period_key` | text | yes | Period. Links to `periods.period_key`. |
| `period_type` | text |  | Period type. |
| `period_label` | text |  | Period label. |
| `period_start` | date (YYYY-MM-DD) |  | Period start date. |
| `period_end` | date (YYYY-MM-DD) |  | Period end date. |
| `financial_year` | text |  | Financial year. |
| `financial_quarter` | text |  | Financial quarter. |
| `value_number` | number |  | Approved value (not text measures). |
| `value_text` | long text |  | Approved value (text measures). |
| `value_missing` | true/false |  | Yes if no value was provided. |
| `narrative` | long text |  | Approved narrative. |
| `data_quality` | text |  | Data quality flag. |
| `version_no` | whole number |  | Approved version number. |
| `approved_by` | text |  | Approver email. |
| `approved_date` | date-time (UTC, ISO 8601) |  | Approval time. |
| `target_value` | number |  | Target for the period. |
| `tolerance_value` | number |  | Tolerance for the period (kpi and okr only). |
| `baseline_value` | number |  | Baseline for the period. |
| `capacity_value` | number |  | Capacity or throughput for the period. |
| `rag_status` | text |  | green, amber, red, no_target, no_data or not_applicable. |
| `is_latest` | true/false |  | Yes on the most recent approved period for the measure. |
| `refreshed_at` | date-time (UTC, ISO 8601) |  | When this row was last rebuilt. |

