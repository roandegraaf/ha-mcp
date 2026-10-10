"""Tests for GUI configuration toggle options (on/off by default)."""

from ha_mcp.config import Settings
from ha_mcp.tools import register_all_tools


class _MockMCPServer:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def test_tools_off_by_default(monkeypatch):
    """By default, enable_config_files and enable_ha_cli are False, so those tools are not registered."""
    test_settings = Settings(enable_config_files=False, enable_ha_cli=False)
    monkeypatch.setattr("ha_mcp.tools.settings", test_settings)

    server = _MockMCPServer()
    register_all_tools(server)

    registered_tools = set(server.tools.keys())

    # Standard tools should be present
    assert "get_config" in registered_tools
    assert "list_entities" in registered_tools

    # Config files tools should NOT be registered
    assert "list_config_files" not in registered_tools
    assert "get_config_file" not in registered_tools

    # HA CLI tools should NOT be registered
    assert "run_ha_command" not in registered_tools
    assert "call_supervisor_api" not in registered_tools


def test_tools_registered_when_enabled(monkeypatch):
    """When enable_config_files and enable_ha_cli are True, the tools are registered."""
    test_settings = Settings(enable_config_files=True, enable_ha_cli=True)
    monkeypatch.setattr("ha_mcp.tools.settings", test_settings)

    server = _MockMCPServer()
    register_all_tools(server)

    registered_tools = set(server.tools.keys())

    # Config files tools should be registered
    assert "list_config_files" in registered_tools
    assert "get_config_file" in registered_tools

    # HA CLI tools should be registered
    assert "run_ha_command" in registered_tools
    assert "call_supervisor_api" in registered_tools
