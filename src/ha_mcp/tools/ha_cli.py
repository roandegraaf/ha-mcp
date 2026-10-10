"""Tools for executing Home Assistant CLI ('ha') commands and Supervisor API calls."""

import asyncio
import json
import logging
import os
import shlex
from typing import Any

import aiohttp
from fastmcp import Context

from ha_mcp.config import settings
from ha_mcp.util.context import get_clients
from ha_mcp.util.dry_run import confirm_change

logger = logging.getLogger(__name__)

# Keywords that indicate a command mutates system or container state
MUTATING_ACTIONS = {
    "restart",
    "reboot",
    "shutdown",
    "update",
    "repair",
    "install",
    "uninstall",
    "restore",
    "remove",
    "wipe",
    "move",
    "sync",
    "reset",
    "start",
    "stop",
    "rebuild",
}

# Mapping common read-only ha commands to Supervisor REST endpoints (for fallback)
CLI_TO_ENDPOINT = {
    ("core", "check"): ("/core/check", "POST"),
    ("core", "info"): ("/core/info", "GET"),
    ("core", "stats"): ("/core/stats", "GET"),
    ("supervisor", "info"): ("/supervisor/info", "GET"),
    ("supervisor", "stats"): ("/supervisor/stats", "GET"),
    ("host", "info"): ("/host/info", "GET"),
    ("host", "services"): ("/host/services", "GET"),
    ("os", "info"): ("/os/info", "GET"),
    ("hardware", "info"): ("/hardware/info", "GET"),
    ("hardware", "audio"): ("/hardware/audio", "GET"),
    ("network", "info"): ("/network/info", "GET"),
    ("dns", "info"): ("/dns/info", "GET"),
    ("dns", "stats"): ("/dns/stats", "GET"),
    ("audio", "info"): ("/audio/info", "GET"),
    ("audio", "stats"): ("/audio/stats", "GET"),
    ("multicast", "info"): ("/multicast/info", "GET"),
    ("resolution", "info"): ("/resolution/info", "GET"),
    ("jobs", "info"): ("/jobs/info", "GET"),
    ("addons", "list"): ("/addons", "GET"),
    ("backups", "list"): ("/backups", "GET"),
    ("info",): ("/info", "GET"),
}


def _is_mutating_command(args: list[str]) -> bool:
    """Check if the CLI command is modifying state."""
    return any(arg.lower() in MUTATING_ACTIONS for arg in args)


async def _call_supervisor_ws_or_http(
    ctx: Context, endpoint: str, method: str = "GET", payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Invoke Supervisor API via HA WebSocket or HTTP."""
    clean_endpoint = "/" + endpoint.lstrip("/")
    ws, _rest = get_clients(ctx)

    # First attempt: Home Assistant Core WebSocket (hassio/api)
    try:
        ws_params = {
            "endpoint": clean_endpoint,
            "method": method.lower(),
        }
        if payload:
            ws_params["data"] = payload
        res = await ws.send_command("hassio/api", **ws_params)
        if isinstance(res, dict):
            return res
        return {"result": res}
    except Exception as ws_err:  # noqa: BLE001
        logger.debug("hassio/api websocket failed: %s; trying supervisor direct HTTP", ws_err)

    # Second attempt: Direct Supervisor HTTP API (inside add-on container)
    supervisor_url = settings.supervisor_url.rstrip("/")
    token = os.environ.get("SUPERVISOR_TOKEN") or settings.ha_token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    target_url = f"{supervisor_url}{clean_endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method.upper(), target_url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
                try:
                    return json.loads(text)
                except Exception:
                    return {"status_code": resp.status, "response": text}
    except Exception as http_err:  # noqa: BLE001
        return {"error": f"Failed to call supervisor API via WS ({ws_err}) and HTTP ({http_err})"}


def register_ha_cli_tools(mcp_server):
    """Register tools for running 'ha' commands and Supervisor API calls."""

    @mcp_server.tool()
    async def run_ha_command(
        ctx: Context,
        command: str,
        raw_json: bool = True,
        skip_confirm: bool = False,
    ) -> str:
        """Execute a Home Assistant CLI ('ha') command against Home Assistant OS / Supervisor.

        Runs CLI commands such as:
          - 'core check', 'core info', 'core restart'
          - 'supervisor info', 'supervisor reload', 'supervisor repair'
          - 'host info', 'host reboot'
          - 'os info', 'os update'
          - 'hardware info', 'network info', 'dns info'
          - 'addons list', 'addons info <slug>'
          - 'backups list'

        Mutating commands (reboot, restart, update, repair, install, etc.) trigger
        a dry-run confirmation prompt unless skip_confirm is True.

        Args:
            command: The CLI command to execute (e.g. 'core check', 'host info').
                Leading 'ha ' is automatically stripped if provided.
            raw_json: If True, request raw JSON output where supported.
            skip_confirm: If True, bypasses the confirmation prompt for mutating commands.
        """
        if not command or not command.strip():
            return json.dumps({"error": "Command string cannot be empty."})

        cleaned = command.strip()
        if cleaned.startswith("ha "):
            cleaned = cleaned[3:].strip()

        try:
            args = shlex.split(cleaned)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"error": f"Invalid command syntax: {exc}"})

        if not args:
            return json.dumps({"error": "No command arguments provided."})

        is_mutating = _is_mutating_command(args)
        if is_mutating:
            if not await confirm_change(
                ctx=ctx,
                action="EXECUTE",
                entity_type="ha_cli",
                identifier=f"ha {' '.join(args)}",
                config={"command": f"ha {' '.join(args)}"},
                skip_confirm=skip_confirm,
            ):
                return json.dumps({"status": "cancelled", "message": f"Execution of 'ha {' '.join(args)}' cancelled."})

        # Check if local ha binary is present and executable
        cli_path = settings.ha_cli_path
        if os.path.isfile(cli_path) and os.access(cli_path, os.X_OK):
            exec_args = list(args)
            if raw_json and "--raw-json" not in exec_args and "-j" not in exec_args:
                # Add --raw-json if not already present
                exec_args.append("--raw-json")

            try:
                proc = await asyncio.create_subprocess_exec(
                    cli_path,
                    *exec_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = await proc.communicate()
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

                data = None
                try:
                    data = json.loads(stdout)
                except Exception:
                    pass

                return json.dumps({
                    "command": f"ha {' '.join(args)}",
                    "exit_code": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "data": data,
                }, indent=2)
            except Exception as exc:  # noqa: BLE001
                return json.dumps({"error": f"Subprocess execution failed: {exc}"})

        # Fallback to Supervisor API when ha binary is not installed
        cmd_key = tuple(arg.lower() for arg in args if not arg.startswith("-"))
        if cmd_key in CLI_TO_ENDPOINT:
            endpoint, method = CLI_TO_ENDPOINT[cmd_key]
            api_res = await _call_supervisor_ws_or_http(ctx, endpoint, method=method)
            return json.dumps({
                "command": f"ha {' '.join(args)} (via Supervisor API fallback)",
                "exit_code": 0 if "error" not in api_res else 1,
                "data": api_res,
            }, indent=2)

        return json.dumps({
            "error": f"The 'ha' CLI binary is not available at '{cli_path}' and no direct API fallback exists for '{' '.join(args)}'.",
            "hint": "Ensure the add-on container has the 'ha' binary installed or use call_supervisor_api directly.",
        })

    @mcp_server.tool()
    async def call_supervisor_api(
        ctx: Context,
        endpoint: str,
        method: str = "GET",
        data: dict | None = None,
        skip_confirm: bool = False,
    ) -> str:
        """Call a Home Assistant Supervisor API endpoint directly.

        Useful for querying host, system, core, or add-on details programmatically.
        Examples:
          - endpoint: '/core/info', method: 'GET'
          - endpoint: '/host/info', method: 'GET'
          - endpoint: '/supervisor/info', method: 'GET'
          - endpoint: '/os/info', method: 'GET'
          - endpoint: '/addons', method: 'GET'
          - endpoint: '/resolution/info', method: 'GET'

        Non-GET (mutating) methods trigger a confirmation prompt unless skip_confirm is True.

        Args:
            endpoint: The Supervisor endpoint path (e.g. '/core/info', '/host/info').
            method: HTTP method (GET, POST). Default is GET.
            data: Optional request payload dictionary.
            skip_confirm: If True, bypasses confirmation for non-GET requests.
        """
        if not endpoint or not endpoint.strip():
            return json.dumps({"error": "Endpoint path cannot be empty."})

        clean_endpoint = "/" + endpoint.strip().lstrip("/")
        norm_method = method.strip().upper()

        if norm_method != "GET":
            if not await confirm_change(
                ctx=ctx,
                action=norm_method,
                entity_type="supervisor_api",
                identifier=clean_endpoint,
                config=data or {},
                skip_confirm=skip_confirm,
            ):
                return json.dumps({"status": "cancelled", "message": f"{norm_method} {clean_endpoint} cancelled."})

        result = await _call_supervisor_ws_or_http(ctx, clean_endpoint, method=norm_method, payload=data)
        return json.dumps(result, indent=2)
