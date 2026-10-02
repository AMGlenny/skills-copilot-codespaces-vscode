# Go-live checklist

Work through this on a test site first, then again on the live site. Tick each line and note who did it and when.

## Governance

- [ ] **Data protection impact assessment** agreed. It needs to cover the wellbeing data, the fact that SharePoint admins can technically reach any list, and exports.
- [ ] **Owner.** A named owner for the system, and a named deputy.
- [ ] **Service account.** It exists, has a Microsoft 365 licence, and its password or credential is managed by IT. It owns every flow and every flow connection.
- [ ] **Licences.** IT has confirmed the daily Power Platform request limits for the service account and for users. Compare them with [capacity_and_limits.md](capacity_and_limits.md).
- [ ] **Office Scripts** are allowed for the service account (the Automate tab appears in Excel for the web).

## Setup ([setup_guide.md](setup_guide.md))

- [ ] **Site.** A dedicated SharePoint site, with its time zone set to London.
- [ ] **Setup files.** `01_schema.json` has run and the errors file is `[]`.
- [ ] **Starting data.** Either the sample data is loaded for testing and later cleared, or real starting data is loaded: people, org units, groups, lookups, settings, periods and measures.
- [ ] **Periods.** Periods exist for this financial year and next, and term dates are checked against the local authority calendars.
- [ ] **Permissions.** Set as in section 5 of the setup guide. Wellbeing is locked down, and the item-level settings are checked.
- [ ] **Deletion.** The "Contribute without delete" permission level is applied, and a test user can't delete an item.

## Flows ([flows/README.md](../flows/README.md))

- [ ] All seven flows ([flows/README.md](../flows/README.md)) are built, owned by the service account, and switched on.
- [ ] **Failure alerts.** Each flow's **Edit**, then **Settings**, then run failure notifications go to the system owner's mailbox.
- [ ] **Office Script.** The `PMSExport` script is saved in the service account. `export_definitions.json` and `export_template.xlsx` are in `/snapshots/_config/`.
- [ ] **App links.** `measures_app_url` and `weekly_app_url` are set in `settings`.

## Apps

- [ ] Both apps are published and shared with everyone who needs them.
- [ ] The test scripts in [weekly_app_guide.md](weekly_app_guide.md) and [measures_app_guide.md](measures_app_guide.md) have been run with people in each role: updater, approver, admin and viewer.
- [ ] **Wellbeing privacy.** A line manager sees their reports; a colleague sees only totals; a team of fewer than 5 sees nothing.
- [ ] **Manual accessibility checks.** Done ([accessibility.md](accessibility.md)) and the results recorded.

## Exports ([exports_guide.md](exports_guide.md))

- [ ] Each on-demand export works, and the requester gets an email.
- [ ] The scheduled jobs have produced a `/latest` folder for each dataset.
- [ ] Power BI connects to `/snapshots/full_model/latest/values_flat.csv`.
- [ ] The quarter pack plus its prompt produce a sensible draft in Copilot.
- [ ] No export contains wellbeing, review comments or line managers. Search the files to check.

## Before real data

- [ ] If the sample data was loaded, clear it: delete the test site, or start a fresh one. Don't delete rows from the live site.
- [ ] Measures are loaded with owners, updaters and approvers, and every measure has exactly one owner.
- [ ] Updaters and approvers have had a 20-minute walkthrough.
