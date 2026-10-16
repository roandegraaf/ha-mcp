"""Tools for creating Home Assistant Template sensor helpers."""

import json
import logging
from typing import Any

from fastmcp import Context

from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)


async def _create_template_entity(
    ctx: Context,
    entity_type: str,
    config: dict[str, Any],
    skip_confirm: bool,
) -> str:
    """Create a Template sensor entity through Home Assistant's config flow."""
    name = config["name"]
    if not await confirm_change(
        ctx,
        action="CREATE",
        entity_type=f"template {entity_type}",
        identifier=name,
        config=config,
        skip_confirm=skip_confirm,
    ):
        return json.dumps({
            "status": "cancelled",
            "message": f"Template {entity_type} creation cancelled",
        })

    _ws, rest = get_clients(ctx)
    flow_id = None
    completed = False

    try:
        flow = await rest.start_config_flow("template")
        flow_id = flow.get("flow_id")
        if flow.get("type") != "menu" or not flow_id:
            return json.dumps({
                "error": "Home Assistant did not start the Template config flow",
                "flow": flow,
            })

        flow = await rest.submit_config_flow_step(
            flow_id,
            {"next_step_id": entity_type},
        )
        if flow.get("type") != "form" or flow.get("step_id") != entity_type:
            return json.dumps({
                "error": f"Home Assistant did not open the {entity_type} setup form",
                "flow": flow,
            })

        flow = await rest.submit_config_flow_step(flow_id, config)
        if flow.get("type") != "create_entry":
            return json.dumps({
                "error": f"Home Assistant did not create the Template {entity_type}",
                "flow": flow,
            })

        completed = True
        return json.dumps({
            "status": "created",
            "entity_type": entity_type,
            "name": name,
            "result": flow.get("result"),
        }, indent=2)
    except Exception as exc:
        logger.error("Failed to create Template %s '%s': %s", entity_type, name, exc)
        return json.dumps({"error": str(exc)})
    finally:
        if flow_id and not completed:
            try:
                await rest.cancel_config_flow(flow_id)
            except Exception as exc:
                logger.warning(
                    "Failed to cancel unfinished Template config flow %s: %s",
                    flow_id,
                    exc,
                )


def register_template_entity_tools(mcp_server):
    """Register Template sensor and binary sensor creation tools."""

    @mcp_server.tool()
    async def create_template_sensor(
        ctx: Context,
        name: str,
        state_template: str,
        device_class: str | None = None,
        unit_of_measurement: str | None = None,
        state_class: str | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Create a UI-managed Template sensor helper in Home Assistant.

        Args:
            name: Sensor name shown in Home Assistant.
            state_template: Jinja2 template that produces the sensor state.
            device_class: Optional Home Assistant sensor device class.
            unit_of_measurement: Optional unit, such as '°C' or '%'.
            state_class: Optional sensor state class, such as 'measurement'.
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the created Template sensor details.
        """
        if not name.strip():
            return json.dumps({"error": "name must not be empty"})
        if not state_template.strip():
            return json.dumps({"error": "state_template must not be empty"})

        config = {"name": name, "state": state_template}
        if device_class:
            config["device_class"] = device_class
        if unit_of_measurement:
            config["unit_of_measurement"] = unit_of_measurement
        if state_class:
            config["state_class"] = state_class

        return await _create_template_entity(
            ctx, "sensor", config, skip_confirm
        )

    @mcp_server.tool()
    async def create_template_binary_sensor(
        ctx: Context,
        name: str,
        state_template: str,
        device_class: str | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Create a UI-managed Template binary sensor helper in Home Assistant.

        Args:
            name: Binary sensor name shown in Home Assistant.
            state_template: Jinja2 template that evaluates to true or false.
            device_class: Optional Home Assistant binary sensor device class.
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the created Template binary sensor details.
        """
        if not name.strip():
            return json.dumps({"error": "name must not be empty"})
        if not state_template.strip():
            return json.dumps({"error": "state_template must not be empty"})

        config = {"name": name, "state": state_template}
        if device_class:
            config["device_class"] = device_class

        return await _create_template_entity(
            ctx, "binary_sensor", config, skip_confirm
        )
