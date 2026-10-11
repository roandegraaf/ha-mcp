import json
import os
import pytest

from fastmcp import FastMCP
from ha_mcp.config import settings
from ha_mcp.tools import _Registrar, classify_tool, register_all_tools
from ha_mcp.tools.config_files import (
    _check_denied,
    register_config_file_tools,
)


@pytest.fixture
def fake_config_dir(tmp_path, monkeypatch):
    """Create a temporary Home Assistant config directory with various files."""
    config_dir = tmp_path / "ha_config"
    config_dir.mkdir()

    # Standard configuration files
    (config_dir / "configuration.yaml").write_text("homeassistant:\n  name: Test Home\napi_key: supersecret123\n")
    (config_dir / "automations.yaml").write_text("- id: '1'\n  alias: 'Test Auto'\n")

    # Subdirectory with template
    templates_dir = config_dir / "custom_templates"
    templates_dir.mkdir()
    (templates_dir / "test.jinja").write_text("{{ 'hello' }}\n")

    # Sensitive files
    (config_dir / "secrets.yaml").write_text("my_api_key: topsecrettoken\nwifi_password: pass123\n")
    (config_dir / "home-assistant_v2.db").write_text("sqlite database content")
    (config_dir / "home-assistant_v2.db-wal").write_text("sqlite wal content")

    # Hidden / internal storage
    storage_dir = config_dir / ".storage"
    storage_dir.mkdir()
    (storage_dir / "auth").write_text('{"jwt_secret": "abcdef123456", "access_token": "token987"}')
    (storage_dir / "core.config_entries").write_text('{"entries": []}')

    cloud_dir = config_dir / ".cloud"
    cloud_dir.mkdir()
    (cloud_dir / "key").write_text("cloudkey")

    monkeypatch.setattr(settings, "config_dir", str(config_dir))
    monkeypatch.setattr(settings, "enable_config_files", True)
    monkeypatch.setattr(settings, "allow_secrets_file", False)

    return config_dir


def test_classify_config_file_tools():
    """Verify tool naming conventions produce readOnlyHint=True."""
    for tool_name in ("list_config_files", "get_config_file"):
        info = classify_tool(tool_name)
        assert info["readOnlyHint"] is True
        assert info["destructiveHint"] is False


def test_check_denied(fake_config_dir, tmp_path):
    real_base = os.path.realpath(str(fake_config_dir))

    # Allowed
    assert _check_denied(real_base, real_base) is None
    assert _check_denied(real_base, os.path.join(real_base, "configuration.yaml")) is None
    assert _check_denied(real_base, os.path.join(real_base, "custom_templates", "test.jinja")) is None

    # Path traversal outside base
    outside = os.path.realpath(str(tmp_path / "outside.yaml"))
    assert "Path traversal prohibited" in _check_denied(real_base, outside)

    # Dot-paths and internal directories
    assert "hidden or internal path" in _check_denied(real_base, os.path.join(real_base, ".storage", "auth"))
    assert "hidden or internal path" in _check_denied(real_base, os.path.join(real_base, ".cloud", "key"))
    assert "hidden or internal path" in _check_denied(real_base, os.path.join(real_base, ".git", "config"))

    # Database files (*.db*)
    assert "database files" in _check_denied(real_base, os.path.join(real_base, "home-assistant_v2.db"))
    assert "database files" in _check_denied(real_base, os.path.join(real_base, "home-assistant_v2.db-wal"))
    assert "database files" in _check_denied(real_base, os.path.join(real_base, "home-assistant_v2.db.corrupt"))
    assert "database files" in _check_denied(real_base, os.path.join(real_base, "test.db.bak"))

    # secrets.yaml denied by default
    assert "secrets.yaml is disabled" in _check_denied(real_base, os.path.join(real_base, "secrets.yaml"))


def test_check_denied_with_secrets_allowed(fake_config_dir, monkeypatch):
    real_base = os.path.realpath(str(fake_config_dir))
    monkeypatch.setattr(settings, "allow_secrets_file", True)
    assert _check_denied(real_base, os.path.join(real_base, "secrets.yaml")) is None


@pytest.mark.asyncio
async def test_list_config_files(fake_config_dir):
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    tool_names = [t.name for t in await mcp.list_tools()]
    assert "list_config_files" in tool_names

    res = await mcp.call_tool("list_config_files", {"subpath": "", "recursive": False})
    data = json.loads(res.content[0].text)

    names = [f["name"] for f in data["files"]]
    assert "configuration.yaml" in names
    assert "automations.yaml" in names
    assert "custom_templates" in names

    # Denied files/dirs must be absent
    assert ".storage" not in names
    assert ".cloud" not in names
    assert "secrets.yaml" not in names
    assert "home-assistant_v2.db" not in names
    assert "home-assistant_v2.db-wal" not in names


@pytest.mark.asyncio
async def test_list_config_files_recursive(fake_config_dir):
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res = await mcp.call_tool("list_config_files", {"subpath": "", "recursive": True})
    data = json.loads(res.content[0].text)

    paths = [f["path"] for f in data["files"]]
    assert "configuration.yaml" in paths
    assert os.path.join("custom_templates", "test.jinja") in paths

    # Hidden folders should not be traversed
    for p in paths:
        assert not p.startswith(".storage")
        assert not p.startswith(".cloud")
        assert not p.endswith(".db")
        assert not p.endswith(".db-wal")
        assert "secrets.yaml" not in p


@pytest.mark.asyncio
async def test_list_config_files_secrets_enabled(fake_config_dir, monkeypatch):
    monkeypatch.setattr(settings, "allow_secrets_file", True)
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res = await mcp.call_tool("list_config_files", {"subpath": "", "recursive": False})
    data = json.loads(res.content[0].text)
    names = [f["name"] for f in data["files"]]
    assert "secrets.yaml" in names


@pytest.mark.asyncio
async def test_get_config_file_reading_and_redaction(fake_config_dir):
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    # Read configuration.yaml with credentials redacted
    res = await mcp.call_tool("get_config_file", {"path": "configuration.yaml"})
    data = json.loads(res.content[0].text)
    assert data["path"] == "configuration.yaml"
    assert "supersecret123" not in data["content"]
    assert "[REDACTED]" in data["content"]
    assert "Test Home" in data["content"]


@pytest.mark.asyncio
async def test_get_config_file_blocked_paths(fake_config_dir):
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    # Traversal attempt
    res = await mcp.call_tool("get_config_file", {"path": "../outside.yaml"})
    data = json.loads(res.content[0].text)
    assert "error" in data
    assert "Path traversal prohibited" in data["error"]

    # .storage/auth attempt
    res = await mcp.call_tool("get_config_file", {"path": ".storage/auth"})
    data = json.loads(res.content[0].text)
    assert "error" in data
    assert "forbidden" in data["error"]

    # Database file attempt
    res = await mcp.call_tool("get_config_file", {"path": "home-assistant_v2.db"})
    data = json.loads(res.content[0].text)
    assert "error" in data
    assert "forbidden" in data["error"]

    # secrets.yaml attempt when disabled
    res = await mcp.call_tool("get_config_file", {"path": "secrets.yaml"})
    data = json.loads(res.content[0].text)
    assert "error" in data
    assert "secrets.yaml is disabled" in data["error"]


@pytest.mark.asyncio
async def test_get_config_file_secrets_allowed(fake_config_dir, monkeypatch):
    monkeypatch.setattr(settings, "allow_secrets_file", True)
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res = await mcp.call_tool("get_config_file", {"path": "secrets.yaml"})
    data = json.loads(res.content[0].text)
    assert "content" in data
    # Secrets should still be redacted!
    assert "topsecrettoken" not in data["content"]
    assert "pass123" not in data["content"]
    assert "[REDACTED]" in data["content"]


@pytest.mark.asyncio
async def test_leading_slash_paths(fake_config_dir):
    """Verify that leading slashes from LLM tool arguments are safely handled."""
    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res_file = await mcp.call_tool("get_config_file", {"path": "/configuration.yaml"})
    data_file = json.loads(res_file.content[0].text)
    assert data_file["path"] == "configuration.yaml"
    assert "Test Home" in data_file["content"]

    res_dir = await mcp.call_tool("list_config_files", {"subpath": "/custom_templates"})
    data_dir = json.loads(res_dir.content[0].text)
    assert data_dir["subpath"] == "custom_templates"
    assert any(f["name"] == "test.jinja" for f in data_dir["files"])


@pytest.mark.asyncio
async def test_broken_symlink_handling(fake_config_dir):
    """Verify that broken symlinks do not crash directory listings."""
    broken_link = fake_config_dir / "broken.yaml"
    try:
        os.symlink("/nonexistent/target/path.yaml", broken_link)
    except OSError:
        pytest.skip("Symlinks not supported on this platform/filesystem")

    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res = await mcp.call_tool("list_config_files", {"subpath": "", "recursive": False})
    data = json.loads(res.content[0].text)
    assert "error" not in data
    names = [f["name"] for f in data["files"]]
    assert "configuration.yaml" in names


@pytest.mark.asyncio
async def test_advanced_secret_redaction(fake_config_dir):
    """Verify single-quote, spaced passwords, and crypto key redactions."""
    adv_file = fake_config_dir / "advanced.yaml"
    adv_file.write_text(
        "wifi_password: 'pass with spaces'\n"
        "private_key: \"super_crypto_key\"\n"
        "encryption_key: secret123\n"
        "keyboard_layout: us\n"
    )

    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res = await mcp.call_tool("get_config_file", {"path": "advanced.yaml"})
    data = json.loads(res.content[0].text)
    content = data["content"]

    assert "'pass with spaces'" not in content
    assert "'[REDACTED]'" in content
    assert '"super_crypto_key"' not in content
    assert '"[REDACTED]"' in content
    assert "secret123" not in content
    assert "encryption_key: [REDACTED]" in content
    assert "keyboard_layout: us" in content


@pytest.mark.asyncio
async def test_large_file_truncation(fake_config_dir):
    """Verify that files exceeding output cap preserve schema and mark truncated: True."""
    large_file = fake_config_dir / "large.yaml"
    large_file.write_text("x" * 60_000)

    mcp = FastMCP("test")
    registrar = _Registrar(mcp)
    register_config_file_tools(registrar)

    res = await mcp.call_tool("get_config_file", {"path": "large.yaml"})
    data = json.loads(res.content[0].text)
    assert data["path"] == "large.yaml"
    assert data["truncated"] is True
    assert len(data["content"]) == 50_000
    assert data["total_chars"] == 60_000


@pytest.mark.asyncio
async def test_registration_toggle(monkeypatch):
    mcp = FastMCP("test")

    # When disabled
    monkeypatch.setattr(settings, "enable_config_files", False)
    register_all_tools(mcp)
    tool_names = [t.name for t in await mcp.list_tools()]
    assert "list_config_files" not in tool_names
    assert "get_config_file" not in tool_names

    # When enabled
    mcp2 = FastMCP("test2")
    monkeypatch.setattr(settings, "enable_config_files", True)
    register_all_tools(mcp2)
    tool_names2 = [t.name for t in await mcp2.list_tools()]
    assert "list_config_files" in tool_names2
    assert "get_config_file" in tool_names2
