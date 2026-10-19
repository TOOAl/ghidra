# Brain.psm1 — PowerShell 모듈: Windows PowerShell에서 Claude Code처럼
# Import-Module .\Brain.psm1; Start-Brain -Interactive

function Start-Brain {
    param(
        [string]$Binary,
        [string]$Task,
        [string]$Preset = "",
        [string]$Provider,
        [string]$Model,
        [switch]$Interactive,
        [switch]$NoPreview
    )
    $root = $PSScriptRoot
    if(-not $root){ $root = (Get-Location).Path }
    $py = Get-Command python -ErrorAction SilentlyContinue
    if(-not $py){ $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if(-not $py){ Write-Error "python 없음"; return }
    $args = @("$root\brain_cli.py")
    if($Binary){ $args += @("--binary", $Binary) }
    if($Task){ $args += @("--task", $Task) }
    if($Preset){ $args += @("--preset", $Preset) }
    if($Provider){ $args += @("--provider", $Provider) }
    if($Model){ $args += @("--model", $Model) }
    if($Interactive -or -not $Task){ $args += @("--interactive") }
    if($NoPreview){ $args += @("--no-preview") }
    & $py.Source @args
}

function Invoke-BrainTask {
    param([Parameter(Mandatory)][string]$Task, [string]$Binary="E:\ghidra\examples\GhidraClaudeCode-Brain\run.py", [string]$Preset="")
    $body = @{task=$Task; binary=$Binary; preset=$Preset} | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8090/api/run -Body $body -ContentType "application/json"
}

function Get-BrainStatus {
    Invoke-RestMethod http://127.0.0.1:8090/api/status | Format-List
}

function Show-BrainPreview {
    Start-Process http://127.0.0.1:8090/ide
}

Export-ModuleMember -Function Start-Brain, Invoke-BrainTask, Get-BrainStatus, Show-BrainPreview
