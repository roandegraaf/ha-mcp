#!/usr/bin/env bashio

# Read configuration from Supervisor
TRANSPORT=$(bashio::config 'transport')
LOG_LEVEL=$(bashio::config 'log_level')

# Get Supervisor token for HA API access
HA_TOKEN="${SUPERVISOR_TOKEN}"
HA_URL="http://supervisor/core"

# Export environment variables for the MCP server
export HA_MCP_HA_URL="${HA_URL}"
export HA_MCP_HA_TOKEN="${HA_TOKEN}"
export HA_MCP_TRANSPORT="${TRANSPORT}"
export HA_MCP_HOST="0.0.0.0"
export HA_MCP_PORT=8099
export HA_MCP_LOG_LEVEL="${LOG_LEVEL}"

bashio::log.info "Starting Home Assistant MCP Server..."
bashio::log.info "Transport: ${TRANSPORT}"
bashio::log.info "Log Level: ${LOG_LEVEL}"

# Start the ingress web UI server in background
python3 -m http.server 8100 --directory /www &
bashio::log.info "Connection guide UI started on port 8100 (ingress)"

# Run the MCP server
exec python3 -m ha_mcp
