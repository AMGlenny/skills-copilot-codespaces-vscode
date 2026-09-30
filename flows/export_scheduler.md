# Flow: PMSExportScheduler

Every morning this flow checks `export_jobs` and queues any job that's due today, by adding a row to `export_requests`. `PMSExportRun` then does the work. Admins change the schedule by editing `export_jobs`, and the flow never needs changing.

It mirrors `job_due()` and `previous_fy_quarter()` in `pms/exports.py`.

| Job | Default schedule | Output |
|---|---|---|
| EXP-FULL-NIGHTLY | Daily | `/snapshots/full_model/latest`: every table, for Power BI and AI |
| EXP-WEEKLY-WORK | Mondays | `/snapshots/weekly_work/latest` |
| EXP-QUARTER-PACK | 10th of Jan, Apr, Jul, Oct | `/snapshots/quarter_pack/latest`: the quarter that just ended, with the report prompt |

## Steps

**Trigger:** **Recurrence**, daily at 05:30, London time zone.

**Date composes** (build these first):

| Compose | Expression |
|---|---|
| `Today` | `convertFromUtc(utcNow(), 'GMT Standard Time', 'yyyy-MM-dd')` |
| `M` | `int(formatDateTime(outputs('Today'), 'MM'))` |
| `D` | `int(formatDateTime(outputs('Today'), 'dd'))` |
| `ISO_DOW` | `if(equals(dayOfWeek(outputs('Today')), 0), 7, dayOfWeek(outputs('Today')))`. Monday is 1 and Sunday is 7, matching `run_day`. |
| `FY` | `if(greaterOrEquals(outputs('M'), 4), int(formatDateTime(outputs('Today'), 'yyyy')), sub(int(formatDateTime(outputs('Today'), 'yyyy')), 1))` |
| `Q` | `add(div(mod(add(sub(outputs('M'), 4), 12), 12), 3), 1)` |
| `PrevQuarter` | `concat(string(if(equals(outputs('Q'), 1), sub(outputs('FY'), 1), outputs('FY'))), '-', substring(string(add(if(equals(outputs('Q'), 1), sub(outputs('FY'), 1), outputs('FY')), 1)), 2, 2), ' Q', string(if(equals(outputs('Q'), 1), 4, sub(outputs('Q'), 1))))` |

**Main steps:**

| # | Action | Details |
|---|---|---|
| 1 | HTTP GET `Get_jobs` | `_api/web/lists/getbytitle('export_jobs')/items?$filter=active eq 1` |
| 2 | Filter array `Due` | From `body('Get_jobs')?['value']`. The condition (advanced mode) is below. |
| 3 | Apply to each over `body('Due')` | Steps 3a and 3b go inside. |
| 3a | Create item in `export_requests` (pattern 3) | Body below |
| 3b | HTTP MERGE the job | `{"last_run_at": "@{utcNow()}", "last_run_status": "queued"}` |

**Due** (step 2):
```
@or(
  equals(item()?['frequency'], 'daily'),
  and(equals(item()?['frequency'], 'weekly'), equals(item()?['run_day'], outputs('ISO_DOW'))),
  and(equals(item()?['frequency'], 'monthly'), equals(item()?['run_day'], outputs('D'))),
  and(equals(item()?['frequency'], 'quarterly'), contains(createArray(1, 4, 7, 10), outputs('M')), equals(item()?['run_day'], outputs('D'))))
```

**Request body** (step 3a):
```json
{
  "Title": "REQ-@{formatDateTime(utcNow(), 'yyyyMMdd-HHmm')}-@{items('Apply_to_each')?['Title']}",
  "dataset": "@{items('Apply_to_each')?['dataset']}",
  "job_code": "@{items('Apply_to_each')?['Title']}",
  "quarter_label": @{if(equals(items('Apply_to_each')?['dataset'], 'quarter_pack'), concat('"', outputs('PrevQuarter'), '"'), 'null')},
  "filter_label": "@{if(equals(items('Apply_to_each')?['dataset'], 'quarter_pack'), concat('Financial quarter ', outputs('PrevQuarter')), 'Everything')}",
  "folder_path": "@{items('Apply_to_each')?['folder_path']}",
  "requested_at": "@{utcNow()}",
  "status": "queued"
}
```

## Test

Set EXP-WEEKLY-WORK's `run_day` to today's weekday (1 is Monday) and run the flow manually. A queued request appears, then `PMSExportRun` produces `/snapshots/weekly_work/latest`.
