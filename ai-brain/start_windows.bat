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
start "" "http://127.0.0.1:8765"
python "%~dp0launch_brain.py" --host 127.0.0.1 --port 8765
pause
