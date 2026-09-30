# Weekly work

Weekly updates (successes, communication, workload), tasks and problems, with names filled in. Wellbeing is never included.

The folder name and `export_info.txt` say when the export ran and what filter was used.

## Files

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
