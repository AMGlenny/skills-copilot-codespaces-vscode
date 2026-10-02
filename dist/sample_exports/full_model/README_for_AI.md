# Full data model

Every table in the model, for Power BI, Excel or AI tools. Approved values only; review comments, wellbeing and the audit log are never included.

The folder name and `export_info.txt` say when the export ran and what filter was used.

## Files

- `measures.csv` (sheet `measures` in the Excel file): One row per measure. Retired measures stay, with their history.
- `periods.csv` (sheet `periods` in the Excel file): Central calendar. Every value joins to one period. Term rows are edited here by admins.
- `measure_roles.csv` (sheet `measure_roles` in the Excel file): Who owns, updates and approves each measure. A measure can have several updaters.
- `people.csv` (sheet `people` in the Excel file): Everyone who uses the system.
- `org_units.csv` (sheet `org_units` in the Excel file): Workstream, team and sub-team hierarchy. Feeds every team dropdown.
- `groups.csv` (sheet `groups` in the Excel file): Themes, programmes and objectives that measures and work contribute to.
- `measure_links.csv` (sheet `measure_links` in the Excel file): Many-to-many links between measures and groups.
- `reference_values.csv` (sheet `reference_values` in the Excel file): Optional targets, tolerances, baselines and capacities. Zero or more per measure per period.
- `submissions.csv` (sheet `submissions` in the Excel file): One row per measure per period. Created as not_started when the period ends.
- `approved_values.csv` (sheet `approved_values` in the Excel file): Every version of every value. Drafts are edited in place; each resubmission after a return is a new version.
- `values_flat.csv` (sheet `values_flat` in the Excel file): Flat, read-only reporting table: one row per approved measure per period with every lookup filled in. Rebuilt by flows; export straight from here.
- `weekly_updates.csv` (sheet `weekly_updates` in the Excel file): One row per person per week: successes, communication and workload.
- `tasks.csv` (sheet `tasks` in the Excel file): One row per task for its whole life. Open tasks carry over each week; nobody re-enters them.
- `problems.csv` (sheet `problems` in the Excel file): One row per problem for its whole life. Open problems carry over each week.
- `data_dictionary.csv` (sheet `data_dictionary`): every column in this export, with its type and meaning.
- `README_for_AI.md`: this file.

## How to read this data

- Every file is tidy: one row per record, one column per field, a single header row, no merged cells and no totals.
- Column names are snake_case and mean the same thing in every file. `data_dictionary.csv` (or the `data_dictionary` sheet) describes every column.
- Dates are `YYYY-MM-DD` (UK dates). Date-times are UTC in ISO 8601, for example `2026-09-30T06:00:00Z`.
- Numbers are plain numbers. A blank cell means there is no value; it never means zero.
- `percent` values are 0 to 100, so 58 means 58%. `gbp` is pounds. `yes_no` is 1 (yes) or 0 (no). `text` measures use `value_text`.
- Only **approved** values are included. Drafts, returned values and reviewer comments are not.
- `measure_code` (for example PM-0007) is the unique key for a measure. `source_ref` is the reference used in the source document and can repeat.
- The financial year runs April to March. `financial_quarter` looks like `2026-27 Q2` (Q1 is April to June).
- `rag_status`: `green` is on or better than target; `amber` is short of target but within tolerance; `red` is off track; `no_target` means no target was set; `no_data` means no value was provided; `not_applicable` means RAG isn't used for that measure.
- `polarity` says whether higher or lower is better. `aggregation_method` says how to combine values into a longer period: sum, average, latest, max or min. `do_not_combine` means the values must not be added up or averaged.
- `is_latest` is true on the most recent approved period for each measure.
- Individual wellbeing, reviewer comments and the audit log are never included in exports.

## How the tables join

| From | Column | To |
|---|---|---|
| any table | `measure_code` | `measures.measure_code` |
| any table | `period_key` | `periods.period_key` |
| measures | `parent_measure_code` | `measures.measure_code` (parent summary measure) |
| submissions, approved_values | `submission_key` | `submissions.submission_key` |
| measure_links | `group_key` | `groups.group_key` |
| measure_roles, weekly_updates | `email` | `people.email` |
| most tables | `org_unit_key` | `org_units.org_unit_key` |
| tasks, problems | `contributes_to_key` | `groups.group_key` or `measures.measure_code` (see `contributes_to_type`) |

`values_flat` already has every lookup filled in, so for most questions it's the only table you need.
