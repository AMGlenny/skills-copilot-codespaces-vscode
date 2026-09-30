# Flow: PMSExportRun

This one flow does every export: on demand from the apps, and scheduled.

- **Start:** it runs whenever a row is added to `export_requests`.
- **Where it writes:** it reads the dataset's definition, then writes one CSV per table, one Excel workbook with a sheet (and table) per table, `data_dictionary.csv`, `README_for_AI.md` and `export_info.txt` into a dated folder in the `snapshots` library.
- **Scheduled jobs:** it also copies the files to that job's `/latest` folder, so Power BI, Excel and Copilot always find the newest files at the same address.
- **Finish:** it records the link on the request and emails the person who asked.

The Office Script `PMSExport` turns the SharePoint rows into tidy rows. It does exactly what `transform()` and `to_csv()` in `pms/exports.py` do, and a test runs both on the same data to prove it.

## One-off setup

1. **Script:** in Excel for the web, open any workbook, go to **Automate**, then **New script**, paste [`office_scripts/PMSExport.ts`](../office_scripts/PMSExport.ts) and save it as **PMSExport**. Do this signed in as the account that owns the flow.
2. **Config folder:** in the `snapshots` library, create a folder called `_config`. Upload [`dist/exports/export_definitions.json`](../dist/exports/export_definitions.json) to it.
3. **Template:** in the same folder, create a blank workbook (**New**, then **Excel workbook**) and name it `export_template.xlsx`.
4. **Check the settings:** `export_definitions_path` and `export_template_path` in `settings` should point at those two files.

If you change the export definitions (`python -m pms build`), upload the new `export_definitions.json` again. The flow never needs editing for that.

## Steps

**Trigger:** SharePoint **When an item is created**, list `export_requests`.

**Initialise these variables** at the top of the flow:

| Variable | Type | Starting value |
|---|---|---|
| `varNext` | String | (empty) |
| `varCsv` | String | (empty) |
| `varFirst` | Boolean | true |
| `varFiles` | Array | `[]` |
| `varWindowStart` | String | (empty) |
| `varWindowEnd` | String | (empty) |

Then a `Try` scope and a `Catch` scope ([pattern 5](README.md#pattern-5-answer-the-app-even-when-something-fails)). Inside `Catch`, update the request with status `failed` and a message, and email the requester if there is one.

Everything below goes inside `Try`.

| # | Action | Name | Details |
|---|---|---|---|
| 1 | Compose | `Req` | `triggerOutputs()?['body']` |
| 2 | HTTP MERGE on `export_requests` item `@{outputs('Req')?['ID']}` | | `{"status": "running"}` |
| 3 | Read one item (twice) | `Defs_path`, `Template_path` | List `settings`, keys `export_definitions_path` and `export_template_path` |
| 4 | **Get file content using path** | `Get_defs` | Path: the `Defs_path` value. Infer Content Type: **No** |
| 5 | Compose | `Def` | `json(base64ToString(body('Get_defs')?['$content']))?['datasets']?[outputs('Req')?['dataset']?['Value']]` |
| 6 | Compose | `Folder` | `concat('/snapshots/', outputs('Req')?['folder_path'], '/', convertFromUtc(utcNow(), 'GMT Standard Time', 'yyyy-MM-dd_HHmm'), '_', outputs('Req')?['Title'])` |
| 7 | Condition | | `@not(empty(outputs('Req')?['quarter_label']))` |
| 7a | *(yes)* Read one item | `Quarter` | List `periods`, key `concat('Q-', replace(outputs('Req')?['quarter_label'], ' ', '-'))` |
| 7b | *(yes)* Set `varWindowStart` | | `concat(addDays(convertFromUtc(outputs('Quarter')?['start_date'], 'GMT Standard Time', 'yyyy-MM-dd'), -1, 'yyyy-MM-dd'), 'T12:00:00Z')` |
| 7c | *(yes)* Set `varWindowEnd` | | `concat(convertFromUtc(outputs('Quarter')?['end_date'], 'GMT Standard Time', 'yyyy-MM-dd'), 'T12:00:00Z')` |
| 8 | Four HTTP GETs | `Get_people`, `Get_org_units`, `Get_groups`, `Get_measures` | `_api/web/lists/getbytitle('<list>')/items?$select=<select>&$top=5000`, taking `<select>` from `export_definitions.json` under `lookup_tables` |
| 9 | Compose | `Lookups` | `{"people": @{body('Get_people')?['value']}, "org_units": @{body('Get_org_units')?['value']}, "groups": @{body('Get_groups')?['value']}, "measures": @{body('Get_measures')?['value']}}` |
| 10 | **Get file content using path** | `Get_template` | The `Template_path` value |
| 11 | **Create file** | `Create_xlsx` | Folder: `outputs('Folder')`. Name: `@{outputs('Req')?['dataset']?['Value']}.xlsx`. Content: `body('Get_template')`. Then **Append to array** `varFiles`: `body('Create_xlsx')?['Id']` |
| 12 | **Apply to each** over `outputs('Def')?['tables']` | | Set **Concurrency** to 1. Steps 12a to 12e go inside. |
| 12a | Compose | `Filter` | see below |
| 12b | Set variables | | `varNext` = `concat('_api/web/lists/getbytitle(''', item()?['list'], ''')/items?$select=', item()?['select'], if(empty(outputs('Filter')), '', concat('&$filter=', encodeUriComponent(outputs('Filter')))), '&$top=1000')`, `varFirst` = `true`, `varCsv` = empty |
| 12c | **Do until** `@equals(variables('varNext'), '')` | | Change its limits to Count 200. Steps i to v go inside. |
| 12c-i | HTTP GET | `Get_page` | Uri `variables('varNext')`, Accept `application/json;odata=nometadata` |
| 12c-ii | **Run script** (Excel Online (Business)) | `Run_script` | Location: your site. Document library: `snapshots`. File: `body('Create_xlsx')?['Id']`. Script: `PMSExport`. payload: `string(json(concat('{"mode":"table","first":', string(variables('varFirst')), ',"table":', string(items('Apply_to_each')), ',"items":', string(body('Get_page')?['value']), ',"lookups":', string(outputs('Lookups')), '}')))` |
| 12c-iii | Append to string variable `varCsv` | | `body('Run_script')?['result']` |
| 12c-iv | Set `varFirst` | | `false` |
| 12c-v | Set `varNext` | | `if(empty(body('Get_page')?['odata.nextLink']), '', concat('_api/', last(split(body('Get_page')?['odata.nextLink'], '/_api/'))))` |
| 12d | **Create file** | `Create_csv` | Folder `outputs('Folder')`. Name `@{items('Apply_to_each')?['name']}.csv`. Content `concat(decodeUriComponent('%EF%BB%BF'), variables('varCsv'))` |
| 12e | Append to array `varFiles` | | `body('Create_csv')?['Id']` |
| 13 | Run script | `Run_dictionary` | Same file and script. payload: `string(json(concat('{"mode":"dictionary","rows":', string(outputs('Def')?['dictionary']), '}')))` |
| 14 | Create file | | `data_dictionary.csv`, content `concat(decodeUriComponent('%EF%BB%BF'), body('Run_dictionary')?['result'])`. Append its Id to `varFiles`. |
| 15 | Create file | | `README_for_AI.md`, content `outputs('Def')?['readme']`. Append its Id. |
| 16 | Condition: `@not(empty(outputs('Def')?['prompt']))` | | **If yes:** create `prompt_quarterly_report.md` with content `replace(outputs('Def')?['prompt'], '{quarter}', outputs('Req')?['quarter_label'])`, and append its Id |
| 17 | Create file | | `export_info.txt`, content below. Append its Id. |
| 18 | Condition: `@not(empty(outputs('Req')?['job_code']))` (scheduled) | | **If yes:** **Create new folder** `/snapshots/@{outputs('Req')?['folder_path']}/latest` (it carries on if the folder exists), then **Apply to each** over `variables('varFiles')` with **Copy file**. Set the destination to that folder and "If another file is already there" to **Replace**. Then update the `export_jobs` row's `last_run_status` to `done`. |
| 19 | HTTP MERGE on the request | | `{"status": "done", "output_url": "<site url>@{outputs('Folder')}", "message": "@{length(outputs('Def')?['tables'])} tables written.", "completed_at": "@{utcNow()}"}` |
| 20 | Condition: `@not(empty(outputs('Req')?['requested_by']))` | | **If yes:** Send an email notification (V3) to the requester. Subject: `Your export is ready`. Body: the folder link. |

**Filter** (step 12a). The app's filter replaces the definition's filter on the dataset's main tables. Otherwise the definition's filter is used, with the quarter placeholders filled in:
```
if(and(equals(items('Apply_to_each')?['main'], true), not(empty(outputs('Req')?['odata_filter']))),
   outputs('Req')?['odata_filter'],
   replace(replace(replace(coalesce(items('Apply_to_each')?['filter'], ''),
       '{quarter_label}', coalesce(outputs('Req')?['quarter_label'], '')),
       '{window_start}', variables('varWindowStart')),
       '{window_end}', variables('varWindowEnd')))
```

**export_info.txt** (step 17):
```
dataset: @{outputs('Req')?['dataset']?['Value']}
request: @{outputs('Req')?['Title']}
requested_by: @{coalesce(outputs('Req')?['requested_by'], 'schedule')}
created_at: @{utcNow()}
filter: @{coalesce(outputs('Req')?['filter_label'], 'everything')}
```

## Limits to know

- **Page size:** each Run script call handles one page of up to 1,000 rows, which keeps it well inside the connector's size and time limits.
- **Daily script limit:** Office Scripts allow about 1,600 runs a day per account. The nightly full export uses about 30.
- **Large lists:** lists over 5,000 items are fine, because paging follows SharePoint's `nextLink`. Filters must use indexed columns, and the definitions only do.

## Test

1. Add a row to `export_requests` by hand, with dataset `measures`, folder_path `on_demand` and status `queued`.
2. Within a few minutes you should see `/snapshots/on_demand/<date>_<ref>/` containing:
   - `measures.xlsx`, with `values_flat` and `data_dictionary` sheets
   - `values_flat.csv`
   - `data_dictionary.csv`
   - `README_for_AI.md`
   - `export_info.txt`
3. Compare `values_flat.csv` with `dist/sample_exports/measures/values_flat.csv` in this repository. The columns and formats should match.
