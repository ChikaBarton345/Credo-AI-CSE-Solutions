from pathlib import Path

import requests
from dotenv import dotenv_values, load_dotenv
from get_bearer_token import TokenManager
from q_manager_utils import QuestionnaireError
from utils import JSONData, export_to_json

load_dotenv(dotenv_path=".env", override=True)


class QuestionnaireDownloader:
    def __init__(self) -> None:
        """Initialize an object to download questionnaires.

        Raises:
            `QuestionnaireError`: If initialization fails.
        """
        try:
            token = TokenManager(version="old").get_token()
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("OLD_BASE_PATH")
            self.tenant = env_vars.get("OLD_TENANT")
            self.q_id = env_vars.get("OLD_QUESTIONNAIRE_ID")
            self.q_ver = env_vars.get("OLD_QUESTIONNAIRE_VERSION")
            self.headers = {
                "Content-type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
                "Authorization": f"Bearer {token}",
            }
        except Exception as exc:
            print(f"Error during questionnaire initialization: {exc}")
            raise QuestionnaireError(f"Failed to initialize questionnaire: {exc}")

    def _list_questionnaires(self) -> JSONData:
        """List all questionnaires available in the source tenant.

        Returns:
            JSONData: JSON response containing questionnaire list.

        Raises:
            `QuestionnaireError`: If the API request fails.
        """
        url = f"https://api.credo.ai/api/v2/{self.tenant}/questionnaire_bases"
        print(f"Listing questionnaires for tenant: {self.tenant}")

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        questionnaire_count = len(response.json().get("data", []))
        print(f"Number of questionnaires retrieved: {questionnaire_count}")
        return response.json()

    def get_questionnaire(self) -> JSONData:
        """Retrieve a questionnaire by ID and version.

        Returns:
            JSONData: The questionnaire data.

        Raises:
            `QuestionnaireError`: If retrieval fails.
        """
        url = (
            f"{self.base_path}/api/v2/{self.tenant}/questionnaires"
            f"/{self.q_id}+{self.q_ver}"
        )

        try:
            print(f"Getting questionnaire: {self.q_id}+{self.q_ver}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            print(f"Successfully retrieved questionnaire: {self.q_id}+{self.q_ver}")
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
    """Given its ID and version, download a questionnaire from the source tenant."""
    q_downloader = QuestionnaireDownloader()
    q_list = q_downloader._list_questionnaires()
    export_to_json(q_list, "src-all-questionnaires.json")
    qstnr = q_downloader.get_questionnaire()
    q_attrs = qstnr.get("data", {}).get("attributes", {})
    q_id = q_attrs.get("key", "unknown")
    q_ver = q_attrs.get("version", "unknown")
    export_to_json(qstnr, f"src-questionnaire-id-{q_id}-ver-{q_ver}.json")
    print(1)


if __name__ == "__main__":
    main()
