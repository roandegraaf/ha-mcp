"""Backup tools: list existing backups and trigger a new backup.

These use the Home Assistant core backup WebSocket API (``backup/info`` and
``backup/generate``), available on modern HA installations with the ``backup``
integration loaded. Commands are issued best-effort: if the backup integration
is unavailable, a helpful error is returned rather than raising.
"""

import json
import logging

from fastmcp import Context

from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)


def register_backup_tools(mcp_server):
    """Register backup tools on the MCP server."""

    @mcp_server.tool()
    async def list_backups(ctx: Context) -> str:
        """List available Home Assistant backups.

        Returns backup metadata (slug/id, name, date, size) plus current backup
        state. Requires the core ``backup`` integration to be loaded.
        """
        ws, _rest = get_clients(ctx)
        try:
            result = await ws.send_command("backup/info")
        except Exception as exc:  # noqa: BLE001
            return json.dumps({
                "error": f"Could not list backups: {exc}",
                "hint": "Requires the 'backup' integration (Settings > System > Backups).",
            })
        return json.dumps(result, indent=2)

    @mcp_server.tool()
    async def create_backup(
        ctx: Context, name: str | None = None, skip_confirm: bool = False
    ) -> str:
        """Create a new full Home Assistant backup.

        Useful to snapshot the system before applying configuration changes.
        Requires the core ``backup`` integration. Generating a backup runs in
        the background and may take a while to complete.

        Args:
            name: Optional name for the backup.
            skip_confirm: If true, skip the confirmation prompt.
        """
        ws, _rest = get_clients(ctx)

        if not await confirm_change(
            ctx=ctx, action="CREATE", entity_type="backup",
            identifier=name or "full backup", config={"name": name} if name else {},
            skip_confirm=skip_confirm,
        ):
            return json.dumps({"status": "cancelled", "message": "Backup cancelled."})

        params = {"name": name} if name else {}
        try:
            result = await ws.send_command("backup/generate", **params)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({
                "error": f"Could not create backup: {exc}",
                "hint": "Requires the 'backup' integration (Settings > System > Backups).",
            })
        return json.dumps({"status": "started", "result": result}, indent=2)
