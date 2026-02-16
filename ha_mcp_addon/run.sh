#!/usr/bin/env bash
set -e

# Debug: show what environment the Supervisor injected
echo "[DEBUG] SUPERVISOR_TOKEN set: $([ -n "${SUPERVISOR_TOKEN:-}" ] && echo yes || echo no)"
echo "[DEBUG] Environment variables from Supervisor:"
env | grep -i "supervisor\|hassio\|home_assistant" || echo "(none found)"
echo "[DEBUG] /data/options.json exists: $([ -f /data/options.json ] && echo yes || echo no)"

# Read configuration from /data/options.json directly (avoids Supervisor API dependency)
if [ -f /data/options.json ]; then
    TRANSPORT=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('transport', 'http'))")
    LOG_LEVEL=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('log_level', 'INFO'))")
else
    echo "[WARN] /data/options.json not found, using defaults"
    TRANSPORT="http"
    LOG_LEVEL="INFO"
fi

# Get Supervisor token for HA API access
HA_TOKEN="${SUPERVISOR_TOKEN:-}"
if [ -z "${HA_TOKEN}" ]; then
    echo "[FATAL] SUPERVISOR_TOKEN not available."
    echo "[FATAL] This add-on requires homeassistant_api: true in config.yaml."
    echo "[FATAL] Try fully uninstalling and reinstalling the add-on."
    exit 1
fi
HA_URL="http://supervisor/core"

# Export environment variables for the MCP server
export HA_MCP_HA_URL="${HA_URL}"
export HA_MCP_HA_TOKEN="${HA_TOKEN}"
export HA_MCP_TRANSPORT="${TRANSPORT}"
export HA_MCP_HOST="0.0.0.0"
export HA_MCP_PORT=8099
export HA_MCP_LOG_LEVEL="${LOG_LEVEL}"

echo "[INFO] Starting Home Assistant MCP Server..."
echo "[INFO] Transport: ${TRANSPORT}"
echo "[INFO] Log Level: ${LOG_LEVEL}"

# Start the ingress web UI server in background
python3 -m http.server 8100 --directory /www &
echo "[INFO] Connection guide UI started on port 8100 (ingress)"

# Run the MCP server
exec python3 -m ha_mcp
