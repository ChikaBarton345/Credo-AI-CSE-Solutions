from pathlib import Path
from typing import Literal, Optional

import requests
from dotenv import dotenv_values, load_dotenv, set_key

load_dotenv(dotenv_path=".env", override=True)


class TokenManager:
    def __init__(self, version: Literal["old", "new"]) -> None:
        """Initialize a `TokenManager`.

        Args:
            version (Literal["old", "new"]): Specifies whether to use the old or new
                token version.
        """
        self.version = version
        self.version_prefix = self.version.upper()
        self.load_env_vars()

    def load_env_vars(self) -> None:
        """Load variables from the .env file in the current working dir."""
        env_path = Path.cwd() / ".env"
        self.env_vars = dotenv_values(env_path) if env_path.exists() else {}
        self.api_token = self.env_vars.get(f"{self.version_prefix}_API_TOKEN")
        self.tenant = self.env_vars.get(f"{self.version_prefix}_TENANT")
        self.base_path = self.env_vars.get(f"{self.version_prefix}_BASE_PATH")

    def get_token(self, write_to_file: bool = True) -> Optional[str]:
        """Get an access token from the Credo AI API.

        This method requires an `API_KEY` environment variable to then make a POST
        request to: `https://{BASE_PATH}/auth/exchange`

        Args:
            write_to_file (bool, optional): Whether to automatically write the token
                to the .env file if successful. Defaults to True.

        Returns:
            Optional[str]: The access token if successful, None otherwise.

        Raises:
            `requests.exceptions.RequestException`: For request-related errors
            `ValueError`: If JSON parsing of the response fails.
        """
        url = f"{self.base_path}/auth/exchange"
        data = {"api_token": self.api_token, "tenant": self.tenant}

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            token = response.json().get("access_token")
            if token and write_to_file:
                self.save_token_to_env(token)
            return token
        except (requests.exceptions.RequestException, ValueError) as err:
            print(f"Error obtaining JWT from API token: {err}")

    def save_token_to_env(self, token: str) -> bool:
        """Write or update a JWT token in the .env file in the current working dir.

        This method creates an .env file if it doesn't exist, then stores the token as
        `{VERSION}_JWT_TOKEN` based on the instance version while preserving existing
        env vars.

        Args:
            token (str): JWT token to be stored.

        Returns:
            bool: True if the token was successfully written, False otherwise.
        """
        env_path = Path.cwd() / ".env"
        token_key = f"{self.version_prefix}_JWT_TOKEN"

        try:
            set_key(env_path, token_key, token)
            return True
        except IOError as err:
            print(f"Failed to write to .env file: {err}")
            return False

def main():
    """Get a token for the source tenant, and one for the target tenant."""
    for ver in ["old", "new"]:
        tm = TokenManager(ver)
        tm.get_token()
    print(1)


if __name__ == "__main__":
    main()
