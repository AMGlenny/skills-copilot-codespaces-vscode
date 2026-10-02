# Exports, snapshots and AI

Every value is entered once and then reused here: in exports, in Power BI, and as files that AI tools can read.

## Five ways to get the data out

| Way | Who | What you get |
|---|---|---|
| **Export values** (measures app, All measures tab) | Anyone | The flat values table for one financial year or all years, as CSV and Excel |
| **Quarterly report pack** (measures app, All measures tab) | Anyone | Everything for one quarter, plus the AI report prompt |
| **Export this team's work** (weekly app, My team) | Anyone | The team's weekly updates, tasks and problems |
| **Scheduled snapshots** (`export_jobs`) | Automatic | The full model nightly, weekly work on Mondays, and the quarter pack on the 10th after each quarter, all in `/latest` folders |
| **SharePoint list views** | Anyone with access | **Export**, then **Export to CSV** or **Export to Excel** on any list view. Column names are already snake_case. |

The first four go through the `PMSExportRun` flow. You get an email with a link, usually within a few minutes.

## What every export contains

```
/snapshots/<folder>/<yyyy-MM-dd_HHmm>_<request>/
    <dataset>.xlsx            one sheet (Excel table) per table, plus a data_dictionary sheet
    <table>.csv               one per table, UTF-8
    data_dictionary.csv       every column: table, name, type, description
    README_for_AI.md          plain-English guide to the files, for people and AI
    export_info.txt           when it ran, who asked, what filter
    prompt_quarterly_report.md   quarter packs only
```

Scheduled jobs also copy their files to `/snapshots/<folder>/latest/`. That address never changes, so it's the one to connect Power BI, Excel or Copilot to.

**Tidy rules** (checked automatically by `tests/test_exports.py`):
- **Shape:** one row per record, one header row, and no merged cells, blank rows or totals.
- **Column names:** snake_case, and identical in every file and in the SharePoint lists.
- **Dates:** `YYYY-MM-DD` (UK dates). Date-times are UTC ISO 8601. In Excel both are real dates, not text.
- **Numbers and blanks:** numbers are numbers, and blank means blank, never "N/A".
- **Text codes:** references such as `1.10` or `0012` stay as text, so Excel doesn't turn them into numbers.
- **No joins needed:** lookup columns are filled in (measure name, owner, team name, period label, targets, RAG), so each file works on its own.
- **Approved values only.** Reviewer comments, individual wellbeing and the audit log are never exported.

Examples built from the sample data are in [`dist/sample_exports`](../dist/sample_exports). Open them to see exactly what you'll get.

## Datasets

| Dataset | Tables |
|---|---|
| `measures` | `values_flat` |
| `weekly_work` | `weekly_updates`, `tasks`, `problems` |
| `quarter_pack` | `quarter_values`, `latest_values`, `tasks` (completed in the quarter, plus open), `problems` (raised or closed in the quarter, plus open), `weekly_updates` (the quarter) |
| `full_model` | `measures`, `periods`, `measure_roles`, `people` (without line managers), `org_units`, `groups`, `measure_links`, `reference_values`, `submissions`, `approved_values`, `values_flat`, `weekly_updates`, `tasks`, `problems` |

These are defined once in `pms/exports.py`. To change one, edit that file, run `python -m pms build`, and upload the new `dist/exports/export_definitions.json` to `/snapshots/_config/`. The flows don't need changing.

## Writing the quarterly report with AI

1. **Get the pack.** Wait for the scheduled pack on the 10th of the month after the quarter, or ask for one from the measures app.
2. **Open Copilot** in Word, or Microsoft 365 Copilot chat.
3. **Point it at the files.** Refer to the pack's files (`/` in Copilot, then pick the files), or attach the Excel file.
4. **Paste the prompt.** Paste the text from `prompt_quarterly_report.md` below the line.
5. **Check the draft** against the questions at the end of it, then edit.

The prompt tells the AI to:
- use only the files
- quote measure codes, so every statement can be checked
- never invent numbers
- respect polarity, so a fall in a lower-is-better measure counts as an improvement
- leave individuals' names out of problems and workload

**If Copilot changes, or isn't available:**
- **Any AI tool:** the pack is plain CSV plus Markdown instructions, so any tool your organisation allows can read it.
- **Power BI:** connect to `/snapshots/quarter_pack/latest` (see below).
- **No AI at all:** the Excel file has a sheet for each part of the report (values, work done, problems, successes), so a person can work through it sheet by sheet.

## Power BI

**Option 1: snapshot files** (recommended for most reports).
1. Go to **Get data**, then **SharePoint folder**, and enter the site URL.
2. Filter to the folder path containing `/snapshots/full_model/latest/`.
3. Combine the CSVs you need. `values_flat.csv` is enough for most reports.

**Option 2: live lists.** Go to **Get data**, then **SharePoint Online list**, then **Implementation 2.0**. Load `rpt_values` for a flat table, or the individual lists to build a model. The display names are already snake_case.

**For a star schema:**
- use `values_flat` (or `approved_values`) as the fact table
- use `measures`, `periods`, `org_units` and `groups` as dimensions
- join on `measure_code`, `period_key` and `org_unit_key`

## Scheduling

Edit rows in `export_jobs`:
- `frequency`: daily, weekly, monthly or quarterly
- `run_day`: Monday is 1 and Sunday is 7 for weekly jobs; the day of the month for monthly and quarterly jobs
- `folder_path`
- `active`

To add a new job, add a row. `PMSExportScheduler` picks it up the next morning.
