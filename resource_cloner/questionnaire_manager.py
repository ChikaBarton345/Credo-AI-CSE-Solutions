from pathlib import Path
from typing import Optional

import requests
from env_manager import EnvManager
from utils import JSONData, JSONDict, JSONList, export_to_json, setup_logger

LOGGER = setup_logger(Path(__file__).stem)


class QuestionnaireManager:
    def __init__(self, env_manager: EnvManager) -> None:
        """Initialize the `QuestionnaireManager` with proper credentials.

        Args:
            env_manager (EnvManager): `EnvManager` object containing critical
                auth and config environment variables.
        """
        self.em = env_manager

        self.src_headers = {
            "Content-type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
            "Authorization": f"Bearer {self.em.src.jwt_token}",
        }
        self.dest_headers = {
            "Content-type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
            "Authorization": f"Bearer {self.em.dest.jwt_token}",
        }

    def _list_qnaires(self) -> JSONData:
        """List all questionnaires available in the source tenant.

        Returns:
            JSONData: JSON response containing questionnaire list.
        """
        url = f"https://api.credo.ai/api/v2/{self.em.src.tenant}/questionnaire_bases"
        LOGGER.info(f"Listing questionnaires for tenant: {self.em.src.tenant}")

        try:
            response = requests.get(url, headers=self.src_headers)
            response.raise_for_status()
            questionnaire_count = len(response.json().get("data", []))
            LOGGER.info(f"Number of questionnaires retrieved: {questionnaire_count}")
            return response.json()
        except requests.RequestException:
            LOGGER.exception("Failed to list questionnaires.")
            return {"data": []}

    def get_qnaire(self) -> JSONData:
        """Retrieve a questionnaire by ID and version (specified in the .env file).

        Returns:
            JSONData: Questionnaire data as a JSON API response.

        Raises:
            `QuestionnaireError`: If retrieval fails.
        """
        url = (
            f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/questionnaires"
            f"/{self.em.src.qid}+{self.em.src.qver}"
        )

        try:
            LOGGER.info(f"Getting questionnaire: {self.em.src.qid}+{self.em.src.qver}")
            response = requests.get(url, headers=self.src_headers)
            response.raise_for_status()
            LOGGER.info(
                f"Successfully retrieved questionnaire:"
                f" {self.em.src.qid}+{self.em.src.qver}"
            )
            return response.json()

        except requests.RequestException:
            LOGGER.exception(
                f"Failed to retrieve questionnaire:"
                f" id={self.em.src.qid} | ver={self.em.src.qver}"
            )
            return {"data": []}

    def _post_qnaire_base(self, questionnaire: JSONData, qb_id: str) -> Optional[str]:
        """Create a questionnaire base and return the questionnaire base ID.

        Args:
            questionnaire (JSONData): Source questionnaire data.
            qb_id (str): ID to assign to the new questionnaire base.

        Returns:
            str: The ID of the created (or existing) questionnaire base.

        Raises:
            `QuestionnaireError`: If creation fails.

        """
        attributes = questionnaire.get("data", {}).get("attributes", {})
        payload = {
            "data": {
                "type": "resource-type",
                "attributes": {
                    "id": qb_id,
                    "name": f"Copy of {attributes.get('name', 'Unnamed')}",
                    "info": attributes.get("info", {}),
                    "metadata": attributes.get("metadata", {}),
                },
            }
        }
        url = (
            f"{self.em.dest.base_path}/api/v2/{self.em.dest.tenant}/questionnaire_bases"
        )
        LOGGER.info(f"Creating questionnaire base: {qb_id}")

        try:
            response = requests.post(url, json=payload, headers=self.dest_headers)
            if response.status_code in (200, 201):
                LOGGER.info(f"Created questionnaire base: {qb_id}")
                return response.json().get("data", {}).get("id", qb_id)

            if response.status_code == 422:
                LOGGER.info(f"Questionnaire base already exists (skipped): {qb_id}")
                return qb_id

            response.raise_for_status()

        except requests.RequestException:
            LOGGER.exception(f"Failed to create questionnaire base: {qb_id}")
            raise

    def _prep_qnaire_payload(self, questionnaire: JSONData) -> JSONData:
        """Build a questionnaire-creation API payload from an existing questionnaire.

        This method preserves all questionnaire metadata.

        Returns:
            JSONData: The questionnaire structure as a JSON-formatted payload.
        """
        attributes = questionnaire.get("data", {}).get("attributes", {})
        sections = attributes.get("sections", [])
        self.current_version = attributes.get("version", 0)
        LOGGER.info(f"Creating questionnaire payload with {len(sections)} section(s).")
        payload = {
            "data": {
                "attributes": {
                    "info": attributes.get("info", {}),
                    "metadata": attributes.get("metadata", {}),
                    "draft": False,
                    "version": self.current_version,
                    "sections": [],
                }
            }
        }
        for i, section in enumerate(sections, 1):
            title = section.get("title", "Untitled")
            LOGGER.debug(f"Section {i}: {title}")
            new_section = {
                "description": section.get("description", ""),
                "title": title,
                "questions": [],
            }

            for j, question in enumerate(section.get("questions", []), 1):
                LOGGER.debug(f"  Question {j}: {question.get('question')}")
                new_question = {
                    "question": question.get("question"),
                    "evidence_type": question.get("evidence_type"),
                    "required": question.get("required"),
                    "hidden": question.get("hidden"),
                    "multiple": question.get("multiple"),
                    "alert_triggers": question.get("alert_triggers"),
                    "description": question.get("description"),
                }
                if "select_options" in question:
                    new_question["select_options"] = question["select_options"]
                    LOGGER.debug(
                        f"Includes {len(question['select_options'])} select option(s)."
                    )
                new_section["questions"].append(new_question)
            payload["data"]["attributes"]["sections"].append(new_section)
        print(f"Questionnaire payload ready ({len(sections)} section(s)).")
        return payload

    def _post_qnaire(self, qb_id: str, payload: JSONData) -> requests.Response:
        """POST a new questionnaire version atop an existing base.

        Args:
            qb_id (str): The ID of the base questionnaire to version.
            payload (JSONData): The JSON-formatted questionnaire data to upload.

        Returns:
            requests.Response: The API response object if successful.
        """

        url = (
            f"{self.em.dest.base_path}/api/v2/{self.em.dest.tenant}"
            f"/questionnaire_bases/{qb_id}/versions"
        )
        LOGGER.info(f"Posting questionnaire version to base: {qb_id}")

        try:
            response = requests.post(url, json=payload, headers=self.dest_headers)
            response.raise_for_status()
            LOGGER.info(f"Successfully posted questionnaire version to base: {qb_id}")
            return response
        except requests.RequestException:
            LOGGER.exception(f"Failed to post questionnaire version to base: {qb_id}")
            raise

    def _post_qnaire_w_ver_retry(self, qb_id: str, payload: JSONData) -> JSONData:
        """Create a new questionnaire version; retry once with +1 to version if needed.

        If the first POST fails due to a version conflict (422), the version is
        incremented and the request is retried once.

        Args:
            qb_id (str): ID of the base questionnaire to post the version to.
            payload (JSONData): Questionnaire data with version, sections, and
                questions.

        Returns:
            JSONData: The response data from the successful POST.

        Raises:
            requests.RequestException: If both attempts fail.
        """
        try:
            response = self._post_qnaire(qb_id, payload)

            if response.status_code in (200, 201):
                qid = response.json().get("data", {}).get("id", "unknown")
                LOGGER.info(
                    f"Created questionnaire version: id={qid},"
                    f" tenant={self.em.dest.tenant}"
                )
                return response.json()

            if response.status_code == 422:
                LOGGER.warning(
                    f"Version conflict at version: {self.current_version}, retrying..."
                )
                new_version = int(self.current_version) + 1
                payload["data"]["attributes"]["version"] = str(new_version)

                retry_response = self._post_qnaire(qb_id, payload)
                if retry_response.status_code in (200, 201):
                    qid = retry_response.json().get("data", {}).get("id", "unknown")
                    LOGGER.info(f"Created questionnaire version after retry: id={qid}")
                    return retry_response.json()

                LOGGER.warning(
                    f"Retry failed for questionnaire {qb_id} at version {new_version}: "
                    f"{retry_response.status_code} - {retry_response.text}"
                )
                retry_response.raise_for_status()

            LOGGER.error(
                f"Unexpected status during questionnaire creation:"
                f" {response.status_code} - {response.text}"
            )
            response.raise_for_status()

        except requests.RequestException:
            LOGGER.exception("Failed to create questionnaire after two attempts.")
            raise

    def _pair_qnaire_sections(self, orig_qst: JSONDict, copy_qst: JSONDict) -> JSONList:
        """Pair each section from the original and copy questionnaires.

        Args:
            orig_qst (Dict[str, Any]): The original questionnaire.
            copy_qst (Dict[str, Any]): The copy questionnaire (of the original).

        Raises:
            `QuestionnaireError`: If there's a failure during the pairing process.

        Returns:
            JSONList: List of dicts pairing original and copy sections, formatted like:
                `{"original": <original_section>, "copy": <copy_section>}`
        """
        orig_sxns = orig_qst.get("data", {}).get("attributes", {}).get("sections", [])
        copy_sxns = copy_qst.get("data", {}).get("attributes", {}).get("sections", [])

        return [
            {"original": orig, "copy": copy} for orig, copy in zip(orig_sxns, copy_sxns)
        ]

    def upload_qnaire_copy(self, questionnaire: JSONData) -> JSONDict:
        """Upload a copy of a questionnaire from the source to the destination tenant.

        Args:
            questionnaire (JSONData): The original questionnaire to copy.

        Returns:
            JSONDict: A dictionary with:
                "old_new_questionnaire_map" (List[JSONDict]):
                    A list of section pairings between the original and copied
                    questionnaire, where each item is a (JSON) dict:
                        {
                            "original": <original_section_dict>,
                            "copy": <copied_section_dict>
                        }
                "new_questionnaire_id" (str):
                    The ID of the newly created questionnaire on the destination tenant.
        """
        qb_id = self._post_qnaire_base(questionnaire, f"{self.em.src.qid}_COPY")
        payload = self._prep_qnaire_payload(questionnaire)
        q_copy = self._post_qnaire_w_ver_retry(qb_id, payload)
        new_id = q_copy.get("data", {}).get("id", "unknown")
        LOGGER.info(f"Successfully uploaded questionnaire copy: id={new_id}")
        q_copy_result = {
            "old_new_questionnaire_map": self._pair_qnaire_sections(
                questionnaire, q_copy
            ),
            "new_questionnaire_id": new_id,
        }
        return q_copy_result


def main():
    """Given its ID and version, download a questionnaire from the source tenant."""
    em = EnvManager()
    qm = QuestionnaireManager(em)
    questionnaire = qm.get_qnaire()
    qattrs = questionnaire.get("data", {}).get("attributes", {})
    qid = qattrs.get("key")
    qver = qattrs.get("version")
    export_to_json(questionnaire, f"src-questionnaire-id-{qid}-ver-{qver}.json")
    q_copy_result = qm.upload_qnaire_copy(questionnaire)
    export_to_json(q_copy_result, "questionnaire-copy-result.json")
    print(1)


if __name__ == "__main__":
    main()
