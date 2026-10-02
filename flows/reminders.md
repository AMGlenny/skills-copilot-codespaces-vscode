# Flow: PMSReminders

Every Monday, each updater gets one email listing their values that are late or expected within the next few days. The number of days comes from the `reminder_days_before_expected` setting (5 by default). There's one email per person, not one per value.

Values with no expected lag are never chased, because the data is lagged and there's no date to chase against.

It mirrors `reminders()` in `pms/workflow.py`.

## Steps

**Trigger:** **Recurrence**, weekly on Monday at 07:45, London time zone.

| # | Action | Details |
|---|---|---|
| 1 | Compose `Today` | `convertFromUtc(utcNow(), 'GMT Standard Time', 'yyyy-MM-dd')` |
| 2 | Read one item `Days` | List `settings`, key `reminder_days_before_expected` |
| 3 | Compose `Horizon` | `addDays(outputs('Today'), int(coalesce(first(body('Days')?['value'])?['setting_value'], '5')), 'yyyy-MM-dd')` |
| 4 | HTTP GET `Get_due` | `submissions` filter: `(status eq 'not_started' or status eq 'draft' or status eq 'returned') and expected_by le '@{outputs('Horizon')}T23:59:59Z'&$top=5000` |
| 5 | HTTP GET `Get_updaters` | `measure_roles` filter: `role eq 'updater' and active eq 1&$top=5000` |
| 6 | Select `Emails` | From `body('Get_updaters')?['value']`. Map, in text mode: `item()?['email']` |
| 7 | Compose `People` | `union(body('Emails'), body('Emails'))`. This removes duplicates. |
| 8 | Read one item `App_url` | List `settings`, key `measures_app_url` |
| 9 | Apply to each over `outputs('People')` | |
| 9a | Filter array `My_roles` | From `body('Get_updaters')?['value']`, where `item()?['email']` equals `items('Apply_to_each')` |
| 9b | Select `My_codes` | From `body('My_roles')`. Map, in text mode: `item()?['measure_code']` |
| 9c | Filter array `My_due` | From `body('Get_due')?['value']`. Condition (advanced): `@contains(body('My_codes'), item()?['measure_code'])` |
| 9d | Condition | `@greater(length(body('My_due')), 0)` |
| 9e | *(yes)* Select `Rows` | From `body('My_due')`. Map: `Measure` = `item()?['measure_code']`, `Period` = `item()?['period_key']`, `Status` = `item()?['status']`, `Expected by` = `convertFromUtc(item()?['expected_by'], 'GMT Standard Time', 'dd MMM yyyy')` |
| 9f | *(yes)* Create HTML table | From `body('Rows')` |
| 9g | *(yes)* Send an email notification (V3) | To: `items('Apply_to_each')`. Subject: `Performance values due: @{length(body('My_due'))}`. Body: `These values are late or expected soon:` then the HTML table, then `Update them here: @{first(body('App_url')?['value'])?['setting_value']}` |

## Test

With the sample data, run it with Today set to 2026-09-30. Nadia Hassan should get a single email listing PM-0020 (FY 2025-26) and her other values that are due.
