from pathlib import Path
from typing import Literal, Optional, Union

import requests
from dotenv import dotenv_values, load_dotenv, set_key
from utils import setup_logger

logger = setup_logger(Path(__file__).stem)

load_dotenv(dotenv_path=".env", override=True)


class EnvManager:
    def __init__(self, env_path: Union[str, Path] = Path(".env")) -> None:
        """Initialize EnvManager with variables loaded from a .env file.

        Args:
            env_path (Union[str, Path], optional): Path to the ".env" file. Defaults to
                Path(".env") (i.e., the .env file in the current working directory).
        """
        self.env_path = Path(env_path)
        self.load_env_vars()

    def load_env_vars(self) -> None:
        """Load environment variables and group them by source and dest tenants."""
        self.env_vars = dotenv_values(self.env_path) if self.env_path.exists() else {}
        self.src_vars = {
            "api_token": self.env_vars.get("SRC_API_TOKEN"),
            "jwt_token": self.env_vars.get("SRC_JWT_TOKEN"),
            "tenant": self.env_vars.get("SRC_TENANT"),
            "base_path": self.env_vars.get("SRC_BASE_PATH"),
            "qid": self.env_vars.get("SRC_QUESTIONNAIRE_ID"),
            "qver": self.env_vars.get("SRC_QUESTIONNAIRE_VERSION"),
        }
        self.dest_vars = {
            "api_token": self.env_vars.get("DEST_API_TOKEN"),
            "jwt_token": self.env_vars.get("DEST_JWT_TOKEN"),
            "tenant": self.env_vars.get("DEST_TENANT"),
            "base_path": self.env_vars.get("DEST_BASE_PATH"),
        }

    def __repr__(self) -> str:
        """Unambiguous string representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"env_path='{self.env_path}', "
            f"src_tenant='{self.src_vars.get('tenant', '?')}', "
            f"dest_tenant='{self.dest_vars.get('tenant', '?')}')"
        )

    def get_token(
        self, src_or_dest: Literal["src", "dest"], write_to_file: bool = True
    ) -> Optional[str]:
        """Get an access token from the Credo AI API.

        This method requires an `API_KEY` environment variable to then make a POST
        request to: `https://{BASE_PATH}/auth/exchange`

        Args:
            src_or_dest (str): Whether the token is for the source or dest tenant.
            write_to_file (bool, optional): Whether to automatically write the token
                to the .env file if successful. Defaults to True.

        Returns:
            Optional[str]: The access token if successful, None otherwise.

        Raises:
            `requests.exceptions.RequestException`: For request-related errors
            `ValueError`: If JSON parsing of the response fails.
        """
        tenant_vars = self.src_vars if src_or_dest == "src" else self.dest_vars
        url = f"{tenant_vars['base_path']}/auth/exchange"
        data = {"api_token": tenant_vars["api_token"], "tenant": tenant_vars["tenant"]}
        tenant = tenant_vars["tenant"]
        try:
            logger.debug(f"Retrieving JWT token for: {tenant}")
            response = requests.post(url, json=data)
            response.raise_for_status()
            token = response.json().get("access_token")
            if token and write_to_file:
                key = f"{src_or_dest.upper()}_JWT_TOKEN"
                self.save_to_env(key, token)
            logger.info(f"Successfully retrieved token for: {tenant}")
            return token
        except (requests.exceptions.RequestException, ValueError) as exc:
            logger.error(f"Failed to retrieve JWT token: {exc}")
            return None

    def save_to_env(self, key: str, val: Union[str, int]) -> bool:
        """Update a key in the existing .env file.

        Note that .env files are simple key-value files where everything is stored as a
        string.

        Args:
            key: The environment variable key to set.
            val (Union[str, int]): The value to assign (converted to str).

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            if not Path(self.env_path).is_file():
                raise FileNotFoundError(f".env file not found at {self.env_path}")

            set_key(str(self.env_path), key, str(val))
            return True

        except (FileNotFoundError, IOError, OSError) as err:
            logger.error(f"Failed to write to .env: {err}")
            return False


def main():
    """Get a token for the source tenant, and one for the target tenant."""
    env_manager = EnvManager()
    env_manager.get_token("src")
    env_manager.get_token("dest")


if __name__ == "__main__":
    main()
