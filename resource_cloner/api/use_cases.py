from pathlib import Path

if __name__ == "__main__":
    import sys
    # Allow for importing from project root when ran directly.
    sys.path.append(str(Path(__file__).resolve().parents[1]))


import requests
from env_manager import EnvManager
from logging_config import setup_logger
from utils import JSONData, export_to_json

LOGGER = setup_logger(Path(__file__).stem)


class UseCases:
    def __init__(self, env_manager: EnvManager) -> None:
        self.em = env_manager

    def get_use_cases(self) -> JSONData:
        """Retrieve use cases from the source tenant.

        Returns:
            JSONData: JSON response containing use cases data.
        """
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/use_cases"
        LOGGER.info(f"Retrieving use cases from: {self.em.src.tenant}")

        try:
            response = requests.get(url, headers=self.em.src_headers)
            response.raise_for_status()
            data = response.json()
            count = len(data.get("data", []))
            LOGGER.info(f"Number of use cases retrieved: {count}")
            return data

        except requests.HTTPError:
            LOGGER.exception(f"API error: {response.status_code} - {response.text}")
        except Exception:
            LOGGER.exception("Error retrieving use cases.")
        LOGGER.warning("Falling back to empty use cases list.")
        return {"data": []}

    def get_use_case_by_id(self, ucid) -> JSONData:
        """Retrieve a use case by ID and version (specified in the .env file).

        Returns:
            JSONData: Use case data as a JSON API response.
        """
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/use_cases/{ucid}"

        try:
            LOGGER.info(f"Getting use case: {ucid}")
            response = requests.get(url, headers=self.em.src_headers)
            response.raise_for_status()
            LOGGER.info(f"Successfully retrieved use case: {ucid}")
            return response.json()

        except requests.RequestException:
            LOGGER.exception(f"Failed to retrieve use case: id={ucid}")
            return {"data": []}


def main():
    em = EnvManager()
    ucm = UseCases(em)
    use_cases = ucm.get_use_cases()
    export_to_json(use_cases, "use_cases.json")
    print(1)


if __name__ == "__main__":
    main()
