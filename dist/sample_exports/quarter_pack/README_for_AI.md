# Quarterly report pack

Everything needed to write the quarterly report for one financial quarter: the quarter's approved values, the latest value of every measure, work completed, open work, problems, and successes. Comes with a prompt for drafting the report with AI.

The folder name and `export_info.txt` say when the export ran and what filter was used.

## Files

- `quarter_values.csv` (sheet `quarter_values` in the Excel file): Flat, read-only reporting table: one row per approved measure per period with every lookup filled in. Rebuilt by flows; export straight from here.
- `latest_values.csv` (sheet `latest_values` in the Excel file): Flat, read-only reporting table: one row per approved measure per period with every lookup filled in. Rebuilt by flows; export straight from here.
- `tasks.csv` (sheet `tasks` in the Excel file): One row per task for its whole life. Open tasks carry over each week; nobody re-enters them.
- `problems.csv` (sheet `problems` in the Excel file): One row per problem for its whole life. Open problems carry over each week.
- `weekly_updates.csv` (sheet `weekly_updates` in the Excel file): One row per person per week: successes, communication and workload.
- `data_dictionary.csv` (sheet `data_dictionary`): every column in this export, with its type and meaning.
- `README_for_AI.md`: this file.
- `prompt_quarterly_report.md`: a prompt for drafting the quarterly report from these files.

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

## What's in each table

- `quarter_values`: approved values for periods that start in the quarter (daily, weekly, fortnightly, monthly and quarterly measures).
- `latest_values`: the latest approved value of every measure, which covers annual, calendar-year, academic-year and term measures.
- `tasks`: tasks completed in the quarter, plus everything still open.
- `problems`: problems raised or closed in the quarter, plus everything still open.
- `weekly_updates`: successes, communication and workload from every weekly update in the quarter.
