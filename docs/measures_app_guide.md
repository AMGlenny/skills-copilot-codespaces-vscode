# Measures app

The measures app is where updaters enter values and approvers review them.

- **My measures:** three tabs.
  - **To update** lists your values, most urgent first: returned for changes, expected but not received, drafts, then values still awaiting data.
  - **To review** is the approver's queue: awaiting your review, returned (waiting on the updater), and overdue.
  - **All measures** shows every active measure with its latest approved value and RAG.
- **The value screen:** one screen for everyone. The updater enters the value, narrative and data quality. The screen shows the targets and a live RAG preview, and lists any validation problems before you submit. Review comments, every version (with what changed between versions) and recent approved values sit alongside the narrative. Approvers approve or return from here, and admins can reopen an approved value.
- **Targets (admins):** set a target, tolerance, baseline or capacity across a range of periods in one go. Tolerance only appears for KPIs and OKRs.

Email links go straight to the value they're about.

## How the rules are enforced

People have read-only access to the measures lists. Every change to a value goes through the `PMSSaveValue` and `PMSReview` flows, which run as the service account. The flows check the rules, so they can't be bypassed from SharePoint:

- Only an updater can edit a value, and only while it's not started, a draft, or returned.
- Only an approver can approve or return, and never a value they entered themselves.
- Returning needs a comment. Reopening needs a reason, and only admins can reopen.
- An approved value is locked. If it's reopened, the approved version stays in reports until a corrected one is approved.
- Every field change and status change is written to `audit_log` with the old and new value.

The rules are written as Python in `pms/workflow.py` and tested in `tests/test_workflow.py`. The flows mirror them step by step.

## What's in phase 3, and what's left to SharePoint

Admins keep measures, people, roles, periods (including term dates), groups and settings up to date directly in the SharePoint lists, using the standard list forms. They are site owners, and version history records every change. [adding_a_measure.md](adding_a_measure.md) walks through it.

I haven't built app screens for this. They would repeat what the list forms already do. They're on the "later" list if the list forms turn out to be awkward in practice.

## Build it (about 2 hours, most of it flows)

1. **Flows**, following [flows/README.md](../flows/README.md). Build `PMSSaveValue`, `PMSReview`, `PMSCreateExpected` and `PMSReminders`.
2. **Create the app.** Choose **Blank canvas app** in Tablet format, and name it `PMS Measures`. Go to **Settings**, then **Display**, and turn **off** "Scale to fit". Under **General**, set the **Data row limit** to **2000**.
3. **Data.** Connect these SharePoint lists: `people`, `measures`, `measure_roles`, `periods`, `submissions`, `submission_versions`, `review_comments`, `reference_values`, `rpt_values`, `export_requests`.
4. **Flows in the app.** Open the Power Automate pane and add `PMSSaveValue` and `PMSReview`.
5. **App formulas.** From [`powerapps/measures/App.pfx`](../powerapps/measures/App.pfx), paste the three blocks into `Formulas`, `StartScreen` and `OnStart`.
6. **Screens.** Paste them in this order, following the instructions at the top of each file:
   - `scrMeasHome` (make it the first screen)
   - `scrMeasSubmission`
   - `scrMeasTargets`
7. **Publish and share.** Then copy the app's web link (**Details**, then **Web link**) into the `measures_app_url` row in `settings`. The emails use it.

## Test script (with the sample data)

To test as different people, add yourself to `people` and give yourself roles in `measure_roles`. Alternatively, change the emails on a few sample roles to yours and colleagues'.

| # | As | Do | Expect |
|---|---|---|---|
| 1 | Updater of PM-0020 | Open To update | "Gender pay gap report, FY 2025-26: Expected, not received" is near the top |
| 2 | | Open it, choose No, and try to submit without a narrative | RAG shows Red, and the message asks for a narrative. Nothing is sent. |
| 3 | | Add a narrative and save a draft | "Draft saved." Version 1 appears. |
| 4 | | Change the narrative and save again | Still version 1. `audit_log` has the narrative change. |
| 5 | | Submit | The value is locked, the approver gets an email, and it appears in their To review tab |
| 6 | Approver | Return without a comment | You're asked for a comment |
| 7 | | Return with a comment | The updaters get an email with the comment. The status is Returned. |
| 8 | Updater | Open the email link, change the value to Yes and submit | Version 2. Under Versions, v2 shows "Changed since version 1: value (0 to 1), narrative." |
| 9 | Approver | Approve | Status Approved, RAG Green, the comment is marked resolved, and `rpt_values` gets a row with `is_latest` set to Yes |
| 10 | Admin | Reopen with a reason | Status Draft, with a note that reports still show version 2 |
| 11 | Updater | Submit a correction, then have it approved | Version 3 approved, version 2 superseded, and the reporting row shows version 3 |
| 12 | Anyone | Try to edit `submissions` in SharePoint | Not allowed: read only |
| 13 | Admin | Targets: pick a monthly KPI, Target, 450, this financial year | 12 rows saved. RAG on new submissions uses them. |

## Accessibility

It follows the same approach as the weekly app:
- **RAG is shown in words.** Colour is extra, never the only signal: "Red: off track", not just a red dot.
- **Live announcements.** Validation messages and the status line are announced to screen readers as they change.
- **Keyboard and touch:** every control has a visible label, focus is clearly visible, and targets are at least 40 pixels.
- **Small screens:** the two columns stack on narrow screens.

Run the App checker and a keyboard-only walkthrough before go-live.

## If pasting fails

See the same section in [weekly_app_guide.md](weekly_app_guide.md). The fixes are identical: control versions, the renamed Title column, and dropdown `Value` properties.
