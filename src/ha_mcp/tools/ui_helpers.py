"""Tools for creating Group and Integral Sensor UI helpers."""

import json
import logging
from typing import Any

from fastmcp import Context

from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)

GROUP_TYPES = (
    "binary_sensor",
    "button",
    "cover",
    "event",
    "fan",
    "light",
    "lock",
    "media_player",
    "notify",
    "sensor",
    "switch",
    "valve",
)
GROUP_STATISTIC_TYPES = (
    "last",
    "first_available",
    "max",
    "mean",
    "median",
    "min",
    "product",
    "range",
    "stdev",
    "sum",
)
INTEGRAL_METHODS = ("trapezoidal", "left", "right")
INTEGRAL_TIME_UNITS = {
    "seconds": "s",
    "minutes": "min",
    "hours": "h",
    "days": "d",
}
INTEGRAL_UNIT_PREFIXES = ("k", "M", "G", "T")


async def _create_config_flow_helper(
    ctx: Context,
    handler: str,
    config: dict[str, Any],
    skip_confirm: bool,
    *,
    menu_step: str | None = None,
) -> str:
    """Create a config-entry helper through its Home Assistant UI config flow."""
    name = config["name"]
    entity_type = "group" if handler == "group" else "integral sensor"
    if not await confirm_change(
        ctx,
        action="CREATE",
        entity_type=entity_type,
        identifier=name,
        config=config,
        skip_confirm=skip_confirm,
    ):
        return json.dumps({
            "status": "cancelled",
            "message": f"{entity_type.title()} creation cancelled",
        })

    _ws, rest = get_clients(ctx)
    flow_id = None
    completed = False

    try:
        flow = await rest.start_config_flow(handler)
        flow_id = flow.get("flow_id")
        if not flow_id:
            return json.dumps({
                "error": f"Home Assistant did not start the {entity_type} config flow",
                "flow": flow,
            })

        if menu_step:
            if flow.get("type") != "menu":
                return json.dumps({
                    "error": f"Home Assistant did not open the {entity_type} type menu",
                    "flow": flow,
                })
            flow = await rest.submit_config_flow_step(
                flow_id,
                {"next_step_id": menu_step},
            )
            if flow.get("type") != "form" or flow.get("step_id") != menu_step:
                return json.dumps({
                    "error": f"Home Assistant did not open the {menu_step} group form",
                    "flow": flow,
                })
        elif flow.get("type") != "form" or flow.get("step_id") != "user":
            return json.dumps({
                "error": f"Home Assistant did not open the {entity_type} setup form",
                "flow": flow,
            })

        flow = await rest.submit_config_flow_step(flow_id, config)
        if flow.get("type") != "create_entry":
            return json.dumps({
                "error": f"Home Assistant did not create the {entity_type}",
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
        logger.error("Failed to create %s '%s': %s", entity_type, name, exc)
        return json.dumps({"error": str(exc)})
    finally:
        if flow_id and not completed:
            try:
                await rest.cancel_config_flow(flow_id)
            except Exception as exc:
                logger.warning(
                    "Failed to cancel unfinished %s config flow %s: %s",
                    entity_type,
                    flow_id,
                    exc,
                )


def register_ui_helper_tools(mcp_server):
    """Register Group and Integral Sensor helper creation tools."""

    @mcp_server.tool()
    async def create_group_helper(
        ctx: Context,
        name: str,
        group_type: str,
        entities: list[str],
        hide_members: bool = False,
        all_entities_on: bool = False,
        statistic_type: str | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Create a UI-managed Group helper from compatible entity IDs.

        Args:
            name: Group name shown in Home Assistant.
            group_type: Group type: binary_sensor, button, cover, event, fan,
                light, lock, media_player, notify, sensor, switch, or valve.
            entities: Member entity IDs, all of a domain compatible with the
                selected group_type.
            hide_members: Hide member entities from the Home Assistant UI.
            all_entities_on: For binary_sensor, light, and switch groups,
                require all members to be on rather than any member.
            statistic_type: Required for sensor groups. One of last,
                first_available, max, mean, median, min, product, range,
                stdev, or sum.
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the created group details.
        """
        if not name.strip():
            return json.dumps({"error": "name must not be empty"})
        if group_type not in GROUP_TYPES:
            return json.dumps({
                "error": f"Invalid group_type '{group_type}'. "
                f"Must be one of: {', '.join(GROUP_TYPES)}"
            })
        if not entities or any(not entity_id.strip() for entity_id in entities):
            return json.dumps({
                "error": "entities must contain at least one non-empty entity ID"
            })

        config: dict[str, Any] = {
            "name": name,
            "entities": entities,
            "hide_members": hide_members,
        }
        if group_type == "sensor":
            if statistic_type not in GROUP_STATISTIC_TYPES:
                return json.dumps({
                    "error": "sensor groups require a statistic_type from: "
                    f"{', '.join(GROUP_STATISTIC_TYPES)}"
                })
            config["type"] = statistic_type
        elif group_type in ("binary_sensor", "light", "switch"):
            config["all"] = all_entities_on

        return await _create_config_flow_helper(
            ctx,
            "group",
            config,
            skip_confirm,
            menu_step=group_type,
        )

    @mcp_server.tool()
    async def create_integral_sensor(
        ctx: Context,
        name: str,
        source_sensor: str,
        unit_time: str = "hours",
        method: str = "trapezoidal",
        unit_prefix: str | None = None,
        round_digits: int | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Create a UI-managed Integral Sensor helper from a numeric entity.

        Args:
            name: Integral sensor name shown in Home Assistant.
            source_sensor: Source entity ID from sensor, number, or input_number.
            unit_time: Integration time unit: seconds, minutes, hours, or days.
            method: Integration method: trapezoidal, left, or right.
            unit_prefix: Optional output unit prefix: k, M, G, or T.
            round_digits: Optional output precision from 0 to 6 digits.
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the created Integral Sensor details.
        """
        if not name.strip():
            return json.dumps({"error": "name must not be empty"})
        if not source_sensor.strip() or "." not in source_sensor:
            return json.dumps({
                "error": "source_sensor must be a valid entity ID"
            })
        if source_sensor.split(".", maxsplit=1)[0] not in {
            "sensor",
            "number",
            "input_number",
        }:
            return json.dumps({
                "error": "source_sensor must belong to sensor, number, or input_number"
            })
        if unit_time not in INTEGRAL_TIME_UNITS:
            return json.dumps({
                "error": f"Invalid unit_time. Must be one of: "
                f"{', '.join(INTEGRAL_TIME_UNITS)}"
            })
        if method not in INTEGRAL_METHODS:
            return json.dumps({
                "error": f"Invalid method. Must be one of: {', '.join(INTEGRAL_METHODS)}"
            })
        if unit_prefix is not None and unit_prefix not in INTEGRAL_UNIT_PREFIXES:
            return json.dumps({
                "error": f"Invalid unit_prefix. Must be one of: "
                f"{', '.join(INTEGRAL_UNIT_PREFIXES)}"
            })
        if round_digits is not None and not 0 <= round_digits <= 6:
            return json.dumps({"error": "round_digits must be between 0 and 6"})

        config = {
            "name": name,
            "source": source_sensor,
            "unit_time": INTEGRAL_TIME_UNITS[unit_time],
            "method": method,
        }
        if unit_prefix is not None:
            config["unit_prefix"] = unit_prefix
        if round_digits is not None:
            config["round"] = round_digits

        return await _create_config_flow_helper(
            ctx,
            "integration",
            config,
            skip_confirm,
        )
