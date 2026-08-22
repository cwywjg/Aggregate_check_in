#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install.sh"
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="/opt/ykt"
CONFIG_DIR="/etc/ykt"
DATA_DIR="/var/lib/ykt"
SERVICE_USER="ykt"

required_files=(
  api_server.py
  ykt_ws_engine.py
  ykt_monitor.py
  ai_solver.py
  safe_json_store.py
  requirements.txt
)

for file in "${required_files[@]}"; do
  if [[ ! -f "${SOURCE_DIR}/${file}" ]]; then
    echo "Missing required file: ${SOURCE_DIR}/${file}"
    exit 1
  fi
done

if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${APP_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

install -d -m 0755 "${APP_DIR}" "${CONFIG_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "${DATA_DIR}"

for file in "${required_files[@]}"; do
  install -m 0644 "${SOURCE_DIR}/${file}" "${APP_DIR}/${file}"
done

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/venv/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"

if [[ ! -f "${CONFIG_DIR}/ykt.env" ]]; then
  install -m 0600 "${SOURCE_DIR}/deploy/ykt.env.example" "${CONFIG_DIR}/ykt.env"
  echo "Created ${CONFIG_DIR}/ykt.env"
  echo "Edit AI_PROVIDER and the selected provider API key before starting services."
fi

install -m 0644 "${SOURCE_DIR}/deploy/ykt-api.service" /etc/systemd/system/ykt-api.service
install -m 0644 "${SOURCE_DIR}/deploy/ykt-ws.service" /etc/systemd/system/ykt-ws.service
install -m 0644 "${SOURCE_DIR}/deploy/ykt-monitor.service" /etc/systemd/system/ykt-monitor.service

chown -R root:root "${APP_DIR}"
chmod -R go-w "${APP_DIR}"
systemctl daemon-reload

echo
echo "Installation complete."
echo "1. Edit: sudo nano /etc/ykt/ykt.env"
echo "2. Start: sudo systemctl enable --now ykt-api ykt-ws ykt-monitor"
echo "3. Check: sudo systemctl status ykt-api ykt-ws ykt-monitor"
echo "4. Logs : sudo journalctl -u ykt-api -u ykt-ws -u ykt-monitor -f"
