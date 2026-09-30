# Flow: PMSCreateExpected

This flow runs every morning. For every period that ended in the last 7 days, it creates a `not_started` submission for each active measure with that frequency, if one doesn't exist yet. That's what drives the "expected, not received" views. The 7-day look-back means a missed run catches up by itself.

It mirrors `expected_submissions()` in `pms/workflow.py`.

## Steps

**Trigger:** **Recurrence**, every 1 day at 05:00, time zone **(UTC+00:00) Dublin, Edinburgh, Lisbon, London**.

**Top of the flow** (before any scope):
- Compose `Caller`: the service account's email, typed in. It's used for `changed_by` in the audit log.
- Compose `Today`: `convertFromUtc(utcNow(), 'GMT Standard Time', 'yyyy-MM-dd')`

Then the main steps:

| # | Action | Details |
|---|---|---|
| 1 | HTTP GET `Get_periods` | `_api/web/lists/getbytitle('periods')/items?$filter=end_date gt '@{addDays(outputs('Today'), -8)}T12:00:00Z' and end_date le '@{addDays(outputs('Today'), -1)}T12:00:00Z'&$top=5000`. This finds periods whose last day was 1 to 7 days ago. |
| 2 | Apply to each period (`body('Get_periods')?['value']`) | |
| 2a | HTTP GET `Get_measures` | `measures` filter: `frequency eq '@{items('Apply_to_each')?['period_type']}' and status eq 'active'&$top=5000` |
| 2b | Compose `PeriodEnd` | `convertFromUtc(items('Apply_to_each')?['end_date'], 'GMT Standard Time', 'yyyy-MM-dd')` |
| 2c | Apply to each measure (`body('Get_measures')?['value']`) | |
| 2c-i | Compose `NewKey` | `concat(items('Apply_to_each_2')?['Title'], '\|', items('Apply_to_each')?['Title'])` |
| 2c-ii | HTTP GET `Exists` | `submissions` filter: `Title eq '@{outputs('NewKey')}'` |
| 2c-iii | Condition | `@empty(body('Exists')?['value'])` |
| 2c-iv | *(yes)* Create item in `submissions` | body below |
| 2c-v | *(yes)* Create item in `audit_log` | `action` create, `list_name` submissions, `item_key` NewKey, `changed_by` Caller |

**Submission body** (step 2c-iv):
```json
{
  "Title": "@{outputs('NewKey')}",
  "measure_code": "@{items('Apply_to_each_2')?['Title']}",
  "period_key": "@{items('Apply_to_each')?['Title']}",
  "status": "not_started",
  "current_version": 0,
  "expected_by": @{if(equals(items('Apply_to_each_2')?['expected_lag_days'], null), 'null', concat('"', addDays(outputs('PeriodEnd'), int(items('Apply_to_each_2')?['expected_lag_days']), 'yyyy-MM-dd'), 'T12:00:00Z"'))}
}
```

## Test

Run it manually the day after a month ends. You should see one new `not_started` row per active monthly measure. Run it again straight away: nothing new is added.
