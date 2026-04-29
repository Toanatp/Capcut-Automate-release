# Capcut-Automate Release Repo

This repo is the dedicated release/artifact repo for the desktop updater.

It is scaffolded to match the updater contract currently used by `C:\Tool_All\Capcut-Automate`:

- manifest asset: `latest.json`
- signature asset: `latest.sig`
- package asset: `*.zip`
- digest asset: `*.sha256`

## Expected GitHub Release Assets

For each published version, upload:

1. the application archive, for example `Capcut-Automate-2.0.1.zip`
2. `latest.json`
3. `latest.sig` if signature verification is enabled
4. `Capcut-Automate-2.0.1.zip.sha256`

## Repo Layout

- `templates/latest.json`
  Manifest template for the updater
- `scripts/build-manifest.ps1`
  Generates `latest.json` and `<zip>.sha256` from a release zip

## Manifest Shape

The updater expects these fields:

```json
{
  "version": "2.0.1",
  "url": "https://github.com/<owner>/<repo>/releases/download/v2.0.1/Capcut-Automate-2.0.1.zip",
  "sha256": "<sha256>",
  "published_at": "2026-04-29T00:00:00Z",
  "release_url": "https://github.com/<owner>/<repo>/releases/tag/v2.0.1",
  "notes": "Release notes here",
  "signature": ""
}
```

## Typical Flow

1. Build the desktop package zip.
2. Create a Git tag such as `v2.0.1`.
3. Run:

```powershell
pwsh -File .\scripts\build-manifest.ps1 `
  -Version 2.0.1 `
  -ZipPath .\Capcut-Automate-2.0.1.zip `
  -Owner your-org `
  -Repo capcut-automate-release
```

4. Review the generated `latest.json`.
5. Optionally sign it and write the signature into `latest.sig` or the manifest `signature` field.
6. Upload the zip, `latest.json`, `latest.sig`, and `.sha256` to the GitHub Release.

## Notes

- This repo is intentionally separate from the source repo so release assets can be managed independently.
- If you want, the next step is to connect this folder to a real GitHub remote and add a publish script using `gh` or GitHub API.
