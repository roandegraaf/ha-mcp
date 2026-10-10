"""Tools for browsing and reading Home Assistant configuration files."""

from datetime import datetime, timezone
import fnmatch
import json
import logging
import os
import re

from fastmcp import Context

from ha_mcp.config import settings

logger = logging.getLogger(__name__)

# Patterns to redact sensitive credentials when redact_secrets is enabled
REDACT_PATTERNS = [
    (re.compile(r"""(?i)(api[_-]?key|password|token|secret|access[_-]?token|auth[_-]?token)\s*[:=]\s*["']?([^"'\s\r\n]+)["']?"""), r"\1: [REDACTED]"),
]


def _is_safe_subpath(base_dir: str, target_path: str) -> bool:
    """Check if target_path is safely contained within base_dir."""
    real_base = os.path.realpath(base_dir)
    real_target = os.path.realpath(target_path)
    return real_target == real_base or real_target.startswith(real_base + os.sep)


def _redact_text(text: str) -> str:
    """Redact passwords and tokens from text content."""
    result = text
    for pattern, repl in REDACT_PATTERNS:
        result = pattern.sub(repl, result)
    return result


def register_config_file_tools(mcp_server):
    """Register configuration file browsing and reading tools."""

    @mcp_server.tool()
    async def list_config_files(
        ctx: Context,
        subpath: str = "",
        pattern: str = "*",
        recursive: bool = False,
    ) -> str:
        """Browse and list files in Home Assistant's configuration directory.

        Lists configuration files (e.g. configuration.yaml, automations.yaml,
        scripts.yaml, packages, templates) located within the Home Assistant
        config directory. Directory traversal outside the config root is blocked.

        Args:
            subpath: Optional relative directory path inside the config directory.
            pattern: Glob pattern to filter files (e.g. '*.yaml', '*'). Default is '*'.
            recursive: Whether to list files recursively within subdirectories.
        """
        config_dir = settings.effective_config_dir
        if not config_dir:
            return json.dumps({
                "error": "Configuration directory is not accessible.",
                "hint": "Ensure the add-on has homeassistant_config mapped or set HA_MCP_CONFIG_DIR.",
            })

        target_dir = os.path.join(config_dir, subpath) if subpath else config_dir
        if not _is_safe_subpath(config_dir, target_dir):
            return json.dumps({"error": "Path traversal prohibited: subpath escapes configuration directory."})

        if not os.path.exists(target_dir):
            return json.dumps({"error": f"Path not found: {subpath or '.'}"})
        if not os.path.isdir(target_dir):
            return json.dumps({"error": f"Path is not a directory: {subpath or '.'}"})

        files_list = []
        try:
            if recursive:
                for root, dirs, files in os.walk(target_dir):
                    # Filter out hidden directories like .storage, .git unless requested
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for item in files:
                        if fnmatch.fnmatch(item, pattern):
                            full_path = os.path.join(root, item)
                            rel_path = os.path.relpath(full_path, config_dir)
                            stat = os.stat(full_path)
                            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                            files_list.append({
                                "name": item,
                                "path": rel_path,
                                "size_bytes": stat.st_size,
                                "modified": mtime,
                                "is_dir": False,
                            })
            else:
                for item in sorted(os.listdir(target_dir)):
                    full_path = os.path.join(target_dir, item)
                    is_dir = os.path.isdir(full_path)
                    if fnmatch.fnmatch(item, pattern) or is_dir:
                        rel_path = os.path.relpath(full_path, config_dir)
                        stat = os.stat(full_path)
                        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                        files_list.append({
                            "name": item,
                            "path": rel_path,
                            "size_bytes": stat.st_size if not is_dir else 0,
                            "modified": mtime,
                            "is_dir": is_dir,
                        })
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"error": f"Failed to list directory: {exc}"})

        return json.dumps({
            "config_dir": config_dir,
            "subpath": subpath or ".",
            "count": len(files_list),
            "files": files_list,
        }, indent=2)

    @mcp_server.tool()
    async def get_config_file(
        ctx: Context,
        path: str,
        redact_secrets: bool = True,
        allow_secrets_file: bool = False,
    ) -> str:
        """Read and return the content of a Home Assistant configuration file.

        Retrieves configuration files such as configuration.yaml, automations.yaml,
        scripts.yaml, packages, or custom template files. Path traversal outside
        the configuration root is strictly prevented.

        Args:
            path: Relative path to the file inside the configuration directory.
            redact_secrets: If True (default), redacts sensitive credentials like
                tokens and passwords from the output.
            allow_secrets_file: If False (default), blocks reading 'secrets.yaml'
                for enhanced security. Must be explicitly set to True to inspect secrets.yaml.
        """
        config_dir = settings.effective_config_dir
        if not config_dir:
            return json.dumps({
                "error": "Configuration directory is not accessible.",
                "hint": "Ensure the add-on has homeassistant_config mapped or set HA_MCP_CONFIG_DIR.",
            })

        if not path:
            return json.dumps({"error": "Path cannot be empty."})

        target_file = os.path.join(config_dir, path)
        if not _is_safe_subpath(config_dir, target_file):
            return json.dumps({"error": "Path traversal prohibited: path escapes configuration directory."})

        norm_rel = os.path.relpath(os.path.realpath(target_file), os.path.realpath(config_dir))
        if os.path.basename(target_file) == "secrets.yaml" and not allow_secrets_file:
            return json.dumps({
                "error": "Access to secrets.yaml is blocked by default for security.",
                "hint": "Set allow_secrets_file=true to view secrets.yaml if explicitly needed.",
            })

        if not os.path.exists(target_file):
            return json.dumps({"error": f"File not found: {norm_rel}"})
        if os.path.isdir(target_file):
            return json.dumps({"error": f"Target is a directory, not a file: {norm_rel}"})

        try:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if redact_secrets:
                content = _redact_text(content)

            return json.dumps({
                "path": norm_rel,
                "size_bytes": len(content),
                "content": content,
            }, indent=2)
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"error": f"Failed to read file: {exc}"})
