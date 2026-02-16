# Tools reference

Home Assistant MCP Server exposes 54 tools organized into 10
categories. Each tool accepts a `ctx` parameter automatically
provided by the MCP framework -- you don't need to supply it.

Mutating tools (create, update, delete) include a `skip_confirm`
parameter. When `false` (the default), the tool shows a YAML
preview and asks you to confirm before applying the change.

## Registry tools

Tools for querying the Home Assistant device, entity, area, floor,
and label registries.

### `list_devices`

List all devices registered in Home Assistant.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `area_id` | `string` | No | Filter by area ID |
| `manufacturer` | `string` | No | Filter by manufacturer (case-insensitive) |
| `model` | `string` | No | Filter by model (case-insensitive) |

### `list_entities`

List all entities registered in Home Assistant.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `domain` | `string` | No | Filter by domain prefix (for example, `light`, `switch`) |
| `device_id` | `string` | No | Filter by device ID |
| `area_id` | `string` | No | Filter by area ID |

### `list_areas`

List all areas. No parameters.

### `list_floors`

List all floors. No parameters.

### `list_labels`

List all labels. No parameters.

### `get_entity_details`

Get detailed information about a specific entity, combining
registry data and live state.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | `string` | Yes | Entity ID (for example, `light.living_room`) |

### `search_entities`

Search entities by name, ID, or attributes using case-insensitive
substring matching.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | `string` | Yes | Search string |
| `domain` | `string` | No | Restrict search to a domain |

## State tools

Tools for reading entity states, history, logs, and rendering
templates.

### `get_all_states`

Get the current state of all entities. Returns entity ID, state
value, attributes, `last_changed`, and `last_updated` for each.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `domain` | `string` | No | Filter by domain |

### `get_entity_state`

Get the full current state of a single entity.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | `string` | Yes | Entity ID |

### `get_entity_history`

Get the state change history of an entity over a time period.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | `string` | Yes | Entity ID |
| `start_time` | `string` | No | ISO 8601 start time |
| `end_time` | `string` | No | ISO 8601 end time |

### `get_logbook`

Get human-readable logbook entries describing events.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | `string` | No | Filter to a specific entity |
| `start_time` | `string` | No | ISO 8601 start time |
| `end_time` | `string` | No | ISO 8601 end time |

### `get_error_log`

Get the raw content of the Home Assistant error log. No
parameters.

### `render_template`

Render a Jinja2 template string on the Home Assistant server.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `template` | `string` | Yes | Jinja2 template (for example, `{{ states('sensor.temperature') }}`) |

## Automation tools

Full CRUD operations for Home Assistant automations.

### `list_automations`

List all automations with their ID, alias, state, and
`last_triggered` timestamp. No parameters.

### `get_automation`

Get the full configuration of a single automation.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `automation_id` | `string` | Yes | Internal automation ID (not the `entity_id`) |

### `create_automation`

Create a new automation from a JSON configuration string.

The server parses the config, generates a UUID if no `id` is
present, validates the configuration against Home Assistant,
shows a YAML preview, and saves after confirmation.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `config` | `string` | Yes | JSON string with automation config (alias, triggers, conditions, actions) |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `update_automation`

Update an existing automation's configuration.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `automation_id` | `string` | Yes | Automation ID to update |
| `config` | `string` | Yes | JSON string with the new configuration |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `delete_automation`

Delete an automation. This action is irreversible.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `automation_id` | `string` | Yes | Automation ID to delete |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `toggle_automation`

Enable or disable an automation without modifying its
configuration. No confirmation required.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | `string` | Yes | Automation entity ID (for example, `automation.morning_lights`) |
| `enabled` | `boolean` | Yes | `true` to enable, `false` to disable |

### `duplicate_automation`

Duplicate an existing automation with a new UUID.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `automation_id` | `string` | Yes | Source automation ID |
| `new_alias` | `string` | No | Alias for the copy (defaults to original alias + " (Copy)") |

## Script tools

CRUD operations for Home Assistant scripts.

### `list_scripts`

List all scripts with entity ID, friendly name, state, and
`last_triggered`. No parameters.

### `get_script`

Get the full configuration of a script.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `script_id` | `string` | Yes | Object ID (for example, `morning_routine`, not `script.morning_routine`) |

### `create_script`

Create a new script. The `script_id` must contain only lowercase
letters, digits, and underscores.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `script_id` | `string` | Yes | Object ID for the new script |
| `config` | `string` | Yes | JSON string with script config (alias, sequence, fields, mode) |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `update_script`

Update an existing script. Replaces the entire configuration.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `script_id` | `string` | Yes | Script object ID |
| `config` | `string` | Yes | JSON string with the new configuration |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `delete_script`

Delete a script. This action is irreversible.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `script_id` | `string` | Yes | Script object ID |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

## Scene tools

CRUD operations for Home Assistant scenes.

### `list_scenes`

List all scenes with entity ID, friendly name, and state. No
parameters.

### `get_scene`

Get the full configuration of a scene.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `scene_id` | `string` | Yes | Scene identifier |

### `create_scene`

Create a new scene. The config must include a `name` and
`entities` map.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `config` | `string` | Yes | JSON string with scene config |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `update_scene`

Update an existing scene by merging new values into the current
configuration.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `scene_id` | `string` | Yes | Scene identifier |
| `config` | `string` | Yes | JSON string with updated fields |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `delete_scene`

Delete a scene. This action is irreversible.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `scene_id` | `string` | Yes | Scene identifier |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

## Helper tools

Tools for managing input helper entities (`input_boolean`,
`input_number`, `input_text`, `input_select`, `input_datetime`,
`input_button`).

### `list_helpers`

List all input helper entities.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `helper_type` | `string` | No | Filter by type (for example, `input_boolean`) |

### `create_helper`

Create a new input helper entity.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `helper_type` | `string` | Yes | One of: `input_boolean`, `input_number`, `input_text`, `input_select`, `input_datetime`, `input_button` |
| `config` | `string` | Yes | JSON string with helper config (name, icon, and type-specific fields) |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `update_helper`

Update an existing input helper entity.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `helper_type` | `string` | Yes | Helper type |
| `entity_id` | `string` | Yes | Entity ID to update |
| `config` | `string` | Yes | JSON string with updated config |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `delete_helper`

Delete an input helper entity. This action is irreversible.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `helper_type` | `string` | Yes | Helper type |
| `entity_id` | `string` | Yes | Entity ID to delete |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

## Dashboard tools

Tools for managing Lovelace dashboards, views, and cards.

### `list_dashboards`

List all Lovelace dashboards. No parameters.

### `get_dashboard_config`

Get the full Lovelace configuration of a dashboard.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `dashboard_id` | `string` | No | Dashboard ID (omit for the default dashboard) |

### `save_dashboard_config`

Save a complete Lovelace dashboard configuration. This replaces
the entire config and must include a `views` array.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `config` | `string` | Yes | JSON string with full dashboard config |
| `dashboard_id` | `string` | No | Dashboard ID (omit for the default dashboard) |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `get_view`

Get the configuration of a single view by index.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `view_index` | `integer` | Yes | Zero-based view index |
| `dashboard_id` | `string` | No | Dashboard ID |

### `add_view`

Add a new view to a dashboard.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `view_config` | `string` | Yes | JSON string with view config |
| `dashboard_id` | `string` | No | Dashboard ID |
| `position` | `integer` | No | Insert position (appended by default) |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `update_view`

Replace a view at a given index.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `view_index` | `integer` | Yes | Zero-based view index |
| `view_config` | `string` | Yes | JSON string with view config |
| `dashboard_id` | `string` | No | Dashboard ID |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `delete_view`

Delete a view by index. This action is irreversible.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `view_index` | `integer` | Yes | Zero-based view index |
| `dashboard_id` | `string` | No | Dashboard ID |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `add_card`

Add a card to a view in a dashboard.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `view_index` | `integer` | Yes | Zero-based view index |
| `card_config` | `string` | Yes | JSON string with card config |
| `dashboard_id` | `string` | No | Dashboard ID |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `update_card`

Replace a card at a specific position within a view.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `view_index` | `integer` | Yes | Zero-based view index |
| `card_index` | `integer` | Yes | Zero-based card index within the view |
| `card_config` | `string` | Yes | JSON string with card config |
| `dashboard_id` | `string` | No | Dashboard ID |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

## Blueprint tools

Tools for managing Home Assistant blueprints.

### `list_blueprints`

List available blueprints.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `domain` | `string` | No | Filter by domain (`automation` or `script`) |

### `get_blueprint`

Get the full configuration and input schema of a blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `domain` | `string` | Yes | Blueprint domain (`automation` or `script`) |
| `path` | `string` | Yes | Blueprint path |

### `import_blueprint`

Import a community blueprint from a URL.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `url` | `string` | Yes | URL of the blueprint to import |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

### `create_from_blueprint`

Create an automation or script from an existing blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `domain` | `string` | Yes | `automation` or `script` |
| `blueprint_path` | `string` | Yes | Path to the blueprint |
| `inputs` | `string` | Yes | JSON string with input values |
| `skip_confirm` | `boolean` | No | Skip the confirmation prompt |

## Configuration validation tools

Tools for validating configurations and YAML syntax.

### `validate_automation_config`

Validate an automation configuration against Home Assistant's
built-in validator.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `config` | `string` | Yes | JSON string with automation config |

### `check_config`

Check the Home Assistant core configuration for errors. This is
equivalent to the "Check Configuration" button in the Home
Assistant UI. No parameters.

### `validate_yaml`

Validate YAML syntax locally without connecting to Home
Assistant. Returns whether the YAML is valid, any parse errors,
and the parsed structure.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `yaml_text` | `string` | Yes | YAML text to validate |

## Suggestion tools

Proactive intelligence tools that analyze your setup and suggest
improvements.

### `analyze_devices`

Analyze device and entity coverage across areas. Identifies
devices with no automations, areas with limited coverage, and
unmonitored sensors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `area_id` | `string` | No | Focus analysis on a specific area |

### `suggest_automations`

Suggest new automations based on existing devices and entities.
Generates suggestions like motion-activated lighting, climate
schedules, leak alerts, and low battery notifications.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `entity_id` | `string` | No | Suggest automations for a specific entity |
| `area_id` | `string` | No | Suggest automations for a specific area |

### `detect_automation_conflicts`

Detect conflicts and redundancies between existing automations,
including overlapping triggers, contradictory actions, duplicate
automations, and race conditions. No parameters.

### `suggest_dashboard`

Suggest a Lovelace dashboard layout based on registered entities,
organized by area and domain with appropriate card types.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `area_id` | `string` | No | Focus suggestions on a specific area |
