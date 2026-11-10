@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

:: 외장하드 포터블 모드: 모든 모델 경로를 현재 외장하드 안의 models 폴더로 고정! (C드라이브 오염 0%)
set "OLLAMA_MODELS=%~dp0models"

echo =========================================================
echo  🐣 나만의 외장하드 다마고치 AI 두뇌를 깨우는 중입니다...
echo  📂 서식지 경로: %~dp0
echo =========================================================

:: 외장하드 runtime 폴더에 llama-server.exe 와 models\*.gguf 가 있으면 자동 백그라운드 실행
for %%F in ("%~dp0models\*.gguf") do (
    if exist "%~dp0runtime\llama-server.exe" (
        echo [엔진 감지] 포터블 llama-server 로 %%~nxF 모델을 메모리에 올립니다...
        start "Portable-SLM" /min "%~dp0runtime\llama-server.exe" -m "%%~fF" --host 127.0.0.1 --port 8080 -c 4096
        goto :launch_ui
    )
)

:launch_ui
:: ── Ghidra 역공학 채널 사전검사 (논블로킹) ──────────
:: 두뇌는 Ghidra 없이도 깨어나요(objdump 폴백).  역공학 채널을 켜려면
:: 일회성으로 tools\fetch_ghidra_dist.bat 를 실행해 vendor 휠로 오프라인 세팅하세요.
if exist "%TEMP%\jdkenv\Scripts\python.exe" (
  echo [역공학 채널] Ghidra venv 감지 — analyzeHeadless 백엔드 활성화.
) else (
  echo [역공학 채널] Ghidra 미세팅 — objdump 폴백으로 깨어납니다.
  echo               Ghidra 를 켜려면: tools\fetch_ghidra_dist.bat  ^(일회성, 오프라인^)
)
start "" "http://127.0.0.1:8765"
python "%~dp0launch_brain.py" --host 127.0.0.1 --port 8765
pause
