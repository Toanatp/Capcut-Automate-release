param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [string]$ZipPath,

    [string]$Owner = "Toanatp",
    [string]$Repo = "Capcut-Automate-release",
    [string]$Notes = "",
    [string]$TokenFile = ".\.secrets\github-release-token.txt",
    [switch]$Prerelease
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $TokenFile)) {
    throw "Token file not found: $TokenFile"
}

$token = (Get-Content -LiteralPath $TokenFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Token file is empty."
}

$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$normalizedVersion = $Version.Trim()
if ($normalizedVersion.StartsWith("v", [System.StringComparison]::OrdinalIgnoreCase)) {
    $normalizedVersion = $normalizedVersion.Substring(1)
}
$tag = "v$normalizedVersion"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$resolvedZip = (Resolve-Path -LiteralPath $ZipPath).Path

& (Join-Path $scriptDir "build-manifest.ps1") `
    -Version $normalizedVersion `
    -ZipPath $resolvedZip `
    -Owner $Owner `
    -Repo $Repo `
    -Notes $Notes `
    -OutputDir $repoRoot

$zipName = [System.IO.Path]::GetFileName($resolvedZip)
$shaPath = Join-Path $repoRoot "$zipName.sha256"
$manifestPath = Join-Path $repoRoot "latest.json"

$releaseUri = "https://api.github.com/repos/$Owner/$Repo/releases"
$existing = $null
try {
    $existing = Invoke-RestMethod -Method Get -Uri "$releaseUri/tags/$tag" -Headers $headers
} catch {
    $existing = $null
}

if ($existing) {
    $release = $existing
} else {
    $body = @{
        tag_name = $tag
        name = $tag
        body = $Notes
        draft = $false
        prerelease = [bool]$Prerelease
    } | ConvertTo-Json -Depth 5

    $release = Invoke-RestMethod -Method Post -Uri $releaseUri -Headers $headers -Body $body -ContentType "application/json"
}

$uploadBase = [string]$release.upload_url
if ([string]::IsNullOrWhiteSpace($uploadBase)) {
    throw "GitHub release upload_url missing."
}
$uploadBase = $uploadBase -replace "\{\?name,label\}$", ""

function Upload-Asset {
    param(
        [string]$Path,
        [string]$ContentType
    )
    $name = [System.IO.Path]::GetFileName($Path)
    $uri = "${uploadBase}?name=$([System.Uri]::EscapeDataString($name))"
    Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -InFile $Path -ContentType $ContentType | Out-Null
}

Upload-Asset -Path $resolvedZip -ContentType "application/zip"
Upload-Asset -Path $shaPath -ContentType "text/plain"
Upload-Asset -Path $manifestPath -ContentType "application/json"

Write-Host "Release published: $($release.html_url)"
