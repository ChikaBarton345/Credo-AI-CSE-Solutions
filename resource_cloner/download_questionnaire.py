from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import dotenv_values, load_dotenv
from get_bearer_token import TokenManager
from q_manager_utils import QuestionnaireError
from utils import export_to_json

load_dotenv(dotenv_path=".env", override=True)


class QuestionnaireDownloader:
    def __init__(self) -> None:
        """Initialize with credentials from environment variables.

        Raises:
            `QuestionnaireError`: If initialization fails
        """
        try:
            self.token = TokenManager(version="old").get_token()
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("OLD_BASE_PATH")
            self.tenant = env_vars.get("OLD_TENANT")
            self.q_id = env_vars.get("OLD_QUESTIONNAIRE_ID")
            self.q_ver = env_vars.get("OLD_QUESTIONNAIRE_VERSION")
            self.headers = {
                "Content-type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
                "Authorization": f"Bearer {self.token}",
            }
            self.list_questionnaires()
        except Exception as exc:
            print(f"Error during questionnaire initialization: {exc}")
            raise QuestionnaireError(f"Failed to initialize questionnaire: {exc}")

    def list_questionnaires(self) -> Dict[str, Any]:
        """List all questionnaires available in the tenant.

        Returns:
            Dict[str, Any]: JSON response containing questionnaire list

        Raises:
            QuestionnaireError: If the API request fails
        """
        url = f"https://api.credo.ai/api/v2/{self.tenant}/questionnaire_bases"
        print(f"Listing questionnaires for tenant: {self.tenant}")

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        questionnaire_count = len(response.json().get("data", []))
        print(f"Successfully retrieved {questionnaire_count} questionnaires")
        return response.json()

    def get_questionnaire(self):
        """Retrieve a questionnaire by ID and version.

        Returns:
            Dict: The questionnaire data.

        Raises:
            `QuestionnaireError`: If retrieval fails.
        """
        url = f"{self.base_path}/api/v2/{self.tenant}/questionnaires/{self.q_id}+{self.q_ver}"

        try:
            print(f"Getting questionnaire: {self.q_id}+{self.q_ver}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            print("Successfully retrieved questionnaire.")
            return response.json()

        except requests.RequestException as exc:
            print(f"Failed to retrieve questionnaire: {exc}")
            raise QuestionnaireError(
                message="Failed to retrieve questionnaire",
                error_type="RetrievalError",
                details={"url": url, "error": str(exc)},
                source="get_questionnaire",
            )


def main():
    questionnaire_manager = QuestionnaireDownloader()
    questionnaire = questionnaire_manager.get_questionnaire()
    export_to_json(questionnaire, "questionnaire.json")
    print(1)


if __name__ == "__main__":
    main()
