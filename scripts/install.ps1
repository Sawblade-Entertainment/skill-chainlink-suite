<#
.SYNOPSIS
  Install the ChainLink skills into a Claude Code skills directory.
.DESCRIPTION
  Installs into ~\.claude\skills by default.
  With no skill names, every skill in skills\ is installed.
.EXAMPLE
  .\scripts\install.ps1
.EXAMPLE
  .\scripts\install.ps1 -Project chainlink blink
.EXAMPLE
  .\scripts\install.ps1 -Target D:\game\.claude\skills -Force
#>
[CmdletBinding()]
param(
  [switch]$Project,    # install to .\.claude\skills (current directory)
  [string]$Target,     # install to this directory (overrides -Project)
  [switch]$Link,       # symlink instead of copying (needs Developer Mode or admin)
  [switch]$Force,      # replace skills that already exist
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Skills
)

$ErrorActionPreference = 'Stop'

$src = Join-Path (Split-Path -Parent $PSScriptRoot) 'skills'
if (-not $Target) {
  $Target = if ($Project) { Join-Path (Get-Location) '.claude\skills' } else { Join-Path $HOME '.claude\skills' }
}
if (-not $Skills) {
  $Skills = Get-ChildItem -Path $src -Directory | ForEach-Object Name
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null

foreach ($name in $Skills) {
  $from = Join-Path $src $name
  if (-not (Test-Path $from -PathType Container)) { throw "Unknown skill: $name" }
  $dest = Join-Path $Target $name

  if (Test-Path $dest) {
    if ($Force) {
      Remove-Item -Recurse -Force $dest
    } else {
      Write-Host "skip  $name (exists; use -Force to replace)"
      continue
    }
  }

  if ($Link) {
    New-Item -ItemType SymbolicLink -Path $dest -Target $from | Out-Null
    Write-Host "link  $name -> $dest"
  } else {
    Copy-Item -Recurse $from $dest
    Write-Host "copy  $name -> $dest"
  }
}
