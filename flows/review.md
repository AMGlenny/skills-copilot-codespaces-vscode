# Flow: PMSReview

This flow handles three actions. It mirrors `approve()`, `return_for_changes()` and `reopen()` in `pms/workflow.py`.

- **approve** (approvers): approves the submitted version and works out and stores RAG. It marks any earlier approved version as superseded, resolves open review comments, and updates the reporting row in `rpt_values`.
- **return** (approvers): sends the value back with a required comment and emails the updaters.
- **reopen** (admins): reopens an approved value with a required reason and emails the updaters. The approved version stays in reports until a new one is approved.

Approvers can't approve or return a version they entered themselves.

## Trigger inputs (in this order, all Text)

| # | Name | Key |
|---|---|---|
| 1 | submission_key | `triggerBody()?['text']` |
| 2 | action | `triggerBody()?['text_1']` (`approve`, `return` or `reopen`) |
| 3 | comment | `triggerBody()?['text_2']` |

## Steps

Start with the pattern 4 variables, then the `Try` and `Catch` scopes. Everything below goes inside `Try`.

**Read and check**

| # | Action | Name | Details |
|---|---|---|---|
| 1 | Compose | `Caller`, `Key`, `Action` | Caller as pattern 1. `Key`: `replace(triggerBody()?['text'], '''', '''''')`. `Action`: `toLower(triggerBody()?['text_1'])` |
| 2 | Read one item | `Sub` | List `submissions`, key `outputs('Key')` |
| 3 | Read one item | `Version` | List `submission_versions`, key `concat(outputs('Key'), '\|v', string(outputs('Sub')?['current_version']))` |
| 4 | Read one item | `Person` | List `people`, key `outputs('Caller')` |
| 5 | HTTP GET | `Get_role` | `measure_roles` filter: `Title eq '@{outputs('Sub')?['measure_code']}\|@{outputs('Caller')}\|approver' and active eq 1` |
| 6 | Compose | `Allowed` | see below |
| 7 | Condition | | `@outputs('Allowed')`. **If no:** respond `{"ok": false, "message": "You can't do that to this value. It may have changed since you opened it."}` and terminate. |
| 8 | Condition | | `@and(not(equals(outputs('Action'), 'approve')), empty(trim(coalesce(triggerBody()?['text_2'], ''))))`. **If yes:** respond `{"ok": false, "message": "Add a comment explaining why."}` and terminate. |
| 9 | Read one item | `Measure` | List `measures`, key `outputs('Sub')?['measure_code']` |
| 10 | Read one item | `App_url` | List `settings`, key `measures_app_url` |

**Allowed** (step 6):
```
if(equals(outputs('Action'), 'reopen'),
   and(equals(outputs('Person')?['app_role'], 'admin'), equals(outputs('Person')?['active'], true), equals(outputs('Sub')?['status'], 'approved')),
   and(contains(createArray('approve', 'return'), outputs('Action')),
       greater(length(body('Get_role')?['value']), 0),
       equals(outputs('Sub')?['status'], 'submitted'),
       not(equals(outputs('Version')?['entered_by'], outputs('Caller')))))
```

After the checks, add a **Switch** on `outputs('Action')`.

### Case `approve`

| # | Action | Details |
|---|---|---|
| A1 | HTTP GET `Get_refs` | `reference_values` filter: `measure_code eq '@{outputs('Sub')?['measure_code']}' and period_key eq '@{outputs('Sub')?['period_key']}' and active eq 1` |
| A2 | Four **Filter array** actions: `Target`, `Tolerance`, `Baseline`, `Capacity` | From `body('Get_refs')?['value']`, where `item()?['ref_type']` equals `target`, `tolerance`, `baseline` or `capacity` |
| A3 | Compose `RAG` | see below |
| A4 | Condition: `@not(empty(outputs('Sub')?['approved_version']))` | **If yes** (this was a reopened value): read version `Key\|v<approved_version>`, then `Write_with_audit` with `varNew` = `{"version_status": "superseded"}` and fields `createArray('version_status')` |
| A5 | `Write_with_audit` on the current version | `varNew` = `{"version_status": "approved", "rag_status": "@{outputs('RAG')}"}`, fields `createArray('version_status','rag_status')` |
| A6 | `Write_with_audit` on the submission | `varNew` = `{"status": "approved", "approved_version": @{outputs('Sub')?['current_version']}, "approved_by": "@{outputs('Caller')}", "approved_date": "@{utcNow()}"}`, fields `createArray('status','approved_version','approved_by','approved_date')` |
| A7 | Condition: comment not empty | **If yes:** create an item in `review_comments`: `Title` `concat('RC-', guid())`, `submission_key`, `version_no`, `reviewer_email` Caller, `action` approved, `comment`, `comment_date` utcNow(), `resolved` true |
| A8 | HTTP GET `Open_comments` | `review_comments` filter: `submission_key eq '@{outputs('Key')}' and resolved eq 0` |
| A9 | Apply to each over the open comments | MERGE `items(@{item()?['ID']})` with `{"resolved": true, "resolved_by": "@{outputs('Caller')}", "resolved_date": "@{utcNow()}"}` |
| A10 | Update the reporting row | see "Reporting row" below |
| A11 | Respond | `{"ok": true, "message": "Approved."}` |

**RAG** (step A3). The expression uses `coalesce` so it never compares against an empty value. It matches `rag_status()` in `pms/rules.py`:
```
if(or(equals(outputs('Measure')?['unit'], 'text'), equals(outputs('Measure')?['polarity'], 'neither')), 'not_applicable',
if(or(equals(outputs('Version')?['value_missing'], true), equals(outputs('Version')?['value_number'], null)), 'no_data',
if(and(empty(body('Target')), or(empty(body('Tolerance')), not(contains(createArray('kpi','okr'), outputs('Measure')?['measure_class'])))), 'no_target',
if(not(empty(body('Target'))),
   if(if(equals(outputs('Measure')?['polarity'], 'higher_is_better'),
         greaterOrEquals(float(coalesce(outputs('Version')?['value_number'], 0)), float(first(body('Target'))?['ref_value'])),
         lessOrEquals(float(coalesce(outputs('Version')?['value_number'], 0)), float(first(body('Target'))?['ref_value']))),
      'green',
      if(and(not(empty(body('Tolerance'))), contains(createArray('kpi','okr'), outputs('Measure')?['measure_class']),
             if(equals(outputs('Measure')?['polarity'], 'higher_is_better'),
                greaterOrEquals(float(coalesce(outputs('Version')?['value_number'], 0)), float(coalesce(first(body('Tolerance'))?['ref_value'], 0))),
                lessOrEquals(float(coalesce(outputs('Version')?['value_number'], 0)), float(coalesce(first(body('Tolerance'))?['ref_value'], 0))))),
         'amber', 'red')),
   if(if(equals(outputs('Measure')?['polarity'], 'higher_is_better'),
         greaterOrEquals(float(coalesce(outputs('Version')?['value_number'], 0)), float(coalesce(first(body('Tolerance'))?['ref_value'], 0))),
         lessOrEquals(float(coalesce(outputs('Version')?['value_number'], 0)), float(coalesce(first(body('Tolerance'))?['ref_value'], 0)))),
      'green', 'red')))))
```

Power Automate works out every part of an `if()` expression, even the branch it doesn't use. That's why the missing-value and missing-target cases are checked first, and why `coalesce` stands in for empty values in the comparisons.

### Reporting row (step A10)

`rpt_values` has one flat row per approved measure per period, and exactly one row per measure is marked `is_latest`. This mirrors `upsert_rpt()` in `pms/workflow.py`.

| # | Action | Details |
|---|---|---|
| R1 | Read one item `Period` | List `periods`, key `outputs('Sub')?['period_key']` |
| R2 | HTTP GET `Get_owner` | `measure_roles` filter: `measure_code eq '...' and role eq 'owner' and active eq 1` |
| R3 | Read one item `Owner` | List `people`, key `first(body('Get_owner')?['value'])?['email']` |
| R4 | HTTP GET `Get_latest` | `rpt_values` filter: `measure_code eq '...' and is_latest eq 1` |
| R5 | Compose `IsLatest` | see below |
| R6 | Condition | `@and(outputs('IsLatest'), not(empty(body('Get_latest')?['value'])), not(equals(first(body('Get_latest')?['value'])?['Title'], triggerBody()?['text'])))`. **If yes:** MERGE the old latest row with `{"is_latest": false}` |
| R7 | Compose `Row` | every `rpt_values` column. Take measure details from `Measure`, period details from `Period`, the value and narrative from `Version`, targets from the four filter arrays, and `approved_by`/`approved_date` from step A6. Set `rag_status` to `outputs('RAG')`, `is_latest` to `outputs('IsLatest')`, `refreshed_at` to `utcNow()`, and `Title` to the submission key. Set `tolerance_value` only for kpi and okr measures. |
| R8 | Read one item `Existing_row` | List `rpt_values`, key `outputs('Key')` |
| R9 | Condition: `@empty(outputs('Existing_row'))` | **If yes:** create the item with `outputs('Row')`. **If no:** MERGE `items(@{outputs('Existing_row')?['ID']})` with `outputs('Row')`. |

**IsLatest** (step R5):
```
or(empty(body('Get_latest')?['value']),
   equals(first(body('Get_latest')?['value'])?['Title'], triggerBody()?['text']),
   greaterOrEquals(ticks(outputs('Period')?['end_date']), ticks(coalesce(first(body('Get_latest')?['value'])?['period_end'], '1900-01-01T00:00:00Z'))))
```

### Case `return`

| # | Action | Details |
|---|---|---|
| B1 | `Write_with_audit` on the current version | `{"version_status": "returned"}` |
| B2 | `Write_with_audit` on the submission | `{"status": "returned"}` |
| B3 | Create item in `review_comments` | `action` returned, `comment` from `triggerBody()?['text_2']`, `resolved` false |
| B4 | HTTP GET `Get_updaters` | `measure_roles` filter: `measure_code eq '...' and role eq 'updater' and active eq 1` |
| B5 | Apply to each updater | **Send an email notification (V3).** To: `item()?['email']`. Subject: `Returned for changes: @{outputs('Measure')?['measure_name']}`. Body: the comment, plus the link built from `App_url` |
| B6 | Respond | `{"ok": true, "message": "Returned to the updater."}` |

### Case `reopen`

| # | Action | Details |
|---|---|---|
| C1 | Set variable `varAuditAction` to `reopen`, then `Write_with_audit` on the submission | `{"status": "draft"}`, then set `varAuditAction` back to empty |
| C2 | Create item in `review_comments` | `action` reopened, `comment` from `triggerBody()?['text_2']`, `resolved` false |
| C3 | Email the updaters | as in B4 and B5, with subject `Reopened: ...` |
| C4 | Respond | `{"ok": true, "message": "Reopened. The approved value stays in reports until a new one is approved."}` |

## Test

Use the sample data.
1. **Approve.** PM-0002 for Aug 2026 is awaiting review by Sam Patel. Approve it as Sam. You should see a RAG status on the version, the submission `approved`, and a row in `rpt_values` with `is_latest` set to Yes. The July row changes to No.
2. **Refused.** Try to approve the same value again. It's refused.
3. **Reopen.** Reopen it as an admin with a reason. The status goes to `draft`, a `reopen` row appears in `audit_log`, and the updaters get an email.
