@echo off
chcp 65001 >nul
setlocal
:: 🚚 Windows Ghidra dist 배달 — fetch_ghidra_dist.ps1 의 얇은 래퍼.
::    더블클릭이나 cmd 에서 ExecutionPolicy 걱정 없이 돌리려고 존재해요.
::    실제 로직(오프라인 벤더 휠 설치 · 청크 재조립 · 체크섬 · PyGhidra 검증)
::    은 전부 .ps1 에 있고, 이건 그걸 Bypass 로 띄워 인자를 그대로 넘겨요.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fetch_ghidra_dist.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo ✅ Ghidra 배달 완료 — start_windows.bat 로 두뇌를 깨우세요.
) else (
  echo ❌ Ghidra 배달 실패 ^(exit %RC%^) — 위 메시지를 확인하세요.
)
endlocal & exit /b %RC%
