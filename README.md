# Home Assistant MCP Server

An MCP (Model Context Protocol) server that gives AI assistants
the ability to manage Home Assistant configurations. It provides
tools for reading device and entity states, creating and editing
automations, scripts, scenes, helpers, dashboards, and blueprints,
and suggesting missing automations based on your setup.

> **Note:** This server manages *configurations* only. It doesn't
> directly control devices (for example, turning lights on or off).
> All configuration changes go through a dry-run and confirm flow
> so you can review changes before they are applied.

## Features

- **Registry queries** -- list and search devices, entities, areas,
  floors, and labels
- **State inspection** -- read entity states, history, logbook
  entries, error logs, and render Jinja2 templates
- **Automation management** -- full CRUD, toggle, duplicate, and
  conflict detection for automations
- **Script management** -- create, read, update, and delete scripts
- **Scene management** -- create, read, update, and delete scenes
- **Helper management** -- create, update, and delete input helpers
  (`input_boolean`, `input_number`, `input_text`, `input_select`,
  `input_datetime`, `input_button`)
- **Dashboard management** -- manage Lovelace dashboards, views,
  and cards
- **Blueprint management** -- list, import, and create automations
  or scripts from blueprints
- **Configuration validation** -- validate automation configs,
  check HA core configuration, and validate YAML syntax
- **Proactive suggestions** -- analyze device coverage, suggest
  automations, detect conflicts, and suggest dashboard layouts
- **Guided workflows** -- six prompt templates for common tasks
  like creating automations, building dashboards, and
  troubleshooting

## Installation

### Option 1: Home Assistant Add-on (recommended)

The easiest way to get started. No Python setup or access tokens
required -- the add-on authenticates automatically via the
Supervisor API. Pre-built images are pulled from GitHub Container
Registry, so installation takes about a minute.

1. In Home Assistant, go to **Settings > Add-ons > Add-on Store**.
2. Click the overflow menu (**⋮**) in the top right, then
   **Repositories**.
3. Paste the repository URL and click **Add**:
   ```
   https://github.com/roandegraaf/ha-mcp
   ```
4. Find **Home Assistant MCP Server** in the store and click
   **Install**.
5. Go to the add-on's **Configuration** tab. The defaults
   (`transport: http`, `log_level: INFO`) work for most setups.
6. Click **Start**.
7. Open the **MCP Server** panel in the sidebar (or click
   **OPEN WEB UI** on the add-on page) to get ready-to-copy
   connection configs for your MCP client.

#### Connecting your MCP client

The add-on exposes the MCP server at:

```
http://<your-ha-hostname-or-ip>:8099/mcp/
```

The add-on's built-in **Connection Guide** web UI auto-detects
your hostname and shows copy-paste configs for all popular
clients. Here are the most common ones:

**Claude Code** (`.mcp.json`):
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`, requires
Node.js for `mcp-remote`):
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

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

**Windsurf** (`~/.codeium/windsurf/mcp_config.json`):
```json
{
  "mcpServers": {
    "home-assistant": {
      "serverUrl": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

**VS Code -- GitHub Copilot** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

Replace `homeassistant.local` with your HA hostname or IP if
needed.

### Option 2: pip install (advanced)

For users running Home Assistant Core, or who want to run the
server on a separate machine.

**Prerequisites:**
- Python 3.11 or later
- A running Home Assistant instance (2024.1 or later recommended)
- A [long-lived access token](https://www.home-assistant.io/docs/authentication/#your-account-profile)

Install:
```bash
pip install .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick start (pip install)

1. Generate a long-lived access token in your Home Assistant
   profile (under **Security**).

2. Set the required environment variables:

   ```bash
   export HA_MCP_HA_URL="http://homeassistant.local:8123"
   export HA_MCP_HA_TOKEN="your-long-lived-access-token"
   ```

3. Run the server:

   ```bash
   ha-mcp
   ```

   The server starts in `stdio` transport mode by default, which
   is compatible with most MCP clients.

#### Connecting your MCP client (pip install)

When running via pip, the server runs locally on your machine.
You can use it in `stdio` mode (default) or `http` mode.

**stdio mode** -- Claude Desktop and Claude Code can launch the
server directly:

```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "ha-mcp",
      "env": {
        "HA_MCP_HA_URL": "http://homeassistant.local:8123",
        "HA_MCP_HA_TOKEN": "your-long-lived-access-token"
      }
    }
  }
}
```

**http mode** -- start the server manually, then point any MCP
client to the URL:

```bash
export HA_MCP_TRANSPORT=http
ha-mcp
```

Then connect to `http://localhost:8099/mcp/`.

## Configuration

All settings are controlled through environment variables with the
`HA_MCP_` prefix. When using the add-on, these are set
automatically -- you only need these for the pip install method.

| Variable | Default | Description |
|---|---|---|
| `HA_MCP_HA_URL` | `http://homeassistant.local:8123` | Home Assistant base URL |
| `HA_MCP_HA_TOKEN` | *(required)* | Long-lived access token |
| `HA_MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `HA_MCP_HOST` | `0.0.0.0` | Host to bind when using `http` transport |
| `HA_MCP_PORT` | `8099` | Port to bind when using `http` transport |
| `HA_MCP_SKIP_CONFIRM_DEFAULT` | `false` | Skip confirmation prompts when the client doesn't support elicitation |
| `HA_MCP_LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

For detailed configuration guidance, see
[docs/configuration.md](docs/configuration.md).

## Documentation

- [Configuration](docs/configuration.md) -- environment variables,
  transport options, and client setup
- [Tools reference](docs/tools.md) -- all 54 MCP tools with
  parameters and descriptions
- [Prompts reference](docs/prompts.md) -- guided workflow
  templates
- [Architecture](docs/architecture.md) -- project structure,
  module design, and extension guide

## License

This project is provided as-is. See the project repository for
license details.
