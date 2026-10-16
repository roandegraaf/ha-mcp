"""Timer helper tools for Home Assistant."""

import json
import logging

from fastmcp import Context

from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)


def register_timer_tools(mcp_server):
    """Register timer helper tools on the MCP server."""

    @mcp_server.tool()
    async def create_timer(
        ctx: Context,
        name: str,
        duration: str,
        restore: bool = False,
        icon: str | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Create a timer helper in Home Assistant through its WebSocket API.

        Args:
            name: Timer name, as shown in Home Assistant.
            duration: Timer duration (for example, '00:05:00').
            restore: Restore the timer state after Home Assistant restarts.
            icon: Optional MDI icon (for example, 'mdi:timer-outline').
            skip_confirm: If True, skip the dry-run confirmation prompt.

        Returns a JSON object with the created timer details on success.
        """
        if not name.strip():
            return json.dumps({"error": "name must not be empty"})
        if not duration.strip():
            return json.dumps({"error": "duration must not be empty"})

        timer_config = {
            "name": name,
            "duration": duration,
            "restore": restore,
        }
        if icon:
            timer_config["icon"] = icon

        confirmed = await confirm_change(
            ctx,
            action="CREATE",
            entity_type="timer",
            identifier=name,
            config=timer_config,
            skip_confirm=skip_confirm,
        )
        if not confirmed:
            return json.dumps({
                "status": "cancelled",
                "message": "Timer creation cancelled",
            })

        ws, _rest = get_clients(ctx)
        try:
            result = await ws.send_command("timer/create", **timer_config)
            return json.dumps({"status": "created", "result": result}, indent=2)
        except Exception as exc:
            logger.error("Failed to create timer '%s': %s", name, exc)
            return json.dumps({"error": str(exc)})
