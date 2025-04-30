from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import dotenv_values, load_dotenv
from get_bearer_token import TokenManager
from q_manager_utils import APIError, CustomFieldsError
from utils import export_to_json

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
            token = TokenManager(version="old").get_token()
            if not token:
                raise CustomFieldsError("Failed to obtain source tenant token.")

            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("OLD_BASE_PATH")
            self.tenant = env_vars.get("OLD_TENANT")
            self.headers = {"Authorization": f"Bearer {token}"}

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
        url = f"{self.base_path}/api/v2/{self.tenant}/custom_fields"
        print(f"Retrieving custom fields from: {self.tenant}")

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            count = len(data.get("data", []))
            print(f"Number of custom fields retrieved: {count}")
            return data

        except requests.HTTPError as http_err:
            err_msg = f"API error: {response.status_code} - {response.text}: {http_err}"
            print(err_msg)
            raise APIError(err_msg)

        except Exception as exc:
            print(f"Error retrieving custom fields: {exc}")
            raise CustomFieldsError(f"Failed to retrieve custom fields: {exc}")


def main():
    """Retrieve all custom fields from the source tenant."""
    custom_fields = CustomFieldsDownloader().get_custom_fields()
    export_to_json(custom_fields, "src-custom-fields.json")
    print(1)


if __name__ == "__main__":
    main()
