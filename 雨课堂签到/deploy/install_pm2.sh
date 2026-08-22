#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/ubuntu/ykt_server"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "$(id -un)" != "ubuntu" ]]; then
  echo "Please run as ubuntu: sudo -iu ubuntu"
  exit 1
fi

for command in python3 node pm2; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "Missing command: ${command}"
    exit 1
  fi
done

required_files=(
  api_server.py
  ykt_ws_engine.py
  ykt_monitor.py
  ai_solver.py
  safe_json_store.py
  requirements.txt
  ecosystem.config.cjs
)

for file in "${required_files[@]}"; do
  if [[ ! -f "${SOURCE_DIR}/${file}" ]]; then
    echo "Missing required file: ${SOURCE_DIR}/${file}"
    exit 1
  fi
done

if [[ "${SOURCE_DIR}" != "${APP_DIR}" ]]; then
  mkdir -p "${APP_DIR}"
  for file in "${required_files[@]}"; do
    install -m 0644 "${SOURCE_DIR}/${file}" "${APP_DIR}/${file}"
  done
  mkdir -p "${APP_DIR}/deploy"
  install -m 0644 "${SOURCE_DIR}/deploy/ykt.pm2.env.example" \
    "${APP_DIR}/deploy/ykt.pm2.env.example"
fi

cd "${APP_DIR}"
mkdir -p data logs
chmod 700 data
chmod 750 logs
python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt

if [[ ! -f ykt.env ]]; then
  install -m 0600 deploy/ykt.pm2.env.example ykt.env
  echo "Created ${APP_DIR}/ykt.env"
fi

chmod 600 ykt.env
pm2 startOrReload ecosystem.config.cjs --update-env
pm2 save

echo
echo "PM2 deployment completed."
echo "Edit config : nano ${APP_DIR}/ykt.env"
echo "Apply config: pm2 restart ecosystem.config.cjs --update-env"
echo "Status      : pm2 status"
echo "Logs        : pm2 logs"
echo
echo "Run once as root to enable boot startup:"
echo "sudo env PATH=\$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu"
echo "Then run as ubuntu: pm2 save"
