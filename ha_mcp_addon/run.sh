#!/usr/bin/env bash
set -e

# Debug: dump all environment info to diagnose missing SUPERVISOR_TOKEN
echo "[DEBUG] === Environment Diagnostics ==="
echo "[DEBUG] SUPERVISOR_TOKEN set: $([ -n "${SUPERVISOR_TOKEN:-}" ] && echo yes || echo no)"
echo "[DEBUG] All environment variables:"
env | sort
echo "[DEBUG] === End env ==="

# Check s6-overlay container environment (HA Supervisor may write vars here)
echo "[DEBUG] /run/s6/container_environment/ contents:"
ls -la /run/s6/container_environment/ 2>/dev/null || echo "(directory not found)"
if [ -d /run/s6/container_environment ]; then
    echo "[DEBUG] Files in container_environment:"
    for f in /run/s6/container_environment/*; do
        [ -f "$f" ] && echo "  $(basename "$f")=$(cat "$f")"
    done
fi

# Check for token in s6 environment and source it if present
if [ -f /run/s6/container_environment/SUPERVISOR_TOKEN ]; then
    echo "[DEBUG] Found SUPERVISOR_TOKEN in s6 container_environment"
    SUPERVISOR_TOKEN=$(cat /run/s6/container_environment/SUPERVISOR_TOKEN)
    export SUPERVISOR_TOKEN
fi

echo "[DEBUG] /data/options.json exists: $([ -f /data/options.json ] && echo yes || echo no)"
if [ -f /data/options.json ]; then
    echo "[DEBUG] /data/options.json contents:"
    cat /data/options.json
fi

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
    echo "[FATAL] SUPERVISOR_TOKEN not available in env or s6 container_environment."
    echo "[FATAL] This add-on requires homeassistant_api: true in config.yaml."
    echo "[FATAL] Ensure you fully uninstalled and reinstalled the add-on after config changes."
    echo "[FATAL] Check Settings > Add-ons > MCP Server > Configuration tab for API access toggle."
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
