const fs = require("fs");
const path = require("path");

const APP_DIR = process.env.YKT_APP_DIR || __dirname;
const ENV_FILE = process.env.YKT_ENV_FILE || path.join(APP_DIR, "ykt.env");
const PYTHON = process.env.YKT_PYTHON || path.join(APP_DIR, "venv", "bin", "python3");

function loadEnvFile(filename) {
  if (!fs.existsSync(filename)) {
    throw new Error(`Missing configuration file: ${filename}`);
  }
  const result = {};
  for (const originalLine of fs.readFileSync(filename, "utf8").split(/\r?\n/)) {
    const line = originalLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator <= 0) continue;
    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }
    result[key] = value;
  }
  return result;
}

const fileEnv = loadEnvFile(ENV_FILE);
const common = {
  cwd: APP_DIR,
  interpreter: PYTHON,
  exec_mode: "fork",
  instances: 1,
  autorestart: true,
  watch: false,
  restart_delay: 3000,
  max_restarts: 30,
  min_uptime: "10s",
  kill_timeout: 30000,
  time: true,
  merge_logs: true,
  env: {
    ...process.env,
    ...fileEnv,
    PYTHONUNBUFFERED: "1",
    PYTHONDONTWRITEBYTECODE: "1",
  },
};

module.exports = {
  apps: [
    {
      ...common,
      name: "ykt-api",
      script: "api_server.py",
      out_file: path.join(APP_DIR, "logs", "api.out.log"),
      error_file: path.join(APP_DIR, "logs", "api.error.log"),
    },
    {
      ...common,
      name: "ykt-ws",
      script: "ykt_ws_engine.py",
      restart_delay: 5000,
      out_file: path.join(APP_DIR, "logs", "ws.out.log"),
      error_file: path.join(APP_DIR, "logs", "ws.error.log"),
    },
    {
      ...common,
      name: "ykt-monitor",
      script: "ykt_monitor.py",
      restart_delay: 10000,
      out_file: path.join(APP_DIR, "logs", "monitor.out.log"),
      error_file: path.join(APP_DIR, "logs", "monitor.error.log"),
    },
  ],
};
