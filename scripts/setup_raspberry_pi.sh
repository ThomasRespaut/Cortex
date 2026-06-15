#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${CORTEX_VENV_DIR:-.venv}"
APT_INSTALL="${CORTEX_APT_INSTALL:-true}"

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
"$VENV_DIR/bin/python" tools/raspberry_pi_preflight.py --project-root .

echo "Environnement Raspberry Pi prêt dans ${VENV_DIR}."
echo "Smoke test headless: SDL_VIDEODRIVER=dummy CORTEX_FULLSCREEN=false CORTEX_SKIP_CORTEX_LOAD=true CORTEX_SCREENSHOT_PATH=artifacts/screen-smoke.png CORTEX_EXIT_AFTER_SCREENSHOT=true ${VENV_DIR}/bin/python Screen.py"
