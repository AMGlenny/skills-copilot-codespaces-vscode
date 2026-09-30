# Power Automate flows

| Flow | Trigger | What it does | Guide |
|---|---|---|---|
| PMSWellbeingView | Weekly app | Returns the wellbeing a person may see | [wellbeing_view.md](wellbeing_view.md) |
| PMSSaveValue | Measures app | Updater saves a draft or submits a value | [save_value.md](save_value.md) |
| PMSReview | Measures app | Approver approves or returns; admin reopens | [review.md](review.md) |
| PMSCreateExpected | Daily, 05:00 | Creates a `not_started` submission for every active measure when a period ends | [create_expected.md](create_expected.md) |
| PMSReminders | Mondays, 07:45 | Emails each updater a list of values that are expected soon or already late | [reminders.md](reminders.md) |

The exact behaviour of every flow is written down as Python in `pms/workflow.py` and checked by `tests/test_workflow.py`. If a flow and that file disagree, the file is right.

## Before you build any of them

- **Owner and connections:** build them while signed in as the **service account**, so every SharePoint connection uses it. Until you have one, use your own account, then change the owner and connections later.
- **Solution:** put them in a **solution** if your environment allows it. It makes moving them between environments easier later. If not, ordinary flows are fine.
- **Triggers:** flows called from an app use the trigger **When Power Apps calls a flow (V2)**, with **Text** inputs only. Power Automate names the inputs `text`, `text_1`, `text_2` and so on, in the order you add them. Each guide lists the order.
- **Site address:** every SharePoint action uses the same site address. Choose it once and copy it.

## Pattern 1: who is calling

Add a **Compose** called `Caller`:
```
toLower(triggerOutputs()?['headers']?['x-ms-user-email'])
```
Power Apps supplies this, so it can't be faked by the app.

## Pattern 2: read one item by key

Use **Send an HTTP request to SharePoint**:
- Method: `GET`
- Uri: `_api/web/lists/getbytitle('LIST')/items?$filter=Title eq '@{KEY}'&$top=1`
- Headers: `Accept` = `application/json;odata=nometadata`

Then add a **Compose** with `first(body('THAT_ACTION')?['value'])`.

A few rules to follow:
- **Escape keys.** Always escape single quotes in a key: `replace(KEY, '''', '''''')`.
- **Title is the key.** In flows the key column is always called `Title`. Flows use internal names; the snake_case display names only appear in the app and in exports.
- **Why HTTP, not Get items.** This format returns choice columns as plain text (for example `"submitted"`) and yes/no columns as `true`/`false`. That keeps comparisons simple.

## Pattern 3: create an item

Use **Send an HTTP request to SharePoint**:
- Method: `POST`
- Uri: `_api/web/lists/getbytitle('LIST')/items`
- Headers: `Accept` and `Content-Type` both `application/json;odata=nometadata`
- Body: a JSON object of column names and values, with the key in `Title`

## Pattern 4: update with audit (build once, copy)

Every change to an existing item goes through the same block, so every changed field is logged with its old and new value.

**Set up once.** At the top of the flow, before the Try scope, initialise these variables:

| Variable | Type | Starting value |
|---|---|---|
| `varList` | String | (empty) |
| `varId` | Integer | 0 |
| `varKey` | String | (empty) |
| `varOld` | Object | `{}` |
| `varNew` | Object | `{}` |
| `varFields` | Array | `[]` |
| `varAuditAction` | String | (empty) |

**Before each use**, set:
- `varList`, `varId` and `varKey`: the list, the item's ID and the item's key
- `varOld`: the item as read in pattern 2
- `varNew`: the changes, for example `{"status": "approved"}`
- `varFields`: the names of the changed fields, for example `createArray('status')`

Then build a **Scope** called `Write_with_audit` containing:

1. **Send an HTTP request to SharePoint**
   - Method: `POST`
   - Uri: `_api/web/lists/getbytitle('@{variables('varList')}')/items(@{variables('varId')})`
   - Headers: `Accept` and `Content-Type` = `application/json;odata=nometadata`, `X-HTTP-Method` = `MERGE`, `IF-MATCH` = `*`
   - Body: `variables('varNew')`
2. **Apply to each** over `variables('varFields')`, set to sequential. Inside it:
   - **Condition**, in advanced mode:
     ```
     @not(equals(string(coalesce(variables('varOld')?[item()], '')), string(coalesce(variables('varNew')?[item()], ''))))
     ```
   - If yes, **create an item** in `audit_log` (pattern 3) with this body:
     ```json
     {
       "Title": "@{concat('AUD-', guid())}",
       "list_name": "@{variables('varList')}",
       "item_key": "@{variables('varKey')}",
       "action": "@{if(empty(variables('varAuditAction')), if(contains(createArray('status','version_status'), item()), 'status_change', 'edit'), variables('varAuditAction'))}",
       "field_name": "@{item()}",
       "old_value": "@{coalesce(variables('varOld')?[item()], '')}",
       "new_value": "@{coalesce(variables('varNew')?[item()], '')}",
       "changed_by": "@{outputs('Caller')}",
       "changed_at": "@{utcNow()}"
     }
     ```

**To reuse it**, copy the scope (the **...** menu, then **Copy**) and paste it where needed. It only uses variables, so the copy works as it is.

## Pattern 5: answer the app, even when something fails

- **Try:** put all the work in a **Scope** called `Try`. End it with **Respond to a PowerApp or flow**, with one **Text** output called `result` and the value `{"ok": true, "message": "..."}`.
- **Catch:** add a second **Scope** called `Catch` after it. Under **Configure run after**, tick only **has failed** and **has timed out**. Inside it, respond with `{"ok": false, "message": "Something went wrong and your change may not have saved. Please try again, or contact an admin if it keeps happening."}`.
- **Refusals:** when a check refuses the request, respond with `{"ok": false, "message": "<reason>"}`, then add **Terminate** with status **Succeeded**.

## Pattern 6: send a notification

Use **Send an email notification (V3)**, from the Mail connector. It's standard, and it doesn't need a mailbox for the service account.

Build links to a value from the `measures_app_url` setting:
```
concat(SETTING, '?submission=', encodeUriComponent(KEY))
```

## Dates

SharePoint can store a date-only value as midnight UK time, which is 23:00 the day before in UTC during summer time. The seed data stores it as midday UTC. So:
- **When reading a date**, turn it into a UK date first: `convertFromUtc(DATE, 'GMT Standard Time', 'yyyy-MM-dd')`.
- **When writing a date**, send it as `yyyy-MM-ddT12:00:00Z`.
- **When filtering on a date**, use a window from midday the day before to midday on the day.
