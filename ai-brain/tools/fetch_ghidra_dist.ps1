<#
.SYNOPSIS
  🚚 Windows 판 Ghidra headless dist 배달 — fetch_ghidra_dist.sh 의 정확한 미러.

.DESCRIPTION
  외장하드 다마고치 AI 두뇌의 역공학 채널(Ghidra)을 Windows 에서 **오프라인**으로
  세팅해요.  저장소가 소유한 vendor\ 휠(jdk4py·jpype1 win_amd64 + pyghidra·
  packaging·typing_extensions py3-none-any)로 venv 를 만들어 네트워크 없이 설치하고,
  파이썬/플랫폼이 안 맞으면 정직하게 PyPI(무료)로 폴백해요.

  Ghidra dist 자체는 릴리스 에셋(allow-list 밖 호스트)이 아니라 **커밋된 orphan
  브랜치**(codeload.github.com, allow-list 안)에서 <=95MB 청크로 받아 재조립·
  체크섬 검증해요.  Linux/macOS 는 같은 폴더의 fetch_ghidra_dist.sh 를 쓰세요.

  요구 사항: Windows 10 1803+ (기본 제공 tar.exe 사용), Python 3.11 (x64) 권장.
  jpype1 벤더 휠은 cp311 태그라 Python 3.11 에서만 오프라인 설치되고, 다른
  파이썬이면 --no-index 가 실패 → PyPI(무료) 폴백으로 정직하게 설치해요.

.PARAMETER Branch
  Ghidra dist 가 실린 orphan 브랜치 (기본: ghidra-dist).
.PARAMETER Repo
  저장소 slug (기본: TOOAl/ghidra).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\fetch_ghidra_dist.ps1
#>
param(
  [string]$Branch = "ghidra-dist",
  [string]$Repo   = "TOOAl/ghidra"
)

$ErrorActionPreference = "Stop"

# 경로 해석 — tools\ 의 부모 = ai-brain, 그 부모 = 저장소 루트.
# 이식성: /tmp 하드코딩 대신 $env:TEMP(Windows temp). 사용자 홈경로 리터럴 금지.
$ScriptDir = $PSScriptRoot
$BrainDir  = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$Vendor    = Join-Path $BrainDir "vendor"
$Temp      = $env:TEMP
$Work      = Join-Path $Temp "ghidra_dl"
$Dest      = Join-Path $Temp "ghidra_dist"
$Venv      = Join-Path $Temp "jdkenv"
$VenvPy    = Join-Path $Venv "Scripts\python.exe"
$VenvPip   = Join-Path $Venv "Scripts\pip.exe"

Write-Host "── 🚚 Ghidra headless dist 배달 (Windows) ──"
Write-Host "  저장소 : $Repo"
Write-Host "  브랜치 : $Branch (orphan, disposable)"
Write-Host "  temp   : $Temp"

# ── 1) dist 받아 재조립 · 체크섬 검증 ────────────────────────────────────────
$Tgz = "$Work.tgz"
try {
  Invoke-WebRequest -UseBasicParsing -TimeoutSec 900 `
    -Uri "https://codeload.github.com/$Repo/tar.gz/refs/heads/$Branch" -OutFile $Tgz
} catch {
  Write-Host "  ❌ 브랜치 '$Branch' 를 가져올 수 없어요: $($_.Exception.Message)"
  Write-Host "     워크플로가 아직 안 돌았거나 이름이 다를 수 있어요: https://github.com/$Repo/actions"
  exit 3
}
if (Test-Path $Work) { Remove-Item -Recurse -Force $Work }
New-Item -ItemType Directory -Force -Path $Work | Out-Null
tar -xzf $Tgz -C $Work --strip-components=1
if ($LASTEXITCODE -ne 0) { Write-Host "  ❌ 바깥 tar.gz 전개 실패"; exit 3 }

$parts = @(Get-ChildItem -Path $Work -Filter "ghidra_headless.tgz.part*" -ErrorAction SilentlyContinue | Sort-Object Name)
$mb = [math]::Round((Get-Item $Tgz).Length / 1MB, 1)
Write-Host "  청크 $($parts.Count)개 받음 · $mb MB"

# 이진 안전 재조립 — Get-Content -Raw 는 바이너리를 깨뜨리므로 FileStream 으로.
$Full = Join-Path $Work "ghidra_headless.tgz"
$fs = [System.IO.File]::Create($Full)
try {
  foreach ($p in $parts) {
    $b = [System.IO.File]::ReadAllBytes($p.FullName)
    $fs.Write($b, 0, $b.Length)
  }
} finally { $fs.Close() }

$sumsFile = Join-Path $Work "SHA256SUMS.txt"
if (Test-Path $sumsFile) {
  $want = (Get-Content $sumsFile -Raw).Trim().ToLower()
  $got  = (Get-FileHash -Algorithm SHA256 -Path $Full).Hash.ToLower()
  if ($want -ne $got) { Write-Host "  ❌ checksum 불일치 (기대 $want / 실제 $got)"; exit 4 }
  Write-Host "  ✅ sha256 일치: $got"
} else {
  Write-Host "  ⚠ SHA256SUMS.txt 없음 — 체크섬 검증 건너뜀 (정직 고지)"
}

if (Test-Path $Dest) { Remove-Item -Recurse -Force $Dest }
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
tar -xzf $Full -C $Dest
if ($LASTEXITCODE -ne 0) { Write-Host "  ❌ dist 청크 전개 실패"; exit 4 }
$RootDir = Get-ChildItem -Path $Dest -Directory -Filter "ghidra_*" | Select-Object -First 1
if (-not $RootDir) { Write-Host "  ❌ ghidra_* 루트를 못 찾았어요: $Dest"; exit 5 }
$Root = $RootDir.FullName
$sizeMB = [math]::Round(((Get-ChildItem -Recurse -Path $Root | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host "  📂 $Root · $sizeMB MB"

# ── 2) venv + 저장소 소유 휠로 오프라인 설치 (안 되면 정직 PyPI 폴백) ──────────
if (-not (Test-Path $VenvPy)) {
  Write-Host "  ☕ venv + JDK 설치 중 (jdk4py → Temurin 25) …"
  if (Get-Command python -ErrorAction SilentlyContinue) { python -m venv $Venv }
  elseif (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv $Venv }
  else { Write-Host "  ❌ Python 없음 — python.org 에서 Python 3.11 (x64) 설치 후 다시"; exit 9 }
  if (-not (Test-Path $VenvPip)) { Write-Host "  ❌ venv pip 생성 실패"; exit 9 }

  # 📦 먼저 우리 벤더 휠(win_amd64·cp311 + py3-none-any)로 — 네트워크 없이.
  & $VenvPip install -q --no-index --find-links $Vendor jdk4py pyghidra jpype1 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  📦 벤더 휠로 설치 완료 (외부 연결 없음 — 오프라인)"
  } else {
    Write-Host "  📦 벤더 휠이 이 파이썬/플랫폼과 안 맞음 → PyPI 폴백 (무료)"
    & $VenvPip install -q jdk4py pyghidra jpype1
    if ($LASTEXITCODE -ne 0) { Write-Host "  ❌ PyPI 폴백도 실패 — Python 3.11 x64 인지 확인하세요"; exit 8 }
  }
} else {
  Write-Host "  ☕ 기존 venv 재사용: $Venv"
}

$JavaHome = (& $VenvPy -c "import jdk4py;print(jdk4py.JAVA_HOME)").Trim()
if (-not $JavaHome) { Write-Host "  ❌ jdk4py.JAVA_HOME 을 못 읽었어요"; exit 8 }
$env:JAVA_HOME = $JavaHome
$env:PATH = (Join-Path $JavaHome "bin") + ";" + $env:PATH
Write-Host "  ☕ JAVA_HOME = $JavaHome"

# ── 3) PyGhidra 사실 추출 + 숫자 검증 (실패하면 멈춰요 — 조용한 통과 없음) ─────
# Windows 네이티브 decompile.exe 는 glibc 를 요구하지 않으므로, Linux 의
# "숙주 glibc 불일치 → 소스 재주조" 단계가 필요 없어요 (그 단계는 .sh 전용).
$Headless = Join-Path $Root "support\analyzeHeadless.bat"
if (-not (Test-Path $Headless)) { Write-Host "  ❌ analyzeHeadless.bat 없음: $Headless"; exit 5 }
$env:GHIDRA_INSTALL_DIR = $Root

$Sample = Join-Path $RepoRoot "GhidraDocs\GhidraClass\ExerciseFiles\Advanced\globalRegVars.so"
if (-not (Test-Path $Sample)) { Write-Host "  ❌ 샘플 바이너리 없음: $Sample"; exit 5 }
$Facts = Join-Path $Temp "brain_facts.json"
if (Test-Path $Facts) { Remove-Item -Force $Facts }

Write-Host "  🔬 PyGhidra 사실 추출 (실패하면 여기서 멈춰요 — 조용한 통과 없음)"
& $VenvPy (Join-Path $ScriptDir "ghidra_facts_pyghidra.py") $Sample $Facts 400
if ($LASTEXITCODE -ne 0) { Write-Host "  ❌ PyGhidra 팩트 추출 실패 — 배달을 신뢰할 수 없어요"; exit 6 }

# 🚚 숫자로 증명: 진짜 Ghidra 출력인지, 디컴파일된 C 가 있는지, 산문 채널이
#    그대로인지.  verify 가 0 이 아니면 배달을 믿지 않아요.
& $VenvPy (Join-Path $ScriptDir "verify_ghidra_facts.py")
if ($LASTEXITCODE -ne 0) { Write-Host "  ❌ 검증 실패 — 배달을 신뢰할 수 없어요"; exit 6 }

Write-Host "── 배달 완료. ROOT=$Root ──"
Write-Host "  두뇌가 이 dist 를 자동 감지해요 (re_analyzer.ghidra_headless):"
Write-Host "    · GHIDRA_INSTALL_DIR 환경변수, 또는 $Dest\ghidra_*"
Write-Host "  PyGhidra 인터프리터 (re_analyzer.ghidra_python): $VenvPy"
Write-Host "  이제 launch_brain.py / start_windows.bat 를 띄우면 역공학 채널이 살아나요."
