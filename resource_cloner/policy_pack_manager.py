from pathlib import Path

import requests
from env_manager import EnvManager
from logging_config import setup_logger
from utils import JSONData, export_to_json

LOGGER = setup_logger(Path(__file__).stem)


class PolicyPackManager:
    """GET policy packs from a source tenant or POST to a dest tenant."""

    def __init__(self, env_manager: EnvManager) -> None:
        """Initialize the `CustomFieldsManager` with proper credentials.

        Args:
            env_manager (EnvManager): `EnvManager` object containing critical
                auth and config environment variables.
        """
        self.em = env_manager

    def get_policy_packs(self) -> JSONData:
        """Retrieve policy packs from the source tenant.

        Returns:
            JSONData: JSON response containing policy packs data.
        """
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/policy_packs"
        LOGGER.info(f"Retrieving policy packs from: {self.em.src.tenant}")

        try:
            response = requests.get(url, headers=self.em.src_headers)
            response.raise_for_status()
            data = response.json()
            count = len(data.get("data", []))
            LOGGER.info(f"Number of policy packs retrieved: {count}")
            return data

        except requests.HTTPError:
            LOGGER.exception(f"API error: {response.status_code} - {response.text}")
        except Exception:
            LOGGER.exception("Error retrieving policy packs.")
        LOGGER.warning("Falling back to empty policy packs list.")
        return {"data": []}

    def get_policy_pack_bases(self) -> JSONData:
        """Retrieve policy pack bases (not the packs themselves) from the source tenant.

        Returns:
            JSONData: JSON response containing policy pack bases data.
        """
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/policy_pack_bases"
        LOGGER.info(f"Retrieving policy pack bases from: {self.em.src.tenant}")

        try:
            response = requests.get(url, headers=self.em.src_headers)
            response.raise_for_status()
            data = response.json()
            count = len(data.get("data", []))
            LOGGER.info(f"Number of policy pack bases retrieved: {count}")
            return data

        except requests.HTTPError:
            LOGGER.exception(f"API error: {response.status_code} - {response.text}")
        except Exception:
            LOGGER.exception("Error retrieving policy packs.")
        LOGGER.warning("Falling back to empty policy packs list.")
        return {"data": []}


def main():
    em = EnvManager()
    ppm = PolicyPackManager(em)
    policy_packs = ppm.get_policy_packs()
    export_to_json(policy_packs, "policy_packs.json")
    policy_pack_bases = ppm.get_policy_pack_bases()
    export_to_json(policy_pack_bases, "policy_pack_bases")
    print(1)


if __name__ == "__main__":
    main()
