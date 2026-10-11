"""Tools for browsing and reading Home Assistant configuration files."""

from datetime import datetime, timezone
import fnmatch
import json
import logging
import os
from pathlib import PurePath

from fastmcp import Context

from ha_mcp.config import settings
from ha_mcp.util.redact import redact

logger = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 50_000
MAX_READ_BYTES = 250_000
MAX_ALLOWED_FILE_BYTES = 5_000_000


def _dump(payload) -> str:
    text = json.dumps(payload, indent=2, default=str)
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return json.dumps(
        {
            "truncated": True,
            "note": "Output exceeded size cap; narrow the query.",
            "preview": text[:MAX_OUTPUT_CHARS],
        },
        indent=2,
    )


def _error(message: str, hint: str | None = None) -> str:
    err = {"error": message}
    if hint:
        err["hint"] = hint
    return json.dumps(err)


def _check_denied(real_base: str, real_target: str) -> str | None:
    """Check if the resolved path is denied. Returns an error message if denied, None if allowed."""
    if real_target == real_base:
        return None

    if not real_target.startswith(real_base + os.sep):
        return "Path traversal prohibited: target escapes configuration directory."

    rel_path = os.path.relpath(real_target, real_base)
    parts = PurePath(rel_path).parts

    # Any dot-path or hidden path component
    for part in parts:
        if part.startswith("."):
            return f"Access to hidden or internal path '{part}' is forbidden."

    basename = os.path.basename(real_target)

    # secrets.yaml protection
    if basename == "secrets.yaml" and not settings.allow_secrets_file:
        return (
            "Access to secrets.yaml is disabled for security. "
            "To permit access, enable 'allow_secrets_file' in the add-on configuration."
        )

    # Database file protection (*.db*)
    if fnmatch.fnmatch(basename, "*.db*"):
        return f"Access to database files ('{basename}') is forbidden."

    return None


def register_config_file_tools(registrar):
    """Register configuration file browsing and reading tools."""

    @registrar.tool()
    async def list_config_files(
        ctx: Context,
        subpath: str = "",
        pattern: str = "*",
        recursive: bool = False,
    ) -> str:
        """Browse and list configuration files in the Home Assistant configuration directory.

        Lists configuration files (e.g. configuration.yaml, automations.yaml,
        scripts.yaml, packages, templates) located within the Home Assistant
        config directory. Internal directories (.storage, .cloud), database files,
        and hidden dot-paths are strictly excluded.

        Args:
            subpath: Relative directory path inside the configuration directory (default: root).
            pattern: Glob pattern to filter files (e.g. '*.yaml', '*'). Default is '*'.
            recursive: Whether to list files recursively within subdirectories.
        """
        config_dir = settings.effective_config_dir
        if not config_dir:
            return _error(
                "Configuration directory is not accessible.",
                "Ensure the add-on has homeassistant_config mapped or set HA_MCP_CONFIG_DIR.",
            )

        clean_subpath = subpath.strip().lstrip("/\\")
        target_dir = os.path.join(config_dir, clean_subpath) if clean_subpath else config_dir
        real_base = os.path.realpath(config_dir)
        real_target = os.path.realpath(target_dir)

        denial = _check_denied(real_base, real_target)
        if denial:
            return _error(denial)

        if not os.path.exists(real_target):
            return _error(f"Path not found: {clean_subpath or '.'}")
        if not os.path.isdir(real_target):
            return _error(f"Path is not a directory: {clean_subpath or '.'}")

        files_list = []
        try:
            if recursive:
                for root, dirs, files in os.walk(real_target):
                    # Filter out hidden or denied directories
                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith(".")
                    ]
                    for item in sorted(files):
                        if item.startswith("."):
                            continue
                        if fnmatch.fnmatch(item, "*.db*"):
                            continue
                        if item == "secrets.yaml" and not settings.allow_secrets_file:
                            continue
                        if not fnmatch.fnmatch(item, pattern):
                            continue

                        full_path = os.path.join(root, item)
                        real_file = os.path.realpath(full_path)
                        if _check_denied(real_base, real_file):
                            continue

                        try:
                            stat = os.stat(real_file)
                            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                            size_bytes = stat.st_size
                        except OSError:
                            continue

                        rel_path = os.path.relpath(real_file, real_base)
                        files_list.append({
                            "name": item,
                            "path": rel_path,
                            "size_bytes": size_bytes,
                            "modified": mtime,
                            "is_dir": False,
                        })
            else:
                for item in sorted(os.listdir(real_target)):
                    if item.startswith("."):
                        continue
                    if fnmatch.fnmatch(item, "*.db*"):
                        continue
                    if item == "secrets.yaml" and not settings.allow_secrets_file:
                        continue

                    full_path = os.path.join(real_target, item)
                    real_item = os.path.realpath(full_path)
                    if _check_denied(real_base, real_item):
                        continue

                    try:
                        stat = os.stat(real_item)
                        is_dir = os.path.isdir(real_item)
                        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                        size_bytes = stat.st_size if not is_dir else 0
                    except OSError:
                        continue

                    if is_dir or fnmatch.fnmatch(item, pattern):
                        rel_path = os.path.relpath(real_item, real_base)
                        files_list.append({
                            "name": item,
                            "path": rel_path,
                            "size_bytes": size_bytes,
                            "modified": mtime,
                            "is_dir": is_dir,
                        })
        except Exception as exc:  # noqa: BLE001
            return _error(f"Failed to list directory: {exc}")

        return _dump({
            "config_dir": config_dir,
            "subpath": clean_subpath or ".",
            "count": len(files_list),
            "files": files_list,
        })

    @registrar.tool()
    async def get_config_file(
        ctx: Context,
        path: str,
    ) -> str:
        """Read and return the content of a Home Assistant configuration file.

        Retrieves configuration files such as configuration.yaml, automations.yaml,
        scripts.yaml, packages, or custom template files. Path traversal outside
        the configuration root, internal paths (.storage, .cloud), and database
        files (*.db*) are strictly prevented. Sensitive credentials (passwords, tokens,
        keys) are automatically redacted.

        Args:
            path: Relative path to the file inside the configuration directory.
        """
        config_dir = settings.effective_config_dir
        if not config_dir:
            return _error(
                "Configuration directory is not accessible.",
                "Ensure the add-on has homeassistant_config mapped or set HA_MCP_CONFIG_DIR.",
            )

        clean_path = path.strip().lstrip("/\\")
        if not clean_path:
            return _error("Path cannot be empty.")

        target_file = os.path.join(config_dir, clean_path)
        real_base = os.path.realpath(config_dir)
        real_target = os.path.realpath(target_file)

        denial = _check_denied(real_base, real_target)
        if denial:
            return _error(denial)

        if not os.path.exists(real_target):
            rel = os.path.relpath(real_target, real_base)
            return _error(f"File not found: {rel}")

        if os.path.isdir(real_target):
            rel = os.path.relpath(real_target, real_base)
            return _error(f"Path is a directory, not a file: {rel}")

        try:
            stat = os.stat(real_target)
            if stat.st_size > MAX_ALLOWED_FILE_BYTES:
                rel = os.path.relpath(real_target, real_base)
                return _error(f"File '{rel}' exceeds maximum size limit ({stat.st_size} bytes).")

            with open(real_target, encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_READ_BYTES)
        except Exception as exc:  # noqa: BLE001
            return _error(f"Failed to read file: {exc}")

        rel = os.path.relpath(real_target, real_base)
        redacted_content = redact(content)
        is_truncated = len(redacted_content) > MAX_OUTPUT_CHARS or stat.st_size > MAX_READ_BYTES

        result = {
            "path": rel,
            "content": redacted_content[:MAX_OUTPUT_CHARS],
            "truncated": is_truncated,
        }
        if is_truncated:
            result["total_chars"] = len(redacted_content)
            result["note"] = f"Content truncated to {MAX_OUTPUT_CHARS} characters."

        return json.dumps(result, indent=2)
