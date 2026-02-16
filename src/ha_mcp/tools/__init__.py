"""MCP Tools for Home Assistant configuration management."""

from ha_mcp.tools.registry import register_registry_tools
from ha_mcp.tools.state import register_state_tools
from ha_mcp.tools.automation import register_automation_tools
from ha_mcp.tools.script import register_script_tools
from ha_mcp.tools.scene import register_scene_tools
from ha_mcp.tools.helper import register_helper_tools
from ha_mcp.tools.dashboard import register_dashboard_tools
from ha_mcp.tools.blueprint import register_blueprint_tools
from ha_mcp.tools.config_validation import register_config_validation_tools
from ha_mcp.tools.suggestions import register_suggestion_tools


def register_all_tools(mcp):
    """Register all tool modules with the MCP server."""
    register_registry_tools(mcp)
    register_state_tools(mcp)
    register_automation_tools(mcp)
    register_script_tools(mcp)
    register_scene_tools(mcp)
    register_helper_tools(mcp)
    register_dashboard_tools(mcp)
    register_blueprint_tools(mcp)
    register_config_validation_tools(mcp)
    register_suggestion_tools(mcp)
