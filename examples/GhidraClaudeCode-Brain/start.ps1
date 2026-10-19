#Requires -Version 5.1
<#
.SYNOPSIS
  start.ps1 — 윈도우 원클릭 실행기 (더블클릭 가능)
  .env에 키를 넣어두면 매번 $env: 설정 없이 바로 8090에 붙는다.

사용법:
  1) .env.example을 .env로 복사 후 sk-or-... 붙여넣기
  2) 이 파일 우클릭 → PowerShell에서 실행 (또는 더블클릭)
  3) 브라우저가 http://127.0.0.1:8090 자동으로 뜬다

수동으로 키 넣고 바로 실행도 가능:
  .\start.ps1 -Preset openrouter_qwen3_free -Task "C2 찾아줘"
#>
param(
  [string]$Preset = "",
  [string]$Task = "",
  [string]$Binary = "/bin/ls",
  [switch]$NoBrowser,
  [switch]$Sync  # git pull 먼저
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

function Load-Dotenv {
  $envFile = Join-Path $Root ".env"
  if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
      $l = $_.Trim()
      if (-not $l -or $l.StartsWith("#") -or -not $l.Contains("=")) { return }
      $kv = $l.Split("=",2); $k=$kv[0].Trim(); $v=$kv[1].Trim().Trim('"').Trim("'")
      if ($k -and $v -and $v -notlike "*여기에*") { Set-Item -Path "env:$k" -Value $v; Write-Host "[start] .env $k 로드" -ForegroundColor DarkGray }
    }
  } else {
    Write-Host "[start] .env 없음 — .env.example을 .env로 복사 후 키를 넣으면 자동 적용" -ForegroundColor Yellow
  }
}

Load-Dotenv

# Python 찾기
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { Write-Error "python을 찾을 수 없음 — https://www.python.org 에서 Python 3.11 설치"; exit 1 }
$pyExe = $py.Source
Write-Host "[start] Python: $pyExe" -ForegroundColor Cyan

if ($Sync) {
  try { git pull origin arena/61934e9d-ghidra; Write-Host "[start] git pull 완료" -ForegroundColor Green } catch { Write-Host "[start] git pull 실패 (무시)" -ForegroundColor Yellow }
}

# 의존성 (pyyaml 휠 실패 시 openai+requests만)
try { & $pyExe -c "import openai,requests; print('deps ok')" 2>$null; Write-Host "[start] 의존성 OK" -ForegroundColor Green }
catch {
  Write-Host "[start] 의존성 설치 중..." -ForegroundColor Yellow
  & $pyExe -m pip install --upgrade pip setuptools wheel -q
  & $pyExe -m pip install openai requests -q
  try { & $pyExe -m pip install --only-binary=:all: pyyaml -q; Write-Host "[start] pyyaml OK" -ForegroundColor Green } catch { Write-Host "[start] pyyaml 휠 없음 — 없이 진행 (UI 모형 배지로 동작)" -ForegroundColor Yellow }
}

# 서버가 이미 켜져있나?
function Test-Server {
  try { $j = Invoke-RestMethod http://127.0.0.1:8090/api/status -TimeoutSec 2; Write-Host "[start] 서버 OK — default:$($j.default) presets:$($j.presets.Count) | LLM $($j.llm.mode) — $($j.llm.detail)" -ForegroundColor Green; return $j } catch { return $null }
}
$st = Test-Server

if (-not $st) {
  Write-Host "[start] 서버 시작: python ui/server.py → http://127.0.0.1:8090" -ForegroundColor Cyan
  $proc = Start-Process -FilePath $pyExe -ArgumentList "ui/server.py" -PassThru -WindowStyle Minimized
  Start-Sleep 1.5
  $st = Test-Server
  if (-not $NoBrowser) { Start-Process http://127.0.0.1:8090 }
  Write-Host "[start] 서버 PID $($proc.Id) — 끄려면 작업관리자에서 python 종료" -ForegroundColor DarkGray
} else {
  Write-Host "[start] 기존 서버 재사용" -ForegroundColor Cyan
  if (-not $NoBrowser) { Start-Process http://127.0.0.1:8090 }
}

if ($Preset) {
  Start-Sleep 0.5
  try { $r = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8090/api/set_model -Body (@{preset=$Preset}|ConvertTo-Json) -ContentType "application/json" -TimeoutSec 5; Write-Host "[start] 모델 교체: $Preset → $($r|ConvertTo-Json -Compress)" -ForegroundColor Green; Test-Server | Out-Null } catch { Write-Host "[start] 모델 교체 실패: $_" -ForegroundColor Red }
}

if ($Task) {
  Write-Host "[start] 작업 실행: $Task ($Binary, $Preset)" -ForegroundColor Cyan
  try {
    $body = @{task=$Task; binary=$Binary; preset=$Preset} | ConvertTo-Json
    $j = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8090/api/run -Body $body -ContentType "application/json" -TimeoutSec 60
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host $j.report
    Write-Host "`n[LLM] $($j.llm | ConvertTo-Json -Compress)" -ForegroundColor DarkGray
  } catch { Write-Host "[start] 실행 실패: $_" -ForegroundColor Red }
}

Write-Host "`n[start] 완료 — 브라우저 http://127.0.0.1:8090 에서 ▶ 실행을 눌러봐" -ForegroundColor Green
if (-not $Task) { Write-Host "팁: .\start.ps1 -Preset openrouter_qwen3_free -Task 'C2 찾아줘' 로 바로 실행 가능" -ForegroundColor DarkGray }
