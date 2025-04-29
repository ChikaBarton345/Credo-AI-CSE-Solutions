from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import dotenv_values

from .exceptions import ConfigError

class Config:
    """Configuration manager for CS Tool client."""

    def __init__(self, env_path: Optional[str] = None):
        """Initialize configuration from .env file.

        Args:
            env_path: Optional path to .env file. Defaults to current directory.

        Raises:
            ConfigError: If required configuration is missing.
        """
        # Load environment variables
        path = Path(env_path) if env_path else Path.cwd() / ".env"
        self.env_vars = dotenv_values(path) if path.exists() else {}

        # Define required config keys
        self.required_keys = [
            "SRC_API_TOKEN", "SRC_TENANT", "SRC_BASE_PATH",
            "DEST_API_TOKEN", "DEST_TENANT", "DEST_BASE_PATH",
        ]

        # Validate config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that all required configuration is present.

        Raises:
            ConfigError: If required configuration is missing.
        """
        missing_keys = [key for key in self.required_keys if key not in self.env_vars]
        if missing_keys:
            raise ConfigError(f"Missing required configuration: {', '.join(missing_keys)}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key.
            default: Default value if key is not found.

        Returns:
            Configuration value or provided default.
        """
        return self.env_vars.get(key, default)