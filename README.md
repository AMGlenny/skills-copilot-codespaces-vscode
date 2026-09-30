# Performance Management System

A performance management system built on Microsoft 365. It has two parts:

- **Measures:** formal measures, targets and approved values, with a full audit trail.
- **Weekly work:** a light daily or weekly log of tasks, problems, successes and workload.

Because the work is logged as it happens, quarterly reports can be put together, or drafted by AI, from data that already exists. There's no quarterly scramble to collect it.

It runs on SharePoint Online lists for the data, a Power Apps canvas app for entry and review, and Power Automate for notifications, reminders and scheduled exports.

## Principles

- **Submit once, use many times.** Every value is entered in one place and reused everywhere.
- **Keep it simple.** Only essential features are built. Everything else is on the "later" list.
- **Data first.** The data model is clean, consistent and exportable, and the interface sits on top.

## Status

| Phase | Scope | Status |
|---|---|---|
| 1. Data foundation | Lists, columns, indexes, views, periods, sample data, data dictionary, setup | **Done** (this repository) |
| 2. Weekly updates app | Daily and weekly tool for tasks, problems, successes, workload and wellbeing | Next |
| 3. Measures app | Entry, review, versions, audit, notifications, RAG, admin screens | |
| 4. Exports | On-demand CSV and xlsx with a data dictionary, scheduled snapshots, quarterly report pack, AI prompt template | |
| 5. Hardening | WCAG 2.2 AA checks, mobile, volume testing | |

## Getting started

1. Follow [docs/setup_guide.md](docs/setup_guide.md). One Power Automate flow creates everything on your SharePoint site and loads the sample data. No IT request or premium licence is needed.
2. Read [docs/data_model.md](docs/data_model.md) for how the data fits together.
3. To add a measure, see [docs/adding_a_measure.md](docs/adding_a_measure.md).

## What's in the repository

| Path | What it is |
|---|---|
| `pms/schema.py` | **Single source of truth** for every list, column, choice and view |
| `pms/periods.py` | Period calendar: financial year (Apr to Mar), calendar year, academic year, terms, weeks, fortnights |
| `pms/rules.py` | Business rules (RAG, validation, expected-by dates). The apps and flows must match these. |
| `pms/seed.py` | Fictional sample data covering every frequency and workflow state |
| `pms/sharepoint.py`, `pms/docs.py` | Generators for the setup requests, data dictionary and diagram |
| `dist/setup/*.json` | Setup requests, run by the setup flow or the PnP script |
| `dist/seed_csv/*.csv` | Sample data as tidy CSV, one file per table. Handy for testing Power BI. |
| `dist/data_dictionary.csv` | Every column, with its type, allowed values and links |
| `docs/` | Guides, data model, generated data dictionary and diagram |
| `scripts/Invoke-PmsSetup.ps1` | PnP PowerShell alternative to the setup flow |
| `tests/` | Checks that the schema, rules and data are consistent |

## Changing the data model

Edit `pms/schema.py` (and `pms/seed.py` if the sample data needs to change). Then rebuild and test:

```bash
python -m pms build
python -m unittest discover -s tests
```

The build regenerates everything in `dist/`, `docs/data_dictionary.md` and `docs/data_model_diagram.md`. It needs Python 3.9 or later and nothing else.

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
  - People have read-only access. Writes go through flows, so the "only the updater edits the value" rule and the audit trail can't be bypassed.
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
- Migration from the old Meeting Submission Tool
