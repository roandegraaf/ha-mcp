# Changelog

## 0.1.10

- Expose recent Home Assistant automation traces through the
  `get_automation_traces` MCP tool

## 0.1.0

- Initial release
- MCP server with 54 tools for Home Assistant configuration management
- Automatic authentication via Supervisor token
- HTTP transport with streamable-HTTP and SSE fallback
- Dry-run and confirm flow for all mutating operations
- Pre-built Docker images for amd64, aarch64, and armv7 via GHCR
- Connection Guide web UI with auto-detected hostname and copy-to-clipboard configs for Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, and more
