# Flow: PMSWellbeingView

Returns only the wellbeing information the person using the app is allowed to see:

- **Team totals** for the chosen team and week, only when at least `wellbeing_min_group_size` people answered (5 by default).
- **Individual answers** only where the caller is the line manager recorded on the check-in.

The caller's identity comes from Power Apps itself, not from anything the app sends, so it can't be faked. The reference behaviour is `wellbeing_view()` in `pms/rules.py`.

## Before you start

The flow must be **owned by the service account**, and its SharePoint connection must use the service account. That account is the only one that can read every row in `wellbeing_checkins`, so the flow's connection has to be the service account's.

Until you have a service account, build it under your own account. Just make sure your account has Full Control on `wellbeing_checkins`.

## Build it (about 15 minutes)

In Power Automate, choose **Create**, then **Instant cloud flow**, and name it **`PMSWellbeingView`**. Use that exact name: the app calls it as `PMSWellbeingView.Run(...)`. For the trigger, choose **When Power Apps calls a flow (V2)**.

| # | Action | Name it | Settings |
|---|---|---|---|
| 1 | Trigger inputs | | Add two **Text** inputs: `week_start` (format YYYY-MM-DD) and `org_unit_key` |
| 2 | Compose | `Caller` | `toLower(triggerOutputs()?['headers']?['x-ms-user-email'])` |
| 3 | Compose | `Team` | `replace(triggerBody()?['text_1'], '''', '''''')` (stops quotes breaking the filter) |
| 4 | Compose | `From` | `concat(addDays(triggerBody()?['text'], -1, 'yyyy-MM-dd'), 'T12:00:00Z')` |
| 5 | Compose | `To` | `concat(addDays(triggerBody()?['text'], 1, 'yyyy-MM-dd'), 'T12:00:00Z')` |
| 6 | SharePoint **Get items** | `Get_setting` | List: `settings`. Filter Query: `Title eq 'wellbeing_min_group_size'`. Top Count: 1 |
| 7 | Compose | `MinSize` | `int(coalesce(first(body('Get_setting')?['value'])?['setting_value'], '5'))` |
| 8 | SharePoint **Get items** | `Get_team` | List: `wellbeing_checkins`. Filter Query: `org_unit_key eq '@{outputs('Team')}' and week_start ge '@{outputs('From')}' and week_start lt '@{outputs('To')}'`. Top Count: 5000 |
| 9 | SharePoint **Get items** | `Get_reports` | List: `wellbeing_checkins`. Filter Query: `line_manager_email eq '@{outputs('Caller')}' and week_start ge '@{outputs('From')}' and week_start lt '@{outputs('To')}'`. Top Count: 5000 |
| 10 | **Filter array** | `Thriving` | From: `body('Get_team')?['value']`. Condition (advanced mode): `@equals(item()?['wellbeing']?['Value'], 'thriving')` |
| 11 | **Filter array** | `OK` | As above with `'ok'` |
| 12 | **Filter array** | `Struggling` | As above with `'struggling'` |
| 13 | **Select** | `Reports` | From: `body('Get_reports')?['value']`. Map (text mode): `{"email": @{item()?['Title']}, "wellbeing": @{item()?['wellbeing']?['Value']}, "comments": @{item()?['comments']}}`. Type the map in the text box and insert each `@{...}` as an expression. |
| 14 | Compose | `Show` | `greaterOrEquals(length(body('Get_team')?['value']), outputs('MinSize'))` |
| 15 | Compose | `Result` | see below |
| 16 | **Respond to a PowerApp or flow** | | One **Text** output called `result`, value `string(outputs('Result'))` |

For step 15, type this in the Compose box and insert each `@{...}` part as an expression:

```json
{
  "responses": @{length(body('Get_team')?['value'])},
  "show_counts": @{outputs('Show')},
  "counts": {
    "thriving": @{if(outputs('Show'), length(body('Thriving')), null)},
    "ok": @{if(outputs('Show'), length(body('OK')), null)},
    "struggling": @{if(outputs('Show'), length(body('Struggling')), null)}
  },
  "direct_reports": @{body('Reports')}
}
```

Notes on the steps:
- **Why steps 4 and 5 use a window:** SharePoint can store a date-only value as midnight UK time, which is 23:00 the day before in UTC during summer time. A window from midday the day before to midday the day after catches the Monday whichever way it was stored. Weeks are 7 days apart, so it can never pick up the wrong week.
- `email` is the renamed Title column, so the flow reads it as `Title` in step 13. Flows always use internal names.

## Add it to the app

In Power Apps Studio, open the **Power Automate** pane, click **Add flow** and choose `PMSWellbeingView`.

## Test it

- **As a line manager** (e.g. Jordan Hughes in the sample data): open My team for team *Team A* and w/c 21 Sep 2026. You should see individual answers for your direct reports, and team totals if 5 or more people answered.
- **As a team member:** the same screen shows totals only, with no names.
- **With fewer than 5 answers:** the totals are replaced with "Totals are hidden...".
