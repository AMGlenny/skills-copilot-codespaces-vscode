# Performance Management System

A performance management system built on Microsoft 365. It has two parts:

- **Measures:** formal measures, targets and approved values, with a full audit trail.
- **Weekly work:** a light daily or weekly log of tasks, problems, successes and workload.

Because the work is logged as it happens, quarterly reports can be put together, or drafted by AI, from data that already exists. There's no quarterly scramble to collect it.

It runs on SharePoint Online lists for the data, two Power Apps canvas apps (weekly updates, and measures), Power Automate for the rules, notifications, reminders and scheduled exports, and an Office Script that writes the Excel exports.

## Principles

- **Submit once, use many times.** Every value is entered in one place and reused everywhere.
- **Keep it simple.** Only essential features are built. Everything else is on the "later" list.
- **Data first.** The data model is clean, consistent and exportable, and the interface sits on top.

## Status

| Phase | Scope | Status |
|---|---|---|
| 1. Data foundation | Lists, columns, indexes, views, periods, sample data, data dictionary, setup | **Done** |
| 2. Weekly updates app | Daily and weekly tool for tasks, problems, successes, workload and wellbeing | **Done**: [build guide](docs/weekly_app_guide.md) |
| 3. Measures app | Entry, review, versions, audit, notifications, reminders, RAG, target setting | **Done**: [build guide](docs/measures_app_guide.md) |
| 4. Exports | On-demand CSV and xlsx with a data dictionary, scheduled snapshots, quarterly report pack, AI prompt template | **Done**: [exports guide](docs/exports_guide.md) |
| 5. Hardening | Query and index checks, capacity estimates, WCAG 2.2 AA checks, go-live checklist, runbook, automated checks on every push | **Done**: [capacity](docs/capacity_and_limits.md), [accessibility](docs/accessibility.md), [go-live](docs/go_live_checklist.md), [operations](docs/operations.md) |

Next: build it in your tenant, using the [go-live checklist](docs/go_live_checklist.md).

## Getting started

1. Follow [docs/setup_guide.md](docs/setup_guide.md). One Power Automate flow creates everything on your SharePoint site and loads the sample data. No IT request or premium licence is needed.
2. Read [docs/data_model.md](docs/data_model.md) for how the data fits together.
3. Build the weekly updates app with [docs/weekly_app_guide.md](docs/weekly_app_guide.md).
4. Build the measures app and its flows with [docs/measures_app_guide.md](docs/measures_app_guide.md).
5. Set up exports and snapshots with [docs/exports_guide.md](docs/exports_guide.md) and [flows/export_run.md](flows/export_run.md).
6. To add a measure, see [docs/adding_a_measure.md](docs/adding_a_measure.md).
7. Before going live, work through [docs/go_live_checklist.md](docs/go_live_checklist.md). After that, [docs/operations.md](docs/operations.md) covers the routine jobs and what to do when something goes wrong.

## What's in the repository

| Path | What it is |
|---|---|
| `pms/schema.py` | **Single source of truth** for every list, column, choice and view |
| `pms/periods.py` | Period calendar: financial year (Apr to Mar), calendar year, academic year, terms, weeks, fortnights |
| `pms/rules.py` | Business rules (RAG, validation, expected-by dates, weekly carry-forward, wellbeing visibility). The apps and flows must match these. |
| `pms/workflow.py` | The approval workflow (who can do what, versions, audit, reporting rows, scheduled jobs). The flows mirror it step by step. |
| `pms/seed.py` | Fictional sample data covering every frequency and workflow state |
| `pms/exports.py` | Export datasets, the tidy-file rules, the README for AI and the quarterly report prompt |
| `pms/sharepoint.py`, `pms/docs.py` | Generators for the setup requests, data dictionary and diagram |
| `dist/setup/*.json` | Setup requests, run by the setup flow or the PnP script |
| `dist/seed_csv/*.csv` | Sample data as tidy CSV, one file per table. Handy for testing Power BI. |
| `dist/exports/export_definitions.json` | What the export flow reads. Upload it to `/snapshots/_config/`. |
| `dist/sample_exports/` | What each export looks like, built from the sample data. Try Power BI or Copilot on these. |
| `office_scripts/PMSExport.ts` | Office Script that writes the Excel and CSV files. Checked against the Python version by the tests. |
| `dist/data_dictionary.csv` | Every column, with its type, allowed values and links |
| `docs/` | Guides, data model, generated data dictionary and diagram |
| `powerapps/weekly/`, `powerapps/measures/` | The two apps: app formulas and screens as YAML to paste into Power Apps Studio |
| `flows/` | Step-by-step builds for Power Automate flows |
| `scripts/Invoke-PmsSetup.ps1` | PnP PowerShell alternative to the setup flow |
| `pms/capacity.py` | Every query the apps and flows make, checked against the indexes, plus growth and flow-usage estimates |
| `tests/` | Checks on the schema, rules, workflow, data, app source, accessibility, exports and capacity. They run on every push (`.github/workflows/pms-checks.yml`). |

## Changing the data model

Edit `pms/schema.py` (and `pms/seed.py` if the sample data needs to change). Then rebuild and test:

```bash
python -m pms build
python -m unittest discover -s tests
```

The build regenerates everything in `dist/`, `docs/data_dictionary.md` and `docs/data_model_diagram.md`. It needs Python 3.9 or later. The app source checks also need PyYAML (`pip install pyyaml`); without it they are skipped.

The tests check, among other things:
- every link points at a real row
- periods don't overlap
- every measure has exactly one owner
- tolerances only exist on KPIs and OKRs
- off-track or missing values have a narrative
- no "N/A" placeholders appear anywhere
- the sample data covers every frequency, status and RAG value

## Key decisions

- **Linking and access**
  - Tables link through readable text keys, not lookup columns.
  - Each list's Title column is renamed to its key.
  - Measures data is read-only for people. Writes go through flows (phase 3), so the "only the updater edits the value" rule and the audit trail can't be bypassed.
  - Weekly work is written by the app directly. SharePoint item-level permissions stop people editing someone else's update, a "no delete" permission level stops deletions, and version history is the audit trail. This keeps the daily tool quick.
- **Measures**
  - `measure_code` (e.g. PM-0007) is the system key.
  - `source_ref` keeps the document's own reference, which can repeat (parent and child can both be "1.01").
  - Tolerance only applies to KPIs and OKRs.
- **Values**
  - No due dates, because data is lagged. Each measure has an optional expected lag, and anything past it shows as "expected, not received".
  - Percent is stored as 0 to 100: 58 means 58%.
  - Data quality flags are verified, provisional, estimated and unverified.
- **Wellbeing** is kept in its own restricted list:
  - Only the line manager sees individual responses.
  - Everyone else sees team counts, and only for teams where at least 5 people responded.
  - It's never exported or sent to AI.
- **AI and exports**
  - AI and Power BI read tidy snapshot files: CSV plus xlsx, a data dictionary and a plain-English README.
  - Nothing depends on a particular Copilot feature, so another AI tool can use the files if Microsoft changes Copilot.

## Later (deliberately not built)

- App screens for editing measures, people, roles and periods (admins use the SharePoint list forms for now)
- Automatic roll-up of child values into parent measures
- Formatted report packs (PDF or Word)
- Power BI template with ready-made visuals
- Trend charts inside the app
- Targets set as a percentage change on baseline
- Bulk CSV import for updaters
- Delegation cover during leave
- Teams adaptive-card approvals
- Multi-level approvals
- Change requests for measure definitions
- Automatic priority score from impact and urgency
- Weekly progress notes on tasks
- Copilot Studio agent
- Automatic clean-up of old dated snapshot folders
- Migration from the old Meeting Submission Tool
