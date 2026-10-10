"""Tests for configuration file listing and reading tools."""

import json
from unittest.mock import MagicMock
import pytest

from ha_mcp.config import settings
from ha_mcp.tools.config_files import register_config_file_tools


class _MockMCPServer:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


@pytest.fixture
def mock_config_dir(tmp_path):
    """Create a temporary configuration directory structure."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create dummy files
    (config_dir / "configuration.yaml").write_text("homeassistant:\n  name: Test Home\napi_key: secret_12345\n")
    (config_dir / "automations.yaml").write_text("- alias: Test Automation\n  trigger: []\n")
    (config_dir / "secrets.yaml").write_text("wifi_password: SuperSecretPassword123\n")

    pkg_dir = config_dir / "packages"
    pkg_dir.mkdir()
    (pkg_dir / "lights.yaml").write_text("light:\n  - platform: group\n")

    return config_dir


@pytest.fixture
def config_tools(mock_config_dir, monkeypatch):
    """Register config file tools on a mock MCP server."""
    monkeypatch.setattr(settings, "config_dir", str(mock_config_dir))

    server = _MockMCPServer()
    register_config_file_tools(server)

    ctx = MagicMock()
    return server.tools, ctx


async def test_list_config_files_flat(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["list_config_files"]

    raw = await tool_fn(ctx, subpath="", pattern="*.yaml", recursive=False)
    res = json.loads(raw)

    assert "files" in res
    paths = [f["name"] for f in res["files"]]
    assert "configuration.yaml" in paths
    assert "automations.yaml" in paths
    assert "secrets.yaml" in paths


async def test_list_config_files_recursive(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["list_config_files"]

    raw = await tool_fn(ctx, subpath="", pattern="*.yaml", recursive=True)
    res = json.loads(raw)

    paths = [f["path"] for f in res["files"]]
    assert "packages/lights.yaml" in paths


async def test_list_config_files_path_traversal(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["list_config_files"]

    raw = await tool_fn(ctx, subpath="../")
    res = json.loads(raw)
    assert "error" in res
    assert "Path traversal prohibited" in res["error"]


async def test_get_config_file_success(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["get_config_file"]

    raw = await tool_fn(ctx, path="automations.yaml")
    res = json.loads(raw)

    assert "content" in res
    assert "Test Automation" in res["content"]


async def test_get_config_file_secrets_redaction(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["get_config_file"]

    # Read configuration.yaml with redaction
    raw = await tool_fn(ctx, path="configuration.yaml", redact_secrets=True)
    res = json.loads(raw)

    assert "[REDACTED]" in res["content"]
    assert "secret_12345" not in res["content"]


async def test_get_secrets_file_blocked_by_default(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["get_config_file"]

    raw = await tool_fn(ctx, path="secrets.yaml", allow_secrets_file=False)
    res = json.loads(raw)

    assert "error" in res
    assert "blocked by default" in res["error"]


async def test_get_secrets_file_allowed_explicitly(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["get_config_file"]

    raw = await tool_fn(ctx, path="secrets.yaml", allow_secrets_file=True, redact_secrets=False)
    res = json.loads(raw)

    assert "content" in res
    assert "SuperSecretPassword123" in res["content"]


async def test_get_config_file_path_traversal(config_tools):
    tools, ctx = config_tools
    tool_fn = tools["get_config_file"]

    raw = await tool_fn(ctx, path="../../etc/shadow")
    res = json.loads(raw)

    assert "error" in res
    assert "Path traversal prohibited" in res["error"]
