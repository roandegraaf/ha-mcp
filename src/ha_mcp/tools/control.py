"""Device control tools: call arbitrary Home Assistant services.

This module expands the server beyond pure configuration management: it can
actuate devices (turn lights on/off, set a thermostat, etc.) by calling any HA
service. Calls go through the dry-run + confirm flow so changes are reviewed
before they are applied. Home Assistant also ships an official MCP Server
integration for Assist-style control; this tool is a lower-level complement.
"""

import json
import logging

from fastmcp import Context

from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)


def register_control_tools(mcp_server):
    """Register device-control tools on the MCP server."""

    @mcp_server.tool()
    async def call_service(
        ctx: Context,
        domain: str,
        service: str,
        data: str | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Call a Home Assistant service to control a device or trigger an action.

        Examples:
            - Turn on a light: domain='light', service='turn_on',
              data='{"entity_id": "light.kitchen", "brightness": 200}'
            - Set a thermostat: domain='climate', service='set_temperature',
              data='{"entity_id": "climate.living", "temperature": 21}'
            - Run a script: domain='script', service='turn_on',
              data='{"entity_id": "script.bedtime"}'

        Use ``list_services`` to discover valid domains, services, and fields,
        and ``resolve_target`` to preview which entities a target covers.

        Args:
            domain: Service domain (e.g. 'light', 'switch', 'climate').
            service: Service name (e.g. 'turn_on', 'set_temperature').
            data: Optional JSON object string with service data / target
                (e.g. entity_id, area_id, device_id, and service params).
            skip_confirm: If true, skip the dry-run confirmation prompt.

        Returns the list of states changed by the call (when HA reports them).
        """
        _ws, rest = get_clients(ctx)

        service_data: dict = {}
        if data:
            try:
                service_data = json.loads(data)
            except json.JSONDecodeError as exc:
                return json.dumps({"error": f"Invalid JSON in data: {exc}"})
            if not isinstance(service_data, dict):
                return json.dumps({"error": "data must be a JSON object."})

        if not await confirm_change(
            ctx=ctx, action="CALL", entity_type="service",
            identifier=f"{domain}.{service}", config=service_data,
            skip_confirm=skip_confirm,
        ):
            return json.dumps({"status": "cancelled", "message": "Service call cancelled."})

        result = await rest.call_service(domain, service, service_data)
        return json.dumps({
            "status": "called",
            "service": f"{domain}.{service}",
            "changed_states": result,
        }, indent=2)
