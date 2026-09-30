<#
.SYNOPSIS
  Replays a setup request file (dist/setup/*.json) against a SharePoint site
  using PnP PowerShell. This is the alternative to the Power Automate setup
  flow; both run exactly the same requests.

.EXAMPLE
  ./scripts/Invoke-PmsSetup.ps1 -SiteUrl https://contoso.sharepoint.com/sites/performance `
      -ClientId 00000000-0000-0000-0000-000000000000 -RequestFile dist/setup/01_schema.json

.NOTES
  Needs PowerShell 7.4+, the PnP.PowerShell module, and an Entra ID app
  registration (ClientId) that IT has approved. See docs/setup_guide.md.
  Errors are logged and the script carries on, so it is safe to re-run:
  anything that already exists fails harmlessly and is skipped.
#>
param(
    [Parameter(Mandatory)] [string] $SiteUrl,
    [Parameter(Mandatory)] [string] $ClientId,
    [Parameter(Mandatory)] [string] $RequestFile,
    [string] $LogFile = "pms-setup-errors.csv"
)

$ErrorActionPreference = "Stop"
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId

$requests = Get-Content -Raw -Encoding UTF8 $RequestFile | ConvertFrom-Json
$failed = @()
$i = 0
foreach ($r in $requests) {
    $i++
    Write-Progress -Activity "PMS setup" -Status $r.description -PercentComplete (100 * $i / $requests.Count)
    $method = if ($r.headers.'X-HTTP-Method') { $r.headers.'X-HTTP-Method' } else { $r.method }
    $body = $r.body | ConvertTo-Json -Depth 20 -Compress
    try {
        Invoke-PnPSPRestMethod -Method $method -Url "/$($r.uri)" -Content $body `
            -ContentType $r.headers.'Content-Type' | Out-Null
    }
    catch {
        $failed += [pscustomobject]@{ step = $r.step; description = $r.description; error = $_.Exception.Message }
    }
}

Write-Host "$($requests.Count - $failed.Count) of $($requests.Count) requests succeeded."
if ($failed.Count) {
    $failed | Export-Csv -NoTypeInformation -Encoding UTF8 $LogFile
    Write-Host "Failures written to $LogFile. 'already exists' and 'duplicate value' errors on a re-run are expected."
}
