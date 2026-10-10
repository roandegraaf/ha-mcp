"""Tests for ha CLI and Supervisor API tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ha_mcp.tools.ha_cli import register_ha_cli_tools


class _MockMCPServer:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


@pytest.fixture
def cli_tools():
    """Register ha_cli tools on a mock MCP server."""
    server = _MockMCPServer()
    register_ha_cli_tools(server)

    ctx = MagicMock()
    return server.tools, ctx


async def test_run_ha_command_empty(cli_tools):
    tools, ctx = cli_tools
    tool_fn = tools["run_ha_command"]

    raw = await tool_fn(ctx, command="")
    res = json.loads(raw)
    assert "error" in res
    assert "empty" in res["error"]


@patch("os.path.isfile", return_value=True)
@patch("os.access", return_value=True)
@patch("asyncio.create_subprocess_exec")
async def test_run_ha_command_with_binary(mock_subproc, mock_access, mock_isfile, cli_tools):
    tools, ctx = cli_tools
    tool_fn = tools["run_ha_command"]

    # Setup mock subprocess
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b'{"result": "ok"}', b""))
    mock_subproc.return_value = mock_proc

    raw = await tool_fn(ctx, command="ha core check")
    res = json.loads(raw)

    assert res["exit_code"] == 0
    assert res["command"] == "ha core check"
    assert res["data"] == {"result": "ok"}
    mock_subproc.assert_called_once()
    called_args = mock_subproc.call_args[0]
    assert "core" in called_args
    assert "check" in called_args


@patch("ha_mcp.tools.ha_cli.confirm_change", new_callable=AsyncMock)
@patch("os.path.isfile", return_value=True)
@patch("os.access", return_value=True)
async def test_run_ha_command_mutation_cancelled(mock_access, mock_isfile, mock_confirm, cli_tools):
    tools, ctx = cli_tools
    tool_fn = tools["run_ha_command"]

    # Simulate user rejecting the confirmation
    mock_confirm.return_value = False

    raw = await tool_fn(ctx, command="core restart")
    res = json.loads(raw)

    assert res["status"] == "cancelled"
    mock_confirm.assert_called_once()


@patch("ha_mcp.tools.ha_cli._call_supervisor_ws_or_http", new_callable=AsyncMock)
@patch("os.path.isfile", return_value=False)
async def test_run_ha_command_api_fallback(mock_isfile, mock_call_api, cli_tools):
    tools, ctx = cli_tools
    tool_fn = tools["run_ha_command"]

    mock_call_api.return_value = {"version": "2026.10.0"}

    raw = await tool_fn(ctx, command="ha core info")
    res = json.loads(raw)

    assert "fallback" in res["command"]
    assert res["data"] == {"version": "2026.10.0"}
    mock_call_api.assert_called_once_with(ctx, "/core/info", method="GET")


@patch("ha_mcp.tools.ha_cli._call_supervisor_ws_or_http", new_callable=AsyncMock)
async def test_call_supervisor_api_get(mock_call_api, cli_tools):
    tools, ctx = cli_tools
    tool_fn = tools["call_supervisor_api"]

    mock_call_api.return_value = {"supervisor": "healthy"}

    raw = await tool_fn(ctx, endpoint="/supervisor/info", method="GET")
    res = json.loads(raw)

    assert res == {"supervisor": "healthy"}
    mock_call_api.assert_called_once_with(ctx, "/supervisor/info", method="GET", payload=None)
