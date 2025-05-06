import requests
from env_manager import EnvManager
from utils import JSONData


class UseCaseManager:
    def __init__(self, env_manager: EnvManager) -> None:
        self.em = env_manager

    def get_use_cases(self) -> JSONData:
        """Get all use cases from the source tenant.

        Returns:
            JSONData: Parsed JSON response from the API.
        """
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/use_cases"
        response = requests.get(url, headers=self.em.src_headers)

        if response.ok:
            return response.json()
        else:
            raise Exception(
                f"Failed to fetch use cases: {response.status_code} - {response.text}"
            )


def main():
    em = EnvManager()
    use_cases = UseCaseManager(em).get_use_cases()
    print(1)


if __name__ == "__main__":
    main()
