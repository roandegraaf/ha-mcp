# CLAUDE.md

## Project
MCP server for Home Assistant configuration management. Python package at `src/ha_mcp/`, distributed as an HA add-on (`ha_mcp_addon/`) and via pip.

## Key Architecture
- **FastMCP v2.x** — decorators: `@mcp.tool()`, `@mcp.prompt()`, `@mcp.resource()`
- **Tools** registered via `register_*_tools(mcp_server)` pattern in each module
- **Clients** accessed via `from ha_mcp.util.context import get_clients` (NOT from server.py — causes circular import)
- **Mutating tools** use `confirm_change()` from `util/dry_run.py` for dry-run + confirm via `ctx.elicit()`
- All tool functions accept `ctx: Context` and return JSON strings
- Config via `pydantic-settings` with `HA_MCP_` env prefix
- Build system: hatchling (`pyproject.toml`)

## HA Add-on (`ha_mcp_addon/`)
- **Pre-built Docker images** pushed to GHCR (`ghcr.io/roandegraaf/ha-mcp-{arch}`)
- Architectures: amd64, aarch64 (no armv7 — Rust compilation fails on armv7 musl)
- Base images: `ghcr.io/home-assistant/{arch}-base-python:3.12-alpine3.19`
- **`init: false`** in config.yaml is required — HA Supervisor injects tini as PID 1 by default, which conflicts with the base image's s6-overlay init. Without this, you get `s6-overlay-suexec: fatal: can only run as pid 1`
- Dockerfile uses standard `CMD ["/run.sh"]` pattern (s6-overlay runs it via its init)
- **Ingress** on port 8100 serves Connection Guide web UI; MCP server on port 8099 (direct, not through ingress)
- Auth is automatic via Supervisor token (`SUPERVISOR_TOKEN` env var)
- `build-prep.sh` copies `src/`, `pyproject.toml`, `README.md` into `ha_mcp_addon/package/` before Docker build (source is outside addon build context)
- `ha_mcp_addon/package/` is gitignored

## Version Bumping
**Always bump `ha_mcp_addon/config.yaml` version when making addon changes.** HA caches Docker images by version tag — same tag = no re-pull, even after reinstall. The CI tags images with the version from config.yaml.

## CI
- `.github/workflows/build-addon.yml` — builds + pushes to GHCR on push to main
- PRs get build-only (no push) as smoke test
- GHCR packages must be set to **public** for HA to pull without auth

## Known Issues
- FastMCP static resources (no URI template params) don't support `ctx` parameter
- Circular import: `server.py` imports tools → tools must NOT import from `server.py` → use `util/context.py`

## Counts
- 54 tools, 6 prompts, 1 resource template, 34 source files
