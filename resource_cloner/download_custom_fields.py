from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import dotenv_values, load_dotenv
from get_bearer_token import TokenManager
from q_manager_utils import APIError, CustomFieldsError

load_dotenv(dotenv_path=".env", override=True)


class CustomFieldsDownloader:
    """Download custom fields from a source tenant."""

    def __init__(self) -> None:
        """Initialize the downloader with proper credentials.


        Raises:
            `CustomFieldsError`: If initialization fails due to missing credentials
                or token acquisition errors.
        """

        try:
            old_token = TokenManager(version="old").get_token()
            if not old_token:
                raise CustomFieldsError("Failed to obtain source tenant token.")

            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("OLD_BASE_PATH")
            self.tenant_old = env_vars.get("OLD_TENANT")
            self.headers_old = {"Authorization": f"Bearer {old_token}"}

            self.success_count = 0
            self.error_count = 0

        except Exception as exc:
            error_msg = f"Error during custom fields initialization: {exc}"
            print(error_msg)
            raise CustomFieldsError(error_msg)

    def get_custom_fields(self) -> Dict[str, Any]:
        """Retrieve custom fields from the source tenant.

        Returns:
            (Dict[str, Any]): JSON response containing custom fields data.

        Raises:
            `CustomFieldsError`: If retrieval fails, with detailed error information
        """
        api_url = f"{self.base_path}/api/v2/{self.tenant_old}/custom_fields"

        try:
            print(f"Retrieving custom fields from: {self.tenant_old}")
            response = requests.get(api_url, headers=self.headers_old)
            if response.status_code in [200, 201]:
                print(
                    f"✓ Successfully retrieved {len(response.json().get('data', []))}"
                    " Custom Fields"
                )
                return response.json()
            err_msg = f"API error: {response.status_code} - {response.text}"
            print(f"✗ {err_msg}")
            raise APIError(err_msg)
        except Exception as exc:
            print(f"✗ Error retrieving custom fields: {exc}")
            raise CustomFieldsError(f"Failed to retrieve custom fields: {exc}")

    def run(self):
        return self.get_custom_fields()


def main():
    custom_fields = CustomFieldsDownloader().get_custom_fields()


if __name__ == "__main__":
    main()
