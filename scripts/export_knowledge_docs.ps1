param(
    [string]$SourcePath,
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if (-not $SourcePath) {
    $SourcePath = Join-Path $ProjectRoot "data\synthetic\knowledge_docs\sources.json"
}
if (-not $OutputDir) {
    $OutputDir = Join-Path $ProjectRoot "data\synthetic\knowledge_docs\upload"
}

function ConvertTo-Slug {
    param([string]$Value)
    $slug = $Value.ToLowerInvariant()
    $slug = $slug -replace "[^a-z0-9]+", "-"
    $slug = $slug.Trim("-")
    if (-not $slug) {
        return "source"
    }
    return $slug
}

function Format-ListValue {
    param($Value)
    if ($null -eq $Value) {
        return ""
    }
    if ($Value -is [array]) {
        return ($Value -join ", ")
    }
    return [string]$Value
}

$ResolvedSource = Resolve-Path -LiteralPath $SourcePath
$ProjectRootResolved = (Resolve-Path -LiteralPath $ProjectRoot).Path
$OutputFullPath = [System.IO.Path]::GetFullPath($OutputDir)
$ExpectedRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "data\synthetic\knowledge_docs"))

if (-not $OutputFullPath.StartsWith($ExpectedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to export outside data\synthetic\knowledge_docs: $OutputFullPath"
}

New-Item -ItemType Directory -Force -Path $OutputFullPath | Out-Null

$Sources = Get-Content -LiteralPath $ResolvedSource -Raw | ConvertFrom-Json
$Written = @()
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

foreach ($Source in $Sources) {
    $Slug = ConvertTo-Slug "$($Source.source_id)-$($Source.title)"
    $Target = Join-Path $OutputFullPath "$Slug.md"
    $Url = if ($Source.url) { $Source.url } else { "synthetic-local-source" }
    $Tags = Format-ListValue $Source.tags
    $Metadata = if ($Source.metadata) {
        ($Source.metadata.PSObject.Properties | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
    } else {
        "- none"
    }

    $Markdown = @"
# $($Source.title)

Source ID: $($Source.source_id)

Source type: $($Source.source_type)

URL: $Url

Tags: $Tags

## Summary

$($Source.summary)

## Excerpt

$($Source.excerpt)

## Metadata

$Metadata

## Safety Boundary

This document is synthetic demo grounding content for a defensive SOC readiness agent. It contains no real employee records, customer data, tenant logs, credentials, secrets, real incidents, or real exam questions.
"@

    [System.IO.File]::WriteAllText($Target, "$Markdown`n", $Utf8NoBom)
    $Written += [PSCustomObject]@{
        source_id = $Source.source_id
        file = $Target.Substring($ProjectRootResolved.Length + 1)
    }
}

$ManifestPath = Join-Path $OutputFullPath "_manifest.json"
$ManifestJson = $Written | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($ManifestPath, "$ManifestJson`n", $Utf8NoBom)

Write-Host "Exported $($Written.Count) knowledge documents to $OutputFullPath"
Write-Host "Manifest: $ManifestPath"
