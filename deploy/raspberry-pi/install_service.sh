#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CORTEX_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SERVICE_NAME="${CORTEX_SERVICE_NAME:-cortex}"
SERVICE_USER="${CORTEX_SERVICE_USER:-${USER:-pi}}"
ENABLE_SERVICE="${CORTEX_ENABLE_SERVICE:-true}"
START_SERVICE="${CORTEX_START_SERVICE:-false}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LAUNCHER="${PROJECT_DIR}/scripts/launch_raspberry_pi.sh"

if [ "$(id -u)" -ne 0 ]; then
  echo "Relance avec sudo: sudo CORTEX_PROJECT_DIR='${PROJECT_DIR}' $0" >&2
  exit 1
fi

if [ ! -x "${LAUNCHER}" ]; then
  echo "Lanceur introuvable ou non exécutable: ${LAUNCHER}" >&2
  echo "Depuis le projet: chmod +x scripts/launch_raspberry_pi.sh" >&2
  exit 1
fi

cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=Cortex circular touchscreen interface
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
Environment=SDL_VIDEODRIVER=kmsdrm
Environment=SDL_TOUCH_MOUSE_EVENTS=0
Environment=SDL_MOUSE_TOUCH_EVENTS=0
Environment=CORTEX_FULLSCREEN=true
Environment=CORTEX_HIDE_CURSOR=true
Environment=CORTEX_PREVIEW_SIZE=900
Environment=CORTEX_FPS=60
Environment=CORTEX_SCREEN_SIZE=480x480
Environment=CORTEX_TOUCH_ROTATION=0
Environment=CORTEX_TOUCH_FLIP_X=false
Environment=CORTEX_TOUCH_FLIP_Y=false
Environment=CORTEX_TOUCH_ROUND_CLIP=true
Environment=CORTEX_TOUCH_EDGE_MARGIN=0
Environment=CORTEX_TOUCH_EDGE_CLAMP=true
Environment=CORTEX_ROUND_MASK=true
Environment=CORTEX_TOUCH_HIT_SLOP=10
Environment=CORTEX_TAP_MOVE_LIMIT=14
Environment=CORTEX_EMPTY_DOUBLE_TAP_MS=500
Environment=CORTEX_EMPTY_DOUBLE_TAP_DISTANCE=36
Environment=CORTEX_INPUT_MODE=voice
Environment=CORTEX_OUTPUT_MODE=voice
Environment=CORTEX_LOCAL_MODE=true
ExecStart=${LAUNCHER}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

if command -v systemd-analyze >/dev/null 2>&1; then
  systemd-analyze verify "${SERVICE_FILE}"
fi

systemctl daemon-reload

if [ "${ENABLE_SERVICE}" = "true" ]; then
  systemctl enable "${SERVICE_NAME}.service"
fi

if [ "${START_SERVICE}" = "true" ]; then
  systemctl restart "${SERVICE_NAME}.service"
fi

echo "Service installé: ${SERVICE_FILE}"
echo "Démarrage manuel: sudo systemctl start ${SERVICE_NAME}.service"
echo "Journal: sudo journalctl -u ${SERVICE_NAME}.service -f"
