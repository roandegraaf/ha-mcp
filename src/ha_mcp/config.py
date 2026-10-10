"""Configuration module for the Home Assistant MCP Server."""

import logging
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables with HA_MCP_ prefix."""

    ha_url: str = "http://homeassistant.local:8123"
    ha_token: str = ""
    transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 8099
    skip_confirm_default: bool = False
    log_level: str = "INFO"
    stateless_http: bool = True
    enable_config_files: bool = False
    enable_ha_cli: bool = False
    config_dir: str = "/homeassistant"
    ha_cli_path: str = "/usr/bin/ha"
    supervisor_url: str = "http://supervisor"

    model_config = SettingsConfigDict(env_prefix="HA_MCP_")

    @field_validator("ha_token")
    @classmethod
    def warn_if_empty_token(cls, v: str) -> str:
        if not v:
            logger.warning(
                "ha_token is empty. Set HA_MCP_HA_TOKEN to a long-lived access token."
            )
        return v

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        allowed = {"stdio", "http", "sse"}
        if v not in allowed:
            raise ValueError(
                f"Invalid transport '{v}'. Must be one of: {', '.join(sorted(allowed))}"
            )
        return v

    @property
    def ha_base_url(self) -> str:
        """Return ha_url with any trailing slash removed."""
        return self.ha_url.rstrip("/")

    @property
    def ha_websocket_url(self) -> str:
        """Convert ha_url to a WebSocket URL and append /api/websocket."""
        parsed = urlparse(self.ha_base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return f"{scheme}://{parsed.netloc}{parsed.path}/api/websocket"

    @property
    def effective_config_dir(self) -> str | None:
        """Resolve the effective configuration directory.

        Checks explicit config_dir, then fallback paths (/homeassistant, /config).
        Returns None if no directory exists.
        """
        import os

        candidates = [self.config_dir, "/homeassistant", "/config"]
        for path in candidates:
            if path and os.path.isdir(path):
                return os.path.realpath(path)
        return None


settings = Settings()
