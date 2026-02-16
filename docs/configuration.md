# Configuration

## Home Assistant Add-on

When running as a Home Assistant add-on, configuration is minimal.
The add-on authenticates automatically via the Supervisor API
token -- no access token or URL setup needed.

The add-on exposes two options in the **Configuration** tab:

| Option | Default | Description |
|--------|---------|-------------|
| `transport` | `http` | Transport protocol (`http` supports both streamable-HTTP and SSE fallback) |
| `log_level` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

The MCP server listens on port **8099**. You can change the host
port mapping in the add-on's **Network** panel.

After starting the add-on, open the **MCP Server** panel in the
sidebar (or click **OPEN WEB UI**) to get auto-detected,
copy-paste-ready connection configs for your MCP client.

## pip install (environment variables)

When running via `pip install`, the server is configured through
environment variables with the `HA_MCP_` prefix.

### `HA_MCP_HA_URL`

The base URL of your Home Assistant instance. Include the protocol
and port.

- **Default:** `http://homeassistant.local:8123`
- **Example:** `http://192.168.1.100:8123` or
  `https://ha.example.com`

The server automatically derives the WebSocket URL from this
value. An `http://` URL produces a `ws://` WebSocket connection,
and an `https://` URL produces a `wss://` connection. The
WebSocket endpoint is always `{url}/api/websocket`.

### `HA_MCP_HA_TOKEN`

A long-lived access token from Home Assistant. This is the only
required variable -- the server exits with an error if it isn't
set.

To generate a token:

1. Open your Home Assistant UI.
2. Navigate to your profile (click your user icon in the sidebar).
3. Scroll to the **Long-lived access tokens** section under
   **Security**.
4. Click **Create Token**, give it a name, and copy the value.

- **Default:** *(empty -- must be set)*
- **Example:** `eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp...`

> **Warning:** Treat this token like a password. Don't commit it
> to version control or share it publicly.

### `HA_MCP_TRANSPORT`

The transport protocol the MCP server uses to communicate with
clients.

- **Default:** `stdio`
- **Allowed values:** `stdio`, `http`

| Transport | Use case |
|---|---|
| `stdio` | Standard MCP client integration (Claude Desktop, Claude Code). The server reads from stdin and writes to stdout. |
| `http` | HTTP-based clients that connect over the network. Supports both streamable-HTTP and SSE fallback. The server starts a web server on the configured host and port. |

### `HA_MCP_HOST`

The host address to bind when using `http` transport.
This setting is ignored in `stdio` mode.

- **Default:** `0.0.0.0` (all interfaces)
- **Example:** `127.0.0.1` (localhost only)

### `HA_MCP_PORT`

The port to bind when using `http` transport. This
setting is ignored in `stdio` mode.

- **Default:** `8099`

### `HA_MCP_SKIP_CONFIRM_DEFAULT`

Controls the fallback behavior when an MCP client doesn't support
elicitation (the interactive confirm/cancel prompt).

- **Default:** `false`
- When `false`, unconfirmed changes are rejected if the client
  can't prompt the user.
- When `true`, changes proceed automatically without confirmation
  when elicitation isn't available.

Individual tool calls can also pass `skip_confirm=true` to bypass
the confirmation prompt on a per-call basis.

### `HA_MCP_LOG_LEVEL`

Controls the verbosity of server logs.

- **Default:** `INFO`
- **Allowed values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`

Set to `DEBUG` for detailed request and response logging during
development or troubleshooting.

## Client setup examples

### Using the add-on (HTTP transport)

The add-on runs the MCP server on port 8099. All clients connect
to:

```
http://<your-ha-hostname-or-ip>:8099/mcp/
```

Replace the hostname/IP below with your own. The add-on's
**Connection Guide** web UI can generate these for you
automatically.

#### Claude Code

Add to `.mcp.json` in your project root (or `~/.claude/.mcp.json`
for global access):

```json
{
  "mcpServers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

#### Claude Desktop

Requires Node.js for `mcp-remote`. Add to
`claude_desktop_config.json`:

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

#### Cursor

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

#### Windsurf

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

#### VS Code -- GitHub Copilot

Add to `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "home-assistant": {
      "url": "http://homeassistant.local:8099/mcp/"
    }
  }
}
```

#### VS Code -- Continue

Add to `.continue/config.yaml`:

```yaml
mcpServers:
  - name: home-assistant
    url: http://homeassistant.local:8099/mcp/
```

#### Other MCP clients

Any client that supports HTTP transport can connect directly to
`http://homeassistant.local:8099/mcp/`.

### Using pip install (stdio transport)

When running locally via pip, clients can launch the server
directly in stdio mode:

#### Claude Desktop

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

#### Claude Code

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

### Using pip install (HTTP transport)

Start the server manually, then connect any client to the URL:

```bash
export HA_MCP_HA_URL="http://homeassistant.local:8123"
export HA_MCP_HA_TOKEN="your-token"
export HA_MCP_TRANSPORT=http
ha-mcp
```

Then point your MCP client to `http://localhost:8099/mcp/`.

### Using a `.env` file

While the server doesn't load `.env` files natively, you can
source one before starting:

```bash
set -a
source .env
set +a
ha-mcp
```

Example `.env` file:

```
HA_MCP_HA_URL=http://192.168.1.50:8123
HA_MCP_HA_TOKEN=eyJhbGciOiJIUzI1NiIs...
HA_MCP_LOG_LEVEL=DEBUG
```

## Confirmation flow

All mutating operations (create, update, delete) use a dry-run
and confirm flow by default. When a tool is called:

1. The server builds the configuration and shows a YAML preview.
2. If validation is available, the result is included in the
   preview.
3. The server prompts the user to confirm or cancel through MCP
   elicitation.
4. Only confirmed changes are applied to Home Assistant.

This flow protects against accidental changes. You can bypass it
per-call with `skip_confirm=true` or globally by setting
`HA_MCP_SKIP_CONFIRM_DEFAULT=true`.
