# Home Assistant MCP Server

This add-on runs an MCP (Model Context Protocol) server that gives AI assistants the ability to manage your Home Assistant configuration. It provides tools for reading device and entity states, creating and editing automations, scripts, scenes, helpers, dashboards, and blueprints.

## How it works

The add-on runs a standalone MCP server inside Home Assistant OS. It authenticates automatically using the Supervisor API token — no long-lived access token needed. MCP clients (like Claude Code or Claude Desktop) connect to the server over HTTP on port 8099.

Pre-built Docker images are pulled from GitHub Container Registry, so installation takes about a minute — even on a Raspberry Pi.

## Installation

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**.
2. Click the overflow menu (**⋮**) in the top right, then **Repositories**.
3. Paste the repository URL and click **Add**:
   ```
   https://github.com/roandegraaf/ha-mcp
   ```
4. Close the dialog. Find **Home Assistant MCP Server** in the store and click **Install**.
5. After installation, go to the **Configuration** tab. The defaults work for most setups.
6. Click **Start**.

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `transport` | `http` | Transport protocol. Use `http` (supports both streamable-HTTP and SSE fallback). |
| `log_level` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |

The server listens on port **8099** by default. You can change the host port mapping in the add-on's **Network** configuration panel.

## Connection Guide (Web UI)

After starting the add-on, open the **MCP Server** panel in the Home Assistant sidebar (or click **OPEN WEB UI** on the add-on page). This connection guide auto-detects your Home Assistant hostname and shows ready-to-copy configuration snippets for all popular MCP clients.

You can override the hostname if the auto-detected value is wrong (e.g., when connecting from an external network or through a reverse proxy).

## Connecting MCP clients

Your MCP server URL is:

```
http://<your-ha-hostname-or-ip>:8099/mcp/
```

Replace `<your-ha-hostname-or-ip>` with your Home Assistant's hostname or IP address (e.g., `homeassistant.local` or `192.168.1.50`). The easiest way to get a ready-to-use config is through the **Connection Guide** web UI above.

### Claude Code

Add to your project's `.mcp.json` (or `~/.claude/.mcp.json` for global access):

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

### Claude Desktop

Claude Desktop requires `mcp-remote` (via Node.js/npx) to connect to remote MCP servers. Add to your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "npx",
      "args": ["mcp-remote", "http://homeassistant.local:8099/mcp/"]
    }
  }
}
```

> **Prerequisite:** Node.js must be installed for `npx` to work.

### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "home-assistant": {
      "serverUrl": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

### VS Code (Copilot / Continue)

For **GitHub Copilot** in VS Code, add to your `.vscode/mcp.json`:

```json
{
  "servers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

For the **Continue** extension, add to `.continue/config.yaml`:

```yaml
mcpServers:
  - name: home-assistant
    url: http://homeassistant.local:8099/mcp/
```

### Other MCP clients

Any MCP client that supports HTTP transport can connect directly to:

```
http://homeassistant.local:8099/mcp/
```

## Troubleshooting

### Add-on won't start

Check the add-on logs for error messages. Common issues:

- **Port conflict:** Another service is using port 8099. Change the host port in the add-on's **Network** settings.
- **Missing Supervisor token:** The add-on requires `homeassistant_api: true` to receive the Supervisor token. This is configured automatically.

### MCP client can't connect

- Verify the add-on is running (check the add-on info panel).
- Ensure the port is exposed: in the add-on's **Network** configuration, the host port should be set (default: 8099).
- Try using the IP address instead of `homeassistant.local`.
- Check that your client and HA instance are on the same network, or that appropriate port forwarding is configured.

### "Unauthorized" or authentication errors

The add-on authenticates automatically via the Supervisor API. If you see auth errors in the logs, try restarting the add-on. If the issue persists, restart Home Assistant.

### Slow installation

The add-on uses pre-built Docker images from GitHub Container Registry. If installation is slow, check your internet connection. If the pre-built image is unavailable, HA will fall back to building from source, which can take 10-20 minutes on a Raspberry Pi.

## What this add-on can do

- **Registry queries** — list and search devices, entities, areas, floors, and labels
- **State inspection** — read entity states, history, logbook entries, error logs, and render Jinja2 templates
- **Automation management** — full CRUD, toggle, duplicate, and conflict detection
- **Script management** — create, read, update, and delete scripts
- **Scene management** — create, read, update, and delete scenes
- **Helper management** — manage input helpers (boolean, number, text, select, datetime, button)
- **Dashboard management** — manage Lovelace dashboards, views, and cards
- **Blueprint management** — list, import, and create from blueprints
- **Configuration validation** — validate automations, core config, and YAML syntax
- **Proactive suggestions** — analyze device coverage and suggest automations

All mutating operations go through a dry-run and confirm flow, so you can review changes before they are applied.
