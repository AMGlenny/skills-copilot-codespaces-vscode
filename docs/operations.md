# Running the system

A runbook for the system owner: routine jobs, and what to do when something goes wrong.

## Routine

| When | Job | How |
|---|---|---|
| Every week | Check for failed flow runs | Failure emails go to the owner. You can also open Power Automate and look at **My flows**, then **Run history**. |
| Every month | Check the `expected_not_received` view | Chase owners of measures that are long overdue, or retire measures nobody reports any more |
| Every term | Nothing | Term periods are created a year ahead |
| Each February | Next year's periods | Run `python -m pms periods <next FY start year>` (or ask a developer), then run the file through the setup flow. Check the term rows. |
| Each summer | Next year's term dates | Edit the term rows in `periods` (the `term_dates` view) once the councils publish them |
| When someone joins | Add them | Add a row to `people` with their team and line manager, and roles in `measure_roles` if they update or approve. Then share the apps. |
| When someone leaves | Mark them inactive | Set `active` to No in `people` and their `measure_roles`. Never delete them: their history stays linked. Move their roles to someone else first. |
| When a measure changes | Change or retire it | See [adding_a_measure.md](adding_a_measure.md). If the definition changes in a way that breaks comparison, retire it and add a new one. |
| When an export changes | Rebuild and upload | Edit `pms/exports.py`, run `python -m pms build`, and upload `dist/exports/export_definitions.json` to `/snapshots/_config/` |
| Each year | Review capacity | Update the profile in `pms/capacity.py` with real numbers and rebuild [capacity_and_limits.md](capacity_and_limits.md) |

## When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| "Something went wrong" when saving a value | A flow failed | Open the flow's run history, find the failed run, and read the red step. Most often it's a changed site address or an expired connection. Fix it, then ask the person to try again. Steps before the failure stay saved, so check the value's screen and `audit_log` to see how far it got. |
| A value can't be submitted: "You can't change this value" | It's already submitted or approved, or the person isn't an updater | Check the submission status. Check `measure_roles` for the person, with `active` set to Yes. |
| An approver can't approve | They entered the value themselves | Another approver must review it. Add a second approver in `measure_roles` if needed. |
| An approved value is wrong | | An admin reopens it from the value screen, with a reason. Reports keep the old value until the correction is approved. |
| No "not started" rows after a period ended | PMSCreateExpected didn't run | Check its run history. Run it manually: it looks back 7 days, so it catches up. |
| An export email never arrives | PMSExportRun failed or is slow | Look at the request in `export_requests`: `status` and `message` say what happened. A failed export can be retried by adding a new request. |
| An export has a sheet with no rows | The filter matched nothing | Check `export_info.txt` for the filter used |
| Dates are one day out | Site time zone | Set **Site settings**, then **Regional settings**, to London |
| Flows are slow in the afternoon | Daily request limit throttling | See [capacity_and_limits.md](capacity_and_limits.md). Move EXP-FULL-NIGHTLY to weekly, or ask IT about a Process licence for the busiest flow. |
| Someone sees wellbeing they shouldn't | Permissions changed | Recheck section 5d of the setup guide straight away, and report it as a data incident |

## Where the truth lives

| Question | Where to look |
|---|---|
| Who changed a value, and when | `audit_log` (measures) or the item's version history (everything else) |
| What was reported for a quarter | The dated quarter pack folder in `snapshots` |
| What a column means | [data_dictionary.md](data_dictionary.md) |
| How a rule works | `pms/rules.py` and `pms/workflow.py`. The tests show worked examples. |
