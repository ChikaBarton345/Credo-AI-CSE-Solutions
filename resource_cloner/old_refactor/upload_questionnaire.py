import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import dotenv_values, load_dotenv
from download_questionnaire import QuestionnaireDownloader
from get_bearer_token import TokenManager
from resource_cloner.old_refactor.q_manager_utils import QuestionnaireError
from utils import export_to_json

load_dotenv(dotenv_path=".env", override=True)


class QuestionnaireUploader:
    def __init__(self, q_orig: Dict[str, Any]):
        """Initialize an object to upload questionnaires.

        Args:
            q_orig (Dict[str, Any]): The questionnaire data to prepare and then upload.

        Raises:
            `QuestionnaireError`: If something unexpected happens during initialization.
        """
        try:
            token = TokenManager(version="new").get_token()
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.q_orig = q_orig
            self.base_path = env_vars.get("NEW_BASE_PATH")
            self.q_id = env_vars.get("OLD_QUESTIONNAIRE_ID")
            self.q_ver = env_vars.get("OLD_QUESTIONNAIRE_VERSION")
            self.tenant = env_vars.get("NEW_TENANT")
            self.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0

        except Exception as exc:
            print(f"Error during questionnaire initialization: {exc}")
            raise QuestionnaireError(f"Failed to initialize questionnaire: {str(exc)}")

    def _post_questionnaire_base(self, qb_id: str) -> str:
        """Create a questionnaire base and return the questionnaire base ID.

        Args:
            qb_id (str): The unique ID to use for the new questionnaire base.

        Raises:
            `QuestionnaireError`: If base creation fails for unexpected reasons.

        Returns:
            str: The associated questionnaire base ID.
        """
        print(f"Creating questionnaire base: id={qb_id}")
        attributes = self.q_orig.get("data", {}).get("attributes", {})
        payload = {
            "data": {
                "attributes": {
                    "id": qb_id,
                    "name": f"Copy of {attributes.get('name', 'Unnamed')}",
                    "info": attributes.get("info", {}),
                    "metadata": attributes.get("metadata", {}),
                },
                "type": "resource-type",
            }
        }
        url = f"{self.base_path}/api/v2/{self.tenant}/questionnaire_bases"

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            if response.status_code in (200, 201):
                self.success_count += 1
                print(f"Successfully created questionnaire base: {qb_id}")
                return response.json().get("data", {}).get("id", qb_id)

            if response.status_code == 422:
                self.skip_count += 1
                print(
                    f"Skipping questionnaire base creation (already exists): id={qb_id}"
                )
                return qb_id

            response.raise_for_status()  # If unexpected status, raise immediately.

        except Exception as exc:
            details = {
                "questionnaire_id": qb_id,
                "request_url": getattr(response.request, "url", None),
                "response_status": getattr(response, "status_code", None),
                "response_body": getattr(response, "text", None),
            }
            raise QuestionnaireError(
                message=f"Failed to create questionnaire base: {exc}",
                error_type="QuestionnaireError",
                status_code=details["response_status"],
                details=details,
                source="_create_base",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def _prepare_questionnaire_payload(self) -> Dict[str, Any]:
        """Build a questionnaire-creation API payload from an existing questionnaire.

        This method preserves all questionnaire metadata.

        Raises:
            `QuestionnaireError`: If payload preparation fails for unexpected reasons.

        Returns:
            (Dict[str, Any]): The questionnaire structure as a JSON-formatted payload.
        """
        try:
            attributes = self.q_orig.get("data", {}).get("attributes", {})
            sections = attributes.get("sections", [])
            self.current_version = attributes.get("version", 0)
            print(f"Found {len(sections)} section(s) in the original questionnaire.")
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
            num_sections = len(sections)
            for i, section in enumerate(sections, 1):
                title = section.get("title", "Untitled")
                print(f"Section {i}/{num_sections}: {title}")
                new_section = {
                    "description": section.get("description"),
                    "title": title,
                    "questions": [],
                }
                questions = section.get("questions", [])
                num_questions = len(questions)
                for j, question in enumerate(questions, 1):
                    print(f"  Question {j}/{num_questions}:", end="")
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
                        print(f" {len(question['select_options'])} select options")
                    new_section["questions"].append(new_question)
                payload["data"]["attributes"]["sections"].append(new_section)
                print(f"Added section: {title}")
            print(f"Questionnaire payload ready ({num_sections} sections).")
            return payload

        except Exception as exc:
            details = {"questionnaire_id": id}
            raise QuestionnaireError(
                message=f"Error constructing questionnaire: {exc}",
                error_type="QuestionnaireError",
                details=details,
                source="_prepare_payload",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def _post_questionnaire(
        self, qb_id: str, payload: Dict[str, Any]
    ) -> requests.Response:
        """POST a questionnaire version atop a pre-existing base.

        Args:
            qb_id (str): The ID of the base questionnaire to post a new version to.
            payload (Dict[str, Any]): The JSON-formatted questionnaire data.

        Returns:
            requests.Response: The API response object if successful.

        Raises:
            `QuestionnaireError`: If the API request fails.
        """

        url = (
            f"{self.base_path}/api/v2/{self.tenant}"
            f"/questionnaire_bases/{qb_id}/versions"
        )

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as exc:
            error_details = {
                "questionnaire_base_id": qb_id,
                "request_url": getattr(exc.request, "url", None),
                "response_status": getattr(exc.response, "status_code", None),
                "response_body": getattr(exc.response, "text", None),
            }
            raise QuestionnaireError(
                message="Failed to POST questionnaire.",
                error_type="RequestError",
                status_code=getattr(exc.response, "status_code", None),
                details=error_details,
                source="post_questionnaire",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def _post_questionnaire_w_version_retry(
        self, qb_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new questionnaire version with sections and questions.

        Args:
            qb_id (str): The ID of the base questionnaire to post a new version to.
            payload (dict): The questionnaire data containing version, sections and
                questions.

        Returns:
            (Dict[str, Any]): The API response data if creation is successful.

        Raises:
            `QuestionnaireError`: For validation, API, or network errors.
        """
        try:
            response = self._post_questionnaire(qb_id, payload)

            if response.status_code in [200, 201]:
                self.success_count += 1
                q_id = response.json().get("data", {}).get("id", "unknown")
                print(f"Created questionnaire version: id={q_id}, tenant={self.tenant}")
                return response.json()

            if response.status_code == 422:
                print(f"Version conflict at version: {self.current_version}")
                new_version = int(self.current_version) + 1
                payload["data"]["attributes"]["version"] = str(new_version)
                retry = self._post_questionnaire(qb_id, payload)
                if retry.status_code in [200, 201]:
                    self.success_count += 1
                    q_id = retry.json().get("data", {}).get("id", "unknown")
                    print(
                        f"Created questionnaire version: id={q_id} after version bump."
                    )
                    return retry.json()

                self.skip_count += 1
                raise QuestionnaireError(
                    message=(
                        f"Failed to create version {new_version} of {qb_id}:"
                        f"{retry.json()}"
                    ),
                    error_type="QuestionnaireError",
                    status_code=retry.status_code,
                    details=retry.json().get("detail"),
                    source="create_questionnaire",
                    error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
                )
            response.raise_for_status()
            self.error_count += 1
            print(
                "Unexpected status during questionnaire creation:"
                f" {response.status_code}"
            )
            return {}

        except requests.exceptions.RequestException as req_exc:
            raise QuestionnaireError(
                message="Failed to create questionnaire",
                error_type="RequestError",
                status_code=getattr(req_exc.response, "status_code", None),
                details={
                    "questionnaire_id": getattr(self, "q_id", "unknown"),
                    "request_url": getattr(req_exc.request, "url", None),
                    "response_status": getattr(req_exc.response, "status_code", None),
                    "response_body": getattr(req_exc.response, "text", None),
                    "operation": "questionnaire_creation",
                },
                source="create_questionnaire",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

        except ValueError as val_exc:
            raise QuestionnaireError(
                message="Invalid questionnaire data",
                error_type="ValidationError",
                details={
                    "questionnaire_id": getattr(self, "q_id", "unknown"),
                    "error_message": str(val_exc),
                    "operation": "questionnaire_creation",
                },
            )

    def _pair_questionnaire_sections(
        self, orig_qst: Dict[str, Any], copy_qst: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Pair each section from the original and copy questionnaires.

        Args:
            orig_qst (Dict[str, Any]): The original questionnaire.
            copy_qst (Dict[str, Any]): The copy questionnaire (of the original).

        Raises:
            `QuestionnaireError`: If there's a failure during the pairing process.

        Returns:
            (List[Dict[str, Any]]): A list of dicts like:
                `{"original": <original_section>, "copy": <copy_section>}`
        """
        try:
            orig_sections = (
                orig_qst.get("data", {}).get("attributes", {}).get("sections", [])
            )
            copy_sections = (
                copy_qst.get("data", {}).get("attributes", {}).get("sections", [])
            )
            return [
                {"original": orig, "copy": copy}
                for orig, copy in zip(orig_sections, copy_sections)
            ]

        except Exception as exc:
            raise QuestionnaireError(
                message=f"Failed to map questionnaire sections: {exc}",
                error_type="MappingError",
                source="map_questionnaire",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def upload_questionnaire_copy(self) -> Dict[str, Any]:
        """With an original questionnaire from one tenant, upload a copy to another.

        Raises:
            `QuestionnaireError`: If there is an error during upload.

        Returns:
            (Dict[str, Any]): Returns an `old_new_questionnaire_map` to confirm data
                transfer, as well as the questionnaire ID of the newly-created
                questionnaire on the target tenant.
        """
        try:
            payload = self._prepare_questionnaire_payload()
            qb_id = self._post_questionnaire_base(f"{self.q_id}_COPY")
            q_copy = self._post_questionnaire_w_version_retry(qb_id, payload)
            new_id = q_copy.get("data", {}).get("id", "unknown")
            print(f"Successfully uploaded questionnaire copy: id={new_id}")
            q_copy_result = {
                "old_new_questionnaire_map": self._pair_questionnaire_sections(
                    q_copy, self.q_orig
                ),
                "new_questionnaire_id": new_id,
            }
            return q_copy_result
        except Exception as exc:
            raise QuestionnaireError(
                message=f"Failed to upload questionnaire: {exc}",
                error_type="RunError",
                source="run",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )


def main():
    """Download a questionnaire from the source tenant, then upload it to the target."""
    q_orig = QuestionnaireDownloader().get_questionnaire()
    q_uploader = QuestionnaireUploader(q_orig)
    q_copy_result = q_uploader.upload_questionnaire_copy()
    export_to_json(q_copy_result, "questionnaire-copy-result.json")
    print(1)


if __name__ == "__main__":
    main()
