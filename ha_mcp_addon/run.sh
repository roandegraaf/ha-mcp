#!/usr/bin/env bash
set -e

# s6-overlay writes environment variables to files instead of inheriting them
# as shell env vars. Source them so SUPERVISOR_TOKEN etc. are available.
if [ -d /run/s6/container_environment ]; then
    for f in /run/s6/container_environment/*; do
        if [ -f "$f" ]; then
            export "$(basename "$f")=$(cat "$f")"
        fi
    done
fi

# Read configuration from /data/options.json directly (avoids Supervisor API dependency)
if [ -f /data/options.json ]; then
    TRANSPORT=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('transport', 'http'))")
    LOG_LEVEL=$(python3 -c "import json; print(json.load(open('/data/options.json')).get('log_level', 'INFO'))")
else
    TRANSPORT="http"
    LOG_LEVEL="INFO"
fi

# Get Supervisor token for HA API access
HA_TOKEN="${SUPERVISOR_TOKEN:-}"
if [ -z "${HA_TOKEN}" ]; then
    echo "[FATAL] SUPERVISOR_TOKEN not available. Ensure homeassistant_api is enabled in config.yaml."
    exit 1
fi

# Export environment variables for the MCP server
export HA_MCP_HA_URL="http://supervisor/core"
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

# Run the MCP server
exec python3 -m ha_mcp
