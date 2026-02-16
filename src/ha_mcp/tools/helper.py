"""Helper (input entity) tools for managing Home Assistant input_* helpers via WebSocket API."""

import json
import logging

from fastmcp import Context

from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)

VALID_HELPER_TYPES = (
    "input_boolean",
    "input_number",
    "input_text",
    "input_select",
    "input_datetime",
    "input_button",
)


def _validate_helper_type(helper_type: str) -> None:
    """Raise ValueError if helper_type is not one of the supported types."""
    if helper_type not in VALID_HELPER_TYPES:
        raise ValueError(
            f"Invalid helper_type '{helper_type}'. "
            f"Must be one of: {', '.join(VALID_HELPER_TYPES)}"
        )


def register_helper_tools(mcp_server):
    """Register all helper (input entity) tools on the MCP server."""

    @mcp_server.tool()
    async def list_helpers(
        ctx: Context,
        helper_type: str | None = None,
    ) -> str:
        """List all input helper entities in Home Assistant.

        Returns a JSON array of state objects for input_boolean, input_number,
        input_text, input_select, input_datetime, and input_button entities.

        Args:
            helper_type: Optional filter to a specific helper type (e.g.
                'input_boolean', 'input_number'). When omitted, all input
                helper entities are returned.

        This is useful for discovering existing helpers or checking their
        current values before creating or updating them.
        """
        if helper_type is not None:
            _validate_helper_type(helper_type)

        _ws, rest = get_clients(ctx)
        states = await rest.get_states()

        if helper_type:
            prefix = f"{helper_type}."
            helpers = [s for s in states if s.get("entity_id", "").startswith(prefix)]
        else:
            helpers = [
                s
                for s in states
                if any(
                    s.get("entity_id", "").startswith(f"{ht}.")
                    for ht in VALID_HELPER_TYPES
                )
            ]

        return json.dumps(helpers, indent=2)

    @mcp_server.tool()
    async def create_helper(
        ctx: Context,
        helper_type: str,
        config: str,
        skip_confirm: bool = False,
    ) -> str:
        """Create a new input helper entity in Home Assistant.

        Args:
            helper_type: The type of helper to create. Must be one of:
                input_boolean, input_number, input_text, input_select,
                input_datetime, input_button.
            config: A JSON string containing the helper configuration. Common
                fields include 'name' and 'icon'. Type-specific fields:
                - input_number: min, max, step, mode, unit_of_measurement
                - input_text: min, max, pattern, mode
                - input_select: options (list of strings)
                - input_datetime: has_date, has_time
                - input_boolean: (no extra required fields)
                - input_button: (no extra required fields)
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the created helper details on success.
        """
        _validate_helper_type(helper_type)

        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"Invalid JSON in config: {exc}"})

        if not isinstance(config_dict, dict):
            return json.dumps({"error": "config must be a JSON object"})

        name = config_dict.get("name", helper_type)

        confirmed = await confirm_change(
            ctx,
            action="CREATE",
            entity_type=helper_type,
            identifier=name,
            config=config_dict,
            skip_confirm=skip_confirm,
        )
        if not confirmed:
            return json.dumps({"status": "cancelled", "message": "Create cancelled by user"})

        ws, _rest = get_clients(ctx)
        try:
            result = await ws.send_command(f"{helper_type}/create", **config_dict)
            return json.dumps({"status": "created", "result": result}, indent=2)
        except Exception as exc:
            logger.error("Failed to create %s helper '%s': %s", helper_type, name, exc)
            return json.dumps({"error": str(exc)})

    @mcp_server.tool()
    async def update_helper(
        ctx: Context,
        helper_type: str,
        entity_id: str,
        config: str,
        skip_confirm: bool = False,
    ) -> str:
        """Update an existing input helper entity in Home Assistant.

        Args:
            helper_type: The type of helper being updated. Must be one of:
                input_boolean, input_number, input_text, input_select,
                input_datetime, input_button.
            entity_id: The full entity ID of the helper to update (e.g.
                'input_boolean.my_toggle').
            config: A JSON string containing the fields to update. Only
                include fields you want to change (e.g. '{"name": "New Name"}').
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the updated helper details on success.

        Note: The helper_type must match the domain of the entity_id.
        """
        _validate_helper_type(helper_type)

        try:
            config_dict = json.loads(config)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"Invalid JSON in config: {exc}"})

        if not isinstance(config_dict, dict):
            return json.dumps({"error": "config must be a JSON object"})

        # Verify entity_id domain matches helper_type
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        if domain != helper_type:
            return json.dumps({
                "error": f"entity_id domain '{domain}' does not match helper_type '{helper_type}'"
            })

        # Get current state for preview context
        _ws, rest = get_clients(ctx)
        current_state = await rest.get_state(entity_id)
        current_name = entity_id
        if current_state and isinstance(current_state, dict):
            attrs = current_state.get("attributes", {})
            current_name = attrs.get("friendly_name", entity_id)

        preview = {"entity_id": entity_id, "current_name": current_name, "changes": config_dict}

        confirmed = await confirm_change(
            ctx,
            action="UPDATE",
            entity_type=helper_type,
            identifier=entity_id,
            config=preview,
            skip_confirm=skip_confirm,
        )
        if not confirmed:
            return json.dumps({"status": "cancelled", "message": "Update cancelled by user"})

        ws, _rest = get_clients(ctx)

        # The WS update command expects the internal ID. We pass entity_id and
        # let HA resolve it. The exact field name varies by HA version; we
        # include both common variants.
        update_payload = {helper_type + "_id": entity_id, **config_dict}

        try:
            result = await ws.send_command(
                f"{helper_type}/update", **update_payload
            )
            return json.dumps({"status": "updated", "result": result}, indent=2)
        except Exception as exc:
            logger.error("Failed to update %s '%s': %s", helper_type, entity_id, exc)
            return json.dumps({"error": str(exc)})

    @mcp_server.tool()
    async def delete_helper(
        ctx: Context,
        helper_type: str,
        entity_id: str,
        skip_confirm: bool = False,
    ) -> str:
        """Delete an input helper entity from Home Assistant.

        Args:
            helper_type: The type of helper to delete. Must be one of:
                input_boolean, input_number, input_text, input_select,
                input_datetime, input_button.
            entity_id: The full entity ID of the helper to delete (e.g.
                'input_boolean.my_toggle').
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object confirming the deletion or an error.

        Warning: This action is irreversible. The helper and its state history
        will be permanently removed.
        """
        _validate_helper_type(helper_type)

        # Verify entity_id domain matches helper_type
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        if domain != helper_type:
            return json.dumps({
                "error": f"entity_id domain '{domain}' does not match helper_type '{helper_type}'"
            })

        # Get current state for the confirmation preview
        _ws, rest = get_clients(ctx)
        current_state = await rest.get_state(entity_id)
        preview = {"entity_id": entity_id}
        if current_state and isinstance(current_state, dict):
            attrs = current_state.get("attributes", {})
            preview["friendly_name"] = attrs.get("friendly_name", entity_id)
            preview["current_state"] = current_state.get("state")
            preview["attributes"] = attrs

        confirmed = await confirm_change(
            ctx,
            action="DELETE",
            entity_type=helper_type,
            identifier=entity_id,
            config=preview,
            skip_confirm=skip_confirm,
        )
        if not confirmed:
            return json.dumps({"status": "cancelled", "message": "Delete cancelled by user"})

        ws, _rest = get_clients(ctx)

        try:
            result = await ws.send_command(
                f"{helper_type}/delete",
                **{helper_type + "_id": entity_id},
            )
            return json.dumps({"status": "deleted", "entity_id": entity_id, "result": result}, indent=2)
        except Exception as exc:
            logger.error("Failed to delete %s '%s': %s", helper_type, entity_id, exc)
            return json.dumps({"error": str(exc)})
