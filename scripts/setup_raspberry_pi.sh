#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

bash -n scripts/launch_raspberry_pi.sh
bash -n deploy/raspberry-pi/install_service.sh

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${CORTEX_VENV_DIR:-.venv}"
APT_INSTALL="${CORTEX_APT_INSTALL:-true}"

"$PYTHON_BIN" tools/raspberry_pi_preflight.py \
  --project-root . \
  --skip-pygame-import \
  --skip-executable-check
"$PYTHON_BIN" -m compileall -q Screen.py app tools

if command -v apt-get >/dev/null 2>&1 && [ "$APT_INSTALL" = "true" ]; then
  sudo apt-get update
  sudo apt-get install -y \
    python3-venv \
    python3-dev \
    portaudio19-dev \
    libasound2-dev \
    libsdl2-2.0-0 \
    libsdl2-dev \
    libffi-dev
fi

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install -r requirements-raspberry-pi.txt
"$VENV_DIR/bin/python" -m pip check
chmod +x scripts/launch_raspberry_pi.sh deploy/raspberry-pi/install_service.sh
"$VENV_DIR/bin/python" tools/validate_raspberry_pi_ui.py \
  --project-root . \
  --size "${CORTEX_SCREEN_SIZE:-480x480}" \
  --step-timeout "${CORTEX_VALIDATE_STEP_TIMEOUT:-120}" \
  --touch-rotation "${CORTEX_TOUCH_ROTATION:-0}" \
  --screenshot artifacts/screen-smoke.png \
  --legacy-output-dir artifacts/legacy-screen-smoke \
  --modern-output-dir artifacts/modern-screen-smoke

echo "Environnement Raspberry Pi prêt dans ${VENV_DIR}."
echo "Smokes Pygame headless validés dans artifacts/."
