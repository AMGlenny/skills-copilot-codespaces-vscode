# Setup guide

This creates every list, column, index and view on a SharePoint site and loads the sample data. You need to be an owner of the site. You don't need IT, PowerShell or a premium licence.

**Try it on a test site first.** The setup files have been checked for consistency, but they haven't been run against the GMCA tenant yet.

## 1. Check you are a site owner

1. Open the SharePoint site you want to use. A new, dedicated site is best.
2. Click the gear icon (top right), then **Site permissions**.
3. If your name is under **Site Owners**, you can carry on. If not, ask the site owner to add you, or ask IT for a new site.

## 2. Upload the setup files

1. In the site, open **Documents** and create a folder called `pms-setup`.
2. Upload these files from the `dist/setup` folder in this repository:
   - `01_schema.json`: creates the lists, columns, indexes and views (263 steps)
   - `02_seed.json`: loads the sample data (1,627 steps)

## 3. Build the setup flow (one off, about 10 minutes)

In Power Automate, choose **Create**, then **Instant cloud flow**. Name it `PMS setup` and pick **Manually trigger a flow**.

1. **Trigger:** add an input of type **Text** called `File name`.
2. **Initialize variable**
   - Name: `Failures`
   - Type: Array
   - Value: `[]`
3. **Get file content using path** (SharePoint)
   - Site address: your site
   - File path: `/Shared Documents/pms-setup/` followed by the `File name` dynamic content
   - Show advanced options, then set **Infer Content Type** to **No**
4. **Compose**, renamed to `Requests`. Expression:
   ```
   json(base64ToString(body('Get_file_content_using_path')?['$content']))
   ```
5. **Apply to each**
   - Input: `outputs('Requests')`
   - Open **Settings**, turn on **Concurrency control** and set the degree of parallelism to **1**. The schema steps must run in order.
6. Inside the loop, add **Send an HTTP request to SharePoint**
   - Site address: your site
   - Method: choose **Enter custom value**, then the expression `items('Apply_to_each')?['method']`
   - Uri: expression `items('Apply_to_each')?['uri']`
   - Headers: click **Switch to text mode**, then the expression `items('Apply_to_each')?['headers']`
   - Body: expression `items('Apply_to_each')?['body']`
7. Inside the loop, under the HTTP action, add **Append to array variable**
   - Name: `Failures`
   - Value (expression):
     ```
     addProperty(addProperty(json('{}'), 'step', items('Apply_to_each')?['step']), 'description', items('Apply_to_each')?['description'])
     ```
   - Open the action's menu, choose **Configure run after**, then tick **has failed** and untick **is successful**. It then only runs when a step fails.
8. After the loop, add **Create file** (SharePoint)
   - Folder path: `/Shared Documents/pms-setup`
   - File name: `errors-` followed by the `File name` dynamic content
   - File content: expression `string(variables('Failures'))`
   - Configure run after: tick **is successful** and **has failed**

Save the flow.

## 4. Run it

1. Run `PMS setup` with File name `01_schema.json`. It takes about 5 to 10 minutes.
2. Open **Site contents**. You should see 20 lists and a `snapshots` library.
3. Run it again with File name `02_seed.json`. It takes about 30 to 50 minutes. If you want it faster, set the loop's parallelism to 10 for this run only.
4. Open `pms-setup/errors-*.json`. It should contain `[]`.

**Re-running is safe.** Anything that already exists fails harmlessly: a list with the same name, or a duplicate key, since keys are unique. Those failures are listed in the errors file, and that's expected.

**Limits:** Power Automate on standard Microsoft 365 licences allows 5,000 items per loop, so each setup file stays under 4,000 steps. If a run slows down part way through, that's daily request throttling. Leave it running and it will finish.

## 5. Set permissions

Writes will go through flows running as a service account (phase 2 onwards), so people only need read access.

| Who | Where | Permission |
|---|---|---|
| Service account (until you have one: you) | Site Owners | Full control |
| System admins | Site Owners | Full control |
| Everyone else | Site Visitors | Read |

Then lock down wellbeing:

1. Open the `wellbeing_checkins` list, then the gear icon, then **List settings**, then **Permissions for this list**.
2. Click **Stop inheriting permissions**.
3. Select every group and click **Remove user permissions**.
4. Click **Grant permissions** and give only the service account **Edit**.

Line managers see their own team's individual responses through the app, and everyone else sees team counts, all served by flows.

Two more things to know:
- SharePoint administrators can always regain access to any list. Record that in your data protection impact assessment. A DPIA is recommended anyway, because wellbeing can be health data.
- The list is excluded from search, which also keeps it out of Copilot.

## 6. Check it worked

- Open `measures`, then the `active_measures` view. You should see 21 measures (the 22nd is retired).
- Open `submissions`, then the `expected_not_received` view. It should include the gender pay gap report (PM-0020). The view compares against today's date, so more rows appear as time passes.
- Open `rpt_values`, then **Export**, then **Export to CSV**. The file should have snake_case headers, ISO dates and one row per measure per period.
- In Power BI Desktop, go to **Get data**, then **SharePoint Online list**, and choose **Implementation 2.0**. Point it at the site and load `rpt_values`. It should need no joins.

If dates show a day out, check **Site settings**, then **Regional settings**, and set the time zone to London.

## Option B: PnP PowerShell

Use this only if IT is happy to support it. It runs exactly the same files.

1. **PowerShell version:** open PowerShell 7 and run `$PSVersionTable.PSVersion`. You need 7.4 or later.
2. **Install PnP:** run `Install-Module PnP.PowerShell -Scope CurrentUser`. If this is blocked, stop and use the flow method above.
3. **App registration:** PnP needs its own Entra ID app registration, which usually needs IT approval:
   ```powershell
   Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP PMS setup" -Tenant yourtenant.onmicrosoft.com -Interactive
   ```
4. **Run the setup files:**
   ```powershell
   ./scripts/Invoke-PmsSetup.ps1 -SiteUrl https://yourtenant.sharepoint.com/sites/performance -ClientId <app id> -RequestFile dist/setup/01_schema.json
   ./scripts/Invoke-PmsSetup.ps1 -SiteUrl https://yourtenant.sharepoint.com/sites/performance -ClientId <app id> -RequestFile dist/setup/02_seed.json
   ```

## Adding next year's periods

Run `python -m pms periods 2027`. This writes `dist/setup/periods_fy2027-28.json`, which you run through the same setup flow.

Before you run it, add the new term dates to `TERM_DATES` in `pms/periods.py`, or edit the term rows in the periods list afterwards. A scheduled flow will take over this job in a later phase.

## Starting without sample data

Skip `02_seed.json`. Then add your own `settings`, `lookups`, `org_units`, `people` and periods. You can take them from the seed file or the CSVs in `dist/seed_csv`.
