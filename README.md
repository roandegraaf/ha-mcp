# Home Assistant MCP Server

An MCP (Model Context Protocol) server for setting up and maintaining
Home Assistant with an AI assistant. It adds integrations through config
flows, organises devices and entities, builds automations, scripts,
scenes, helpers, dashboards and blueprints, fixes repairs, debugs
automation traces, and manages backups.

It is aimed at configuration, not day-to-day device control. The generic
`call_service` tool is off by default.

To test, ask your agent:
"List the tools you have available for Home Assistant."

"What is the current state of my Home Assistant entities?"

"Check my Home Assistant logs for any recent automation failures."

Stop the Agent's Behavior
In your VS Code chat, give the agent a strict system instruction to stop hitting the web API. Tell it:
"Stop attempting to access the Home Assistant REST API, login flows, or web interface directly. You do not have browser credentials. You must only interact with Home Assistant using the available MCP server tools."

Redirect the agent to use MCP
You can correct the AI's behavior by telling it to stop trying to bypass the system. Reply with:
"Do not try to hit the Home Assistant REST API directly. You are connected to the Home Assistant MCP server. Please use the MCP tools provided to you to check the current entity states or call services to diagnose the issue."

"Stop attempting to log into Home Assistant via the web auth flow. I have provided my Long-Lived Access Token in the .env file under HA_TOKEN, and my local URL under HA_URL. For any direct REST API calls you need to make to Home Assistant, read this .env file and pass the token as a Bearer token in the Authorization header."

1. The Discovery Prompt (Start here)
This forces the agent to read its available MCP capabilities and confirms it sees the trace tools.

"List all the Home Assistant MCP tools you currently have available for reading automations, logs, and traces. Do not execute them yet, just tell me their names and what they do."

2. The Specific Trace Prompt
Once you know the connection is active, trigger an automation in your house (like your garage door or a smart plug) so there is a fresh trace, then use this prompt:

"Fetch the latest trace for automation.[insert_your_automation_name_here]. Analyze the execution path and tell me if it completed successfully or if it stopped at a specific condition."

3. The Open-Ended Debugging Prompt
If you have an automation that has been failing, you can let the agent do the heavy lifting:

"Use your Home Assistant tools to check for any recent automation failures. Fetch the trace data for the failed run, read the corresponding YAML configuration for that automation, and explain exactly which step caused the failure."

If the agent successfully returns the JSON trace tree or describes the step-by-step execution path (e.g., "It passed the time trigger but stopped at the state condition"), your MCP server is fully configured and working perfectly.

## Features

- **Registry queries** -- list and search devices, entities, areas,
  floors, and labels
- **Registry editing** -- create/update/delete areas, floors, and
  labels; rename entities and devices, assign them to areas, attach
  labels, and hide/disable them
- **Device control** -- call any Home Assistant service to actuate
  devices (turn lights on/off, set a thermostat, run a script)
- **Integration management** -- list, reload, and enable/disable
  configured integrations (config entries)
- **Backups** -- list existing backups and create a new full backup
- **System control** -- reload a config domain, restart core (with a
  config check first), inspect core config, system health, and the
  available services
- **Live events** -- listen to Home Assistant events for a bounded
  window (e.g. to watch what a device does)
- **State inspection** -- read entity states, history, logbook
  entries, error logs, and render Jinja2 templates
- **Automation management** -- full CRUD, toggle, duplicate,
  execution-trace debugging, and conflict detection for automations
- **Script management** -- create, read, update, and delete scripts
- **Scene management** -- create, read, update, and delete scenes
- **Helper management** -- create, update, and delete input helpers
  (`input_boolean`, `input_number`, `input_text`, `input_select`,
  `input_datetime`, `input_button`)
- **Timer management** -- create timer helpers in Home Assistant
- **Template sensor management** -- create UI-managed Template sensors
  and binary sensors
- **Group and Integral Sensor helpers** -- create UI-managed entity
  groups and Riemann-sum integral sensors
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
- **Integration setup** -- start and step through config flows, options
  flows and subentry flows; handle discovered and ignored flows; delete
  integrations
- **Registries** -- list, search and edit devices, entities, areas,
  floors, labels and categories; remove orphaned entities and devices
- **Automations, scripts, scenes** -- full CRUD, validated against Home
  Assistant before saving, plus conflict detection
- **Helpers** -- `input_*`, `counter`, `timer` and `schedule`, and
  config-flow helpers (template, group, utility_meter, ...) via config
  flows
- **Dashboards and blueprints** -- views, cards, blueprint import and
  instantiation
- **Diagnostics** -- repairs, structured system log, automation/script
  traces, and discovery of the triggers, conditions and services
  available for a target
- **Backups** -- list, create, delete, and configure automatic backups
- **System** -- reload domains, restart core after a config check,
  system health
- **Guided workflows** -- six prompt templates

Tools added in 0.2.0 (config flows, registry removal, categories,
diagnostics, backup configuration, `counter`/`timer`/`schedule` helpers)
are not yet verified against a live Home Assistant.

## Security model

- MCP clients authenticate with an API key (`Authorization: Bearer
  <key>`). The add-on generates one on first start; the pip version
  refuses to serve HTTP without one.
- Confirmation is a server setting (`confirm_mode`), never a tool
  argument, so the model can't skip it.
- Every tool carries MCP annotations (read-only / destructive), so your
  client can auto-approve reads and prompt for changes.
- `read_only` mode exposes only read tools.
- Shell/Python execution, Supervisor services, stop/restart and recorder
  purge are blocked in `call_service` even when device control is on.

## Installation

### Home Assistant add-on (recommended)

1. **Settings > Add-ons > Add-on Store**, overflow menu (**⋮**) >
   **Repositories**, add `https://github.com/roandegraaf/ha-mcp`.
2. Install **Home Assistant MCP Server** and click **Start**.
3. Open the **MCP Server** panel in the sidebar. It shows your API key
   and ready-to-copy snippets for Claude Code, Claude Desktop, Cursor,
   VS Code and other clients.

For example, Claude Code:

```bash
claude mcp add --transport http --scope user home-assistant http://homeassistant.local:8099/mcp \
  --header "Authorization: Bearer <API_KEY>"
```

Claude Desktop (requires Node.js; Settings > Developer > Edit Config):

```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://homeassistant.local:8099/mcp",
               "--allow-http", "--header", "Authorization:${AUTH_HEADER}"],
      "env": { "AUTH_HEADER": "Bearer <API_KEY>" }
    }
  }
}
```

Claude Desktop's custom connectors can't reach a server on your LAN,
so use the config file above. See
[docs/configuration.md](docs/configuration.md#client-setup) for all
clients.

### pip install

Requires Python 3.11+ and a
[long-lived access token](https://www.home-assistant.io/docs/authentication/#your-account-profile).

```bash
pip install .
export HA_MCP_HA_URL="http://homeassistant.local:8123"
export HA_MCP_HA_TOKEN="<long-lived-access-token>"
ha-mcp            # stdio, for clients that launch the server themselves
```

For HTTP, an API key is required:

```bash
export HA_MCP_TRANSPORT=http
export HA_MCP_API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
ha-mcp            # serves http://127.0.0.1:8099/mcp
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `HA_MCP_HA_URL` | `http://homeassistant.local:8123` | Home Assistant base URL |
| `HA_MCP_HA_TOKEN` | *(required)* | Long-lived access token |
| `HA_MCP_TRANSPORT` | `stdio` | `stdio`, `http` or `sse` |
| `HA_MCP_HOST` | `127.0.0.1` | Bind address for `http`/`sse` |
| `HA_MCP_PORT` | `8099` | Port for `http`/`sse` |
| `HA_MCP_API_KEY` | *(empty)* | Required for `http`/`sse` |
| `HA_MCP_ALLOW_UNAUTHENTICATED` | `false` | Allow `http`/`sse` without a key (loopback only) |
| `HA_MCP_CONFIRM_MODE` | `client` | `client` (client's tool approval) or `elicit` (server-side prompt) |
| `HA_MCP_READ_ONLY` | `false` | Only expose read-only tools |
| `HA_MCP_ENABLE_DEVICE_CONTROL` | `false` | Expose `call_service` |
| `HA_MCP_LOG_LEVEL` | `INFO` | Logging level |

## Documentation

- [Configuration](docs/configuration.md) -- environment variables,
  transport options, and client setup
- [Tools reference](docs/tools.md) -- all 85 MCP tools with
  parameters and descriptions
- [Prompts reference](docs/prompts.md) -- guided workflow
  templates
- [Architecture](docs/architecture.md) -- project structure,
  module design, and extension guide
- [Configuration](docs/configuration.md) -- settings, confirmation,
  client setup
- [Tools reference](docs/tools.md) -- all 110 tools
- [Prompts reference](docs/prompts.md)
- [Architecture](docs/architecture.md)

## License

See [LICENSE](LICENSE).
