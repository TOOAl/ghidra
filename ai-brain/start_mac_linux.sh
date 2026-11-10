#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

# 외장하드 포터블 모드: Ollama를 쓰더라도 모델이 호스트 PC가 아닌 외장하드 models/ 에 저장됨
export OLLAMA_MODELS="$SCRIPT_DIR/models"

echo "========================================================="
echo " 🐣 나만의 외장하드 다마고치 AI 두뇌를 깨우는 중입니다..."
echo " 📂 서식지 경로: $SCRIPT_DIR"
echo "========================================================="

FIRST_GGUF=$(ls -1 "$SCRIPT_DIR"/models/*.gguf 2>/dev/null | head -n 1 || true)
if [ -n "$FIRST_GGUF" ] && [ -x "$SCRIPT_DIR/runtime/llama-server" ]; then
    echo "[엔진 감지] 포터블 llama-server 로 $(basename "$FIRST_GGUF") 구동 중..."
    "$SCRIPT_DIR/runtime/llama-server" -m "$FIRST_GGUF" --host 127.0.0.1 --port 8080 -c 4096 >/dev/null 2>&1 &
    SLM_PID=$!
    trap 'kill "$SLM_PID" 2>/dev/null || true' EXIT INT TERM
fi

python3 "$SCRIPT_DIR/launch_brain.py" --host 127.0.0.1 --port 8765
