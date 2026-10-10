# Changelog

## 0.1.12

- Added configuration files browsing and reading tools:
  - `list_config_files`: Browse and glob files in the Home Assistant configuration directory with path-traversal sandboxing.
  - `get_config_file`: Read raw configuration file content (`configuration.yaml`, packages, templates) with `secrets.yaml` safety protection and regex-based credential redaction.
- Added Home Assistant CLI and Supervisor execution tools:
  - `run_ha_command`: Execute official Home Assistant CLI (`ha`) commands with argument parsing, raw JSON output, and dry-run safety confirmation for mutating actions.
  - `call_supervisor_api`: Direct programmatic invocation of Supervisor REST / WebSocket endpoints.
- Bundled official static `ha` CLI binary (`home-assistant/cli` releases) directly into the add-on container.
- Added GUI configuration toggle options in Home Assistant Add-on Settings:
  - `enable_config_files`: Toggle switch for configuration file tools (disabled by default).
  - `enable_ha_cli`: Toggle switch for `ha` CLI and Supervisor tools (disabled by default).
- Implemented conditional tool registration on the MCP server so disabled features are completely omitted from the tool schema, minimizing LLM context tokens.
- Bound Home Assistant configuration directory to `/homeassistant` in read-only mode (`map: ["homeassistant_config:ro"]`).
- Granted Supervisor API access with `manager` role (`hassio_api: true`, `hassio_role: manager`).

## 0.1.11

- Configured stateless Streamable HTTP transport session flags (`HA_MCP_STATELESS_HTTP="true"`, `FASTMCP_STATELESS_HTTP="true"`) for compatibility with stateless reverse proxies and MCP clients.

## 0.1.10

- Added category registry CRUD tools:
  - `list_categories`: List categories across scopes (`automation`, `script`, `scene`, `helpers`) or filtered by scope.
  - `create_category`: Create new categories with names and MDI icons.
  - `update_category`: Update existing category names and icons.
  - `delete_category`: Delete category definitions.
- Extended `update_entity` with `categories` parameter to allow assigning entities to registry categories per scope.
- Added unit tests for category management in `tests/test_categories.py`.

## 0.1.9

- Added system, control, registry-edit, backup, and event tools:
  - `registry_edit`: Area, floor, label, device, and entity mutations.
  - `control`: Direct device control via `call_service`.
  - `system`: System utilities (`get_config`, `get_system_health`, `list_services`, `reload_domain`, `restart_home_assistant`, `resolve_target`).
  - `backup`: `list_backups` and `create_backup`.
  - `events`: `listen_events` for bounded live event stream inspection.
  - `integration`: `list_integrations`, `reload_integration`, `set_integration_enabled`.
- Dry-run + confirm flow with elicitation for mutating actions.
- WebSocket client enhancements with subscription routing and tracking.

## 0.1.0

- Initial release.
- MCP server for Home Assistant configuration management.
- Automatic authentication via Supervisor token.
- HTTP transport with streamable-HTTP and SSE fallback.
- Dry-run and confirm flow for all mutating operations.
- Pre-built Docker images for amd64, aarch64, and armv7 via GHCR.
- Connection Guide web UI with auto-detected hostname and copy-to-clipboard configs for Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, and more.
