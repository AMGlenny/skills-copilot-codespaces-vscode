# Weekly updates app

A simple app for logging everyday work as it happens. People can use it any day of the week, and each week's entry builds on the last:

- **My week:** successes, communication, workload and a private wellbeing check-in. Open tasks and problems carry over from previous weeks, so nothing is typed twice. Tick what's done, add what's new, and save.
- **Task and problem screens:** add or update a task or a problem, and link it to the theme, programme, objective or measure it supports.
- **My team:** who has updated this week, team successes and communication, workload totals, and wellbeing totals. Line managers also see their own direct reports' wellbeing.

Everything saved here feeds the quarterly report pack in phase 4.

## How it stores data

- **Direct writes:** the app writes straight to the `weekly_updates`, `wellbeing_checkins`, `tasks` and `problems` lists.
- **SharePoint enforces the rules** through permissions (see the setup guide):
  - People can edit only their own weekly update.
  - People can read only their own wellbeing check-ins.
  - Nobody can delete anything.
- **Audit trail:** every change is kept in SharePoint version history (who, when, old value, new value).
- **Wellbeing for other people** is only ever read through the `PMSWellbeingView` flow.

## Build it (about 45 minutes)

These steps assume setup (lists and permissions) is already done.

1. **Create the app.** In Power Apps, choose **Create**, then **Blank app**, then **Blank canvas app**. Name it `PMS Weekly` and pick the **Tablet** format. The layout adapts to phones.
2. **Settings.** Go to **Settings**, then **Display**, and turn **off** "Scale to fit". Then go to **General** and set the **Data row limit** to **2000**.
3. **Data.** Add a **SharePoint** connection to your site and tick these lists: `people`, `org_units`, `groups`, `measures`, `settings`, `weekly_updates`, `wellbeing_checkins`, `tasks`, `problems`.
4. **App formulas.** Open [`powerapps/weekly/App.pfx`](../powerapps/weekly/App.pfx):
   - Select **App** in the tree view and paste the **App.Formulas** block into the `Formulas` property.
   - Paste the **App.OnStart** block into `OnStart`.
5. **Flow.** Build `PMSWellbeingView` ([flows/wellbeing_view.md](../flows/wellbeing_view.md)). Then add it to the app from the Power Automate pane.
6. **Screens.** Paste them in this order, following the instructions at the top of each file:
   - [`scrWeek.pa.yaml`](../powerapps/weekly/scrWeek.pa.yaml) (make it the first screen)
   - [`scrTask.pa.yaml`](../powerapps/weekly/scrTask.pa.yaml)
   - [`scrProblem.pa.yaml`](../powerapps/weekly/scrProblem.pa.yaml)
   - [`scrTeam.pa.yaml`](../powerapps/weekly/scrTeam.pa.yaml)

   For each screen: add a blank screen, rename it, set its `Fill` and `OnVisible`, copy the YAML, right-click the screen in the tree view and choose **Paste code**.
7. **Run App.OnStart** (right-click **App**, then **Run OnStart**), then preview.
8. **Save, publish and share.** Share with everyone who needs it. They also need at least Read on the site, which they get through site permissions.

## Test script

Sign in as someone in the `people` list (with the sample data, add yourself as a person in team `ST-SDS-A` with `jordan.hughes@example.org` as your line manager).

| # | Do this | Expect |
|---|---|---|
| 1 | Open the app | This week's Monday is shown. Your team is pre-filled. Open tasks from earlier weeks are listed. |
| 2 | Type a success, pick a workload, pick a wellbeing answer, save | "Saved" message. A row appears in `weekly_updates` and one in `wellbeing_checkins`. |
| 3 | Change the success and save again | The same rows update. Version history shows the old and new text. |
| 4 | Tick a task, then leave and come back to My week | The tick is still there and the status line says 1 change is not saved yet. |
| 5 | Save | The task is `complete`, with you as `completed_by` and today's date. |
| 6 | Pick last week | Your saved entries for that week load, or blanks if there are none. Tasks completed this week no longer show under last week. |
| 7 | Add a task | It gets a TSK- code and appears in the list. |
| 8 | Close a problem without a resolution | You're told to add a resolution, and nothing saves. |
| 9 | Open My team | Update counts and successes show. Wellbeing shows totals only if 5 or more people answered. |
| 10 | As a line manager, open My team | Your direct reports' answers show. Other people's don't. |
| 11 | Try to open `wellbeing_checkins` in SharePoint as a normal user | You see only your own check-ins. |
| 12 | As a `viewer` | Everything is read-only. |

## Accessibility (WCAG 2.2 AA)

What's built in:
- **Colour and contrast:**
  - All text colours pass the 4.5:1 contrast ratio.
  - The header is dark enough for white text. The old grey header was about 2:1.
  - Status is shown in words ("Updated", "Not yet"), never by colour alone.
- **Screen readers:**
  - Every input has a visible label and an accessible name.
  - Headings use heading roles, so screen reader users can jump between sections.
  - The save status is a polite live region, so screen readers announce it.
  - Icons have accessible labels, such as "Open task: ...".
- **Keyboard and touch:**
  - Buttons and icons are at least 40 by 40 pixels, above the 24 pixel minimum in WCAG 2.2.
  - Focused buttons get a thick visible border.
  - Tab order follows the layout because everything sits in auto-layout containers.
- **Small screens:** the three columns stack into one on screens narrower than 900 pixels, with no sideways scrolling.

Check these by hand before go-live:
- Run Power Apps' **App checker**, then **Accessibility**, and fix anything it lists.
- Tab through each screen with the keyboard only.
- Test with Narrator or NVDA.
- Test on a phone.

## If pasting fails

- **"Unknown control" or a version error:** Microsoft updates control versions from time to time. Insert one control of that type by hand, right-click it, choose **View code** to see the current version (e.g. `Classic/Button@2.2.0`), and change the version in the YAML to match.
- **A gallery won't paste:** insert a blank vertical gallery with the same name, then paste its `Children` controls into it.
- **A formula shows `email`, `task_code` or another key as not recognised:** on some tenants Power Apps still calls the renamed Title column `Title`. Replace the key name with `Title` in those formulas.
- **Dropdowns show `[object]` or are blank:** set the dropdown's **Value** property to `label` in the right-hand panel.
- **Dates on the team screen are a day out:** check that the site time zone is London (see the setup guide).
