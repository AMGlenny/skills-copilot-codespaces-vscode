# How to add a measure

Until the admin screens arrive (phase 3), admins add measures straight into the SharePoint lists. It takes about five minutes.

## 1. Check it doesn't already exist

In `measures`, search for the name and the `source_ref`. If a retired measure is being brought back, set its status back to `active` rather than creating a new one, so its history stays joined up.

## 2. Add the measure

In `measures`, click **New** and fill in the fields below.

| Field | What to enter |
|---|---|
| measure_code | The next number after the highest existing code, e.g. PM-0023. Never reuse a code. |
| measure_name | A short, plain name. |
| source_ref and source_document | Exactly as the source document has them, e.g. `1.01` and `Housing Delivery Plan 2025-30`. A duplicate ref is fine. |
| parent_measure_code | The parent's measure_code if this rolls up into a summary measure. Otherwise blank. |
| description and definition | What it tells you, and exactly how it's calculated. |
| measure_class | `kpi` or `okr` if it's formally one; otherwise `measure`. Only kpi and okr can have a tolerance. |
| measure_type | `summary`, `output` or `outcome`. |
| unit | Choose from the list. For percent, people enter 58 for 58%. |
| decimal_places | How many decimal places to show. |
| polarity | `higher_is_better`, `lower_is_better`, or `neither` (no RAG). |
| frequency | How often a value is recorded. |
| aggregation_method | How to roll up to longer periods: sum for counts of activity, latest for snapshots, average for rates. |
| expected_lag_days | Typical days after period end before the data exists. Leave blank if there's no firm expectation. |
| category, data_source, org_unit_key | Category from `lookups`, where the data comes from, and the owning team from `org_units`. |
| status | `active`. |

## 3. Assign people

In `measure_roles`, add one row per person per role. The `role_key` is `measure_code|email|role`.

- exactly one **owner**
- at least one **updater** (the owner can also be an updater)
- at least one **approver**, who should not be the owner

## 4. Link to themes or programmes (optional)

In `measure_links`, add one row per group. The `link_key` is `measure_code|group_key`. Use `primary` for its main home, and `contributes_to` or `related` for the others.

## 5. Add targets (optional)

The easiest way is the **Targets** screen in the measures app: pick the measure, the type and a date range, and it writes one row per period. You can also add rows in `reference_values` by hand: one per measure, per period, per type, with `ref_key` set to `measure_code|period_key|ref_type`.

- Leave out targets entirely if there aren't any. The measure will show "No target set".
- Tolerance only counts for kpi and okr measures.

## 6. Submissions

You don't need to create anything. The `PMSCreateExpected` flow runs every morning and creates a `not_started` submission for every active measure when each of its periods ends. To create one straight away, for example for a period that has already ended, run that flow manually. It looks back 7 days.

## Retiring a measure

Set `status` to `retired` and fill in `retired_date` and `retired_reason`. Never delete a measure: its history stays in reports and exports.
