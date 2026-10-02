# Flow: PMSSaveValue

An updater saves a draft or submits a value. This mirrors `save_value()` in `pms/workflow.py`.

- **Checks:** the caller must be an active **updater** of the measure, and the value must be `not_started`, `draft` or `returned`. Anything else is refused.
- **Versions:** the first save after a return or a reopen creates a **new version**. Otherwise the draft is edited in place, and every changed field goes into `audit_log`.
- **On submit:** the approvers get an email with a link.

**Validation.** The app checks everything before it calls this flow: number format, yes/no values, and a narrative when the value is missing or off track. The flow re-checks the most important rule (a narrative when there's no value). The approver reviews every submission, so they're the backstop for the rest.

## Trigger inputs (in this order, all Text)

| # | Name | Key in expressions | Example |
|---|---|---|---|
| 1 | submission_key | `triggerBody()?['text']` | `PM-0002\|M-2026-09` |
| 2 | submit | `triggerBody()?['text_1']` | `true` or `false` |
| 3 | value_number | `triggerBody()?['text_2']` | `412` or empty |
| 4 | value_text | `triggerBody()?['text_3']` | text measures only |
| 5 | value_missing | `triggerBody()?['text_4']` | `true` or `false` |
| 6 | narrative | `triggerBody()?['text_5']` | |
| 7 | data_quality | `triggerBody()?['text_6']` | `verified` |

## Steps

Start with the pattern 4 variables, then a `Try` scope and a `Catch` scope (pattern 5). Everything below goes inside `Try`.

| # | Action | Name | Details |
|---|---|---|---|
| 1 | Compose | `Caller` | Pattern 1 |
| 2 | Compose | `Key` | `replace(triggerBody()?['text'], '''', '''''')` |
| 3 | Read one item (pattern 2) | `Get_sub` + Compose `Sub` | List `submissions`, key `outputs('Key')` |
| 4 | Read one item | `Get_role` | List `measure_roles`. Filter: `Title eq '@{outputs('Sub')?['measure_code']}\|@{outputs('Caller')}\|updater' and active eq 1` |
| 5 | Condition | `Allowed` | `@and(greater(length(body('Get_role')?['value']), 0), contains(createArray('not_started','draft','returned'), outputs('Sub')?['status']))`. **If no:** respond `{"ok": false, "message": "You can't change this value. It may have been submitted already, or you aren't an updater for this measure."}` and terminate. |
| 6 | Compose | `Submit` | `equals(toLower(triggerBody()?['text_1']), 'true')` |
| 7 | Compose | `Missing` | `equals(toLower(triggerBody()?['text_4']), 'true')` |
| 8 | Condition | `Narrative_needed` | `@and(outputs('Submit'), outputs('Missing'), empty(trim(coalesce(triggerBody()?['text_5'], ''))))`. **If yes:** respond `{"ok": false, "message": "Add a narrative explaining why there is no value."}` and terminate. |
| 9 | Compose | `NewVersion` | `or(contains(createArray('not_started','returned'), outputs('Sub')?['status']), and(greater(outputs('Sub')?['current_version'], 0), equals(outputs('Sub')?['current_version'], outputs('Sub')?['approved_version'])))` |
| 10 | Compose | `VersionNo` | `if(outputs('NewVersion'), add(outputs('Sub')?['current_version'], 1), outputs('Sub')?['current_version'])` |
| 11 | Compose | `Fields` | the JSON under this table |
| 12 | Condition | `Is_new_version` | `@outputs('NewVersion')` |
| 12a | *(yes)* Create item (pattern 3) | `Create_version` | List `submission_versions`. Body: `union(outputs('Fields'), json(concat('{"Title":"', triggerBody()?['text'], '|v', string(outputs('VersionNo')), '","submission_key":"', triggerBody()?['text'], '","measure_code":"', outputs('Sub')?['measure_code'], '","period_key":"', outputs('Sub')?['period_key'], '","version_no":', string(outputs('VersionNo')), ',"entered_date":"', utcNow(), '"}')))` |
| 12b | *(yes)* Create item | `Audit_create` | List `audit_log`: `Title` AUD-guid, `list_name` submission_versions, `item_key` the new version key, `action` create, `changed_by` Caller, `changed_at` utcNow() |
| 12c | *(no)* Read one item | `Get_version` + Compose `Version` | List `submission_versions`, key `concat(outputs('Key'), '\|v', string(outputs('VersionNo')))` |
| 12d | *(no)* Set variables, then paste `Write_with_audit` | | `varList` = `submission_versions`, `varId` = `outputs('Version')?['ID']`, `varKey` = the version key, `varOld` = `outputs('Version')`, `varNew` = `outputs('Fields')`, `varFields` = `createArray('value_number','value_text','value_missing','narrative','data_quality','entered_by','version_status','submitted_date')` |
| 13 | Set variables, then paste `Write_with_audit` | | `varList` = `submissions`, `varId` = `outputs('Sub')?['ID']`, `varKey` = `triggerBody()?['text']`, `varOld` = `outputs('Sub')`, `varNew` = the JSON under this table, `varFields` = `createArray('status','current_version','submitted_date')` |
| 14 | Condition | `Notify_approvers` | `@outputs('Submit')` |
| 14a | *(yes)* HTTP GET | `Get_approvers` | `_api/web/lists/getbytitle('measure_roles')/items?$filter=measure_code eq '@{outputs('Sub')?['measure_code']}' and role eq 'approver' and active eq 1` |
| 14b | *(yes)* Read one item | `Get_measure` + Compose `Measure` | List `measures`, key `outputs('Sub')?['measure_code']` |
| 14c | *(yes)* Read one item | `Get_app_url` | List `settings`, key `measures_app_url` |
| 14d | *(yes)* Apply to each over `body('Get_approvers')?['value']` | | **Send an email notification (V3).** To: `item()?['email']`. Subject: `Value to review: @{outputs('Measure')?['measure_name']}`. Body: `@{outputs('Caller')} has submitted a value for @{outputs('Sub')?['period_key']}. Review it here: @{concat(first(body('Get_app_url')?['value'])?['setting_value'], '?submission=', encodeUriComponent(triggerBody()?['text']))}` |
| 15 | Respond | | `{"ok": true, "message": "@{if(outputs('Submit'), 'Submitted for review.', 'Draft saved.')}"}` |

**Fields** (step 11):
```json
{
  "value_number": @{if(empty(triggerBody()?['text_2']), null, float(triggerBody()?['text_2']))},
  "value_text": @{if(empty(triggerBody()?['text_3']), null, triggerBody()?['text_3'])},
  "value_missing": @{outputs('Missing')},
  "narrative": @{if(empty(triggerBody()?['text_5']), null, triggerBody()?['text_5'])},
  "data_quality": "@{triggerBody()?['text_6']}",
  "entered_by": "@{outputs('Caller')}",
  "version_status": "@{if(outputs('Submit'), 'submitted', 'draft')}",
  "submitted_date": @{if(outputs('Submit'), concat('"', utcNow(), '"'), 'null')}
}
```
If typing JSON with expressions in a Compose gets fiddly, add an expression that builds the same object with `json(concat(...))` instead.

**Submission changes** (step 13, `varNew`):
```json
{
  "status": "@{if(outputs('Submit'), 'submitted', 'draft')}",
  "current_version": @{outputs('VersionNo')},
  "submitted_date": @{if(outputs('Submit'), concat('"', utcNow(), '"'), if(empty(outputs('Sub')?['submitted_date']), 'null', concat('"', outputs('Sub')?['submitted_date'], '"')))}
}
```

## Test

In the sample data, Nadia Hassan updates PM-0020 (gender pay gap report) for FY 2025-26.
1. Save a draft with value Yes. You should see version 1 with status draft.
2. Save again with No and a narrative. It's still version 1, and `audit_log` shows `value_number` changing from 1 to 0.
3. Submit. The submission becomes `submitted`, and Jordan Hughes gets an email.
