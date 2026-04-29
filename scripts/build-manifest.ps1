param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [string]$ZipPath,

    [Parameter(Mandatory = $true)]
    [string]$Owner,

    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [string]$PublishedAt = "",
    [string]$Notes = "",
    [string]$OutputDir = "."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $ZipPath)) {
    throw "Zip file not found: $ZipPath"
}

$resolvedZip = (Resolve-Path -LiteralPath $ZipPath).Path
$zipName = [System.IO.Path]::GetFileName($resolvedZip)
$normalizedVersion = $Version.Trim()
if ($normalizedVersion.StartsWith("v", [System.StringComparison]::OrdinalIgnoreCase)) {
    $normalizedVersion = $normalizedVersion.Substring(1)
}

$tag = "v$normalizedVersion"
if ([string]::IsNullOrWhiteSpace($PublishedAt)) {
    $PublishedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedZip).Hash.ToLowerInvariant()
$outputRoot = (Resolve-Path -LiteralPath $OutputDir).Path
$shaPath = Join-Path $outputRoot "$zipName.sha256"
$manifestPath = Join-Path $outputRoot "latest.json"

$downloadUrl = "https://github.com/$Owner/$Repo/releases/download/$tag/$zipName"
$releaseUrl = "https://github.com/$Owner/$Repo/releases/tag/$tag"

$manifest = [ordered]@{
    version = $normalizedVersion
    url = $downloadUrl
    sha256 = $sha256
    published_at = $PublishedAt
    release_url = $releaseUrl
    notes = $Notes
    signature = ""
}

Set-Content -LiteralPath $shaPath -Value "$sha256  $zipName" -Encoding utf8
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Generated:"
Write-Host " - $manifestPath"
Write-Host " - $shaPath"
