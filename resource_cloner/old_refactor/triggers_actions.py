import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import dotenv_values, load_dotenv
from download_questionnaire import QuestionnaireDownloader
from get_bearer_token import TokenManager
from resource_cloner.old_refactor.q_manager_utils import APIError, TriggersActionsError
from upload_questionnaire import QuestionnaireUploader
from utils import JSONData, JSONDict, JSONList

load_dotenv(dotenv_path=".env", override=True)


class TriggersAndActions:
    def __init__(self, q_copy_result):
        self.q_copy_result = q_copy_result
        self.q_copy_id = q_copy_result.get("new_questionnaire_id", {})
        try:
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.q_orig_id = env_vars.get("OLD_QUESTIONNAIRE_ID")
            self.q_orig_ver = env_vars.get("OLD_QUESTIONNAIRE_VERSION")
            self.old_base_path = env_vars.get("OLD_BASE_PATH")
            self.old_tenant = env_vars.get("OLD_TENANT")
            self.new_tenant = env_vars.get("NEW_TENANT")
            old_token = TokenManager(version="old").get_token()
            new_token = TokenManager(version="new").get_token()
            self.old_headers = {"Authorization": f"Bearer {old_token}"}
            self.new_headers = {"Authorization": f"Bearer {new_token}"}
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0

        except Exception as exc:
            print(f"Error during triggers and actions initialization: {exc}")
            raise TriggersActionsError(
                f"Failed to initialize triggers and actions : {str(exc)}"
            )

    def get_triggers(self) -> JSONData:
        """Fetch all triggers from the source tenant.

        Raises:
            `APIError`: If the request fails due to an HTTP error (e.g., 4xx).
            `TriggersActionsError`: For unexpected non-request-related failures during
                execution.

        Returns:
            JSONData: Parsed JSON data containing the list of triggers.
        """
        try:
            print(f"Fetching triggers from: {self.old_tenant}")
            url = f"{self.old_base_path}/api/v2/{self.old_tenant}/triggers"
            response = requests.get(url, headers=self.old_headers)
            response.raise_for_status()
            json_data = response.json().get("data", {})
            num_triggers = sum(1 for i in json_data if i["type"] == "trigger")
            print(f"Triggers retrieved: {num_triggers}")
            return response.json()
        except requests.RequestException as exc:
            raise APIError(
                message=f"Failed to retrieve triggers: {exc}",
                error_type="APIError",
                status_code=getattr(exc.response, "status_code", None),
                details=getattr(exc.response, "json", lambda: {})(),
                source="get_triggers",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )
        except Exception as exc:
            raise TriggersActionsError(
                message=(f"Unexpected error while getting triggers: {exc}")
            )

    def _prepare_trigger_payload(
        self, trigger: Dict[str, Any], matching_section: Dict[str, Any]
    ) -> JSONData:
        """Format an API payload for a trigger using mapped question and section IDs.

        Validates required fields and includes optional data if present. Raises a
            Val`ueError or a `TriggersActionsError` if formatting fails.

        Args:
            trigger: Trigger object containing attributes and nested data.
            matching_section: Dict with the `new_question_id` and associated text for
                the `section_id` from the copied questionnaire.

        Returns:
            JSONData: JSON-formatted payload for trigger creation.
        """
        try:
            attributes = trigger.get("attributes", {})
            description = attributes.get("description")
            trigger_type = attributes.get("type")
            data = attributes.get("data", {})
            options = data.get("options", {})
            new_question_id = matching_section.get("new_question_id")
            section_id = matching_section.get("section_id")
            if not self.q_copy_id:
                raise ValueError("Missing `questionnaire_id`.")
            if not description:
                raise ValueError("Missing trigger `description`.")
            if not new_question_id:
                raise ValueError("Missing `new_question_id` in `matching_section`.")
            if not section_id:
                raise ValueError("Missing `section_id` in `matching_section`.")
            if not trigger_type:
                raise ValueError("Missing trigger `type`.")

            payload = {
                "data": {
                    "attributes": {
                        "type": trigger_type,
                        "description": description,
                        "data": {
                            "questionnaire_id": self.q_copy_id,
                            "question_id": new_question_id,
                            "section_id": section_id,
                        },
                    }
                }
            }

            if options:  # Avoid sending unnecessary keys with empty vals to the API.
                payload["data"]["attributes"]["data"]["options"] = options
            return payload

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Failed to format trigger: {exc}",
                error_type="TriggerFormatError",
                source="_prepare_trigger_payload",
                details={
                    "error_message": str(exc),
                    "trigger": trigger,
                    "matching_section": matching_section,
                },
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def _find_matching_section_for_trigger(
        self, trigger: JSONData, zipped_sections: List[Dict[str, Any]]
    ) -> Optional[Dict[str, str]]:
        """Find the copied section (and question) matching a trigger's the original.

        Args:
            trigger (JSONData): Trigger object containing the original `question_id`.
            zipped_sections (List[Dict[str, Any]]): List of paired sections (original +
                copy) from the questionnaire map.

        Returns:
            (Optional[Dict[str, str]]): A dict with `new_question_id` and `section_id`
                if a match is found, else None.
        """
        try:
            trigger_qid = (
                trigger.get("attributes", {}).get("data", {}).get("question_id")
            )
            if not trigger_qid:
                return None

            for pair in zipped_sections:
                orig_questions = pair.get("original", {}).get("questions", [])
                copy_section = pair.get("copy", {})
                copy_questions = copy_section.get("questions", [])
                section_id = copy_section.get("id")

                for orig_question in orig_questions:
                    if orig_question.get("id") == trigger_qid:
                        target_text = orig_question.get("question")
                        for copy_question in copy_questions:
                            if copy_question.get("question") == target_text:
                                return {
                                    "new_question_id": copy_question.get("id"),
                                    "section_id": section_id,
                                }

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Error while finding matching section for trigger: {exc}",
                error_type="TriggersActionsError",
                source="find_matching_section_for_trigger",
                details={
                    "error_message": str(exc),
                    "trigger": trigger,
                    "zipped_sections": zipped_sections,
                },
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def create_trigger(self, payload: JSONData) -> Optional[str]:
        """Create a new trigger in the target tenant via API using the provided payload.

        A trigger defines a rule attached to a question (e.g. validations or
        conditional logic). Returns the new trigger ID if successful, or `None` if it
        already exists (HTTP 422).

        Args:
            payload (JSONData): Trigger payload including description, question_id,
                questionnaire_id, etc.

        Returns:
            (Optional[str]): The ID of the newly created trigger, or None if skipped or
                failed.
        """

        try:
            description = (
                payload.get("data", {}).get("attributes", {}).get("description")
            )
            question_id = (
                payload.get("data", {})
                .get("attributes", {})
                .get("data", {})
                .get("question_id")
            )
            questionnaire_id = (
                payload.get("data", {})
                .get("attributes", {})
                .get("data", {})
                .get("questionnaire_id")
            )
            trigger_id = payload.get("data", {}).get("id")

            print(f"Creating trigger: {description}")
            url = f"{self.old_base_path}/api/v2/{self.new_tenant}/triggers"
            response = requests.post(url, headers=self.new_headers, json=payload)
            if response.status_code == 201:
                self.success_count += 1
                print(f"Successfully created trigger for question ID: {question_id}")
                return response.json().get("data", {}).get("id")
            if response.status_code == 422:
                self.skip_count += 1
                print(
                    f"Trigger {trigger_id} already exists in questionnaire {questionnaire_id}"
                )
                return None

            # Handle unexpected response
            self.error_count += 1
            raise APIError(
                message="Failed to create trigger",
                error_type="APIError",
                status_code=response.status_code,
                details={
                    "request_url": url,
                    "status_code": response.status_code,
                    "response_text": getattr(response, "text", None),
                    "payload": payload,
                },
                source="create_trigger",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Error while creating trigger: {exc}",
                error_type="TriggersActionsError",
                source="create_trigger",
                details={
                    "error_message": str(exc),
                    "payload": payload,
                },
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def create_triggers(self, triggers: JSONList) -> List[Dict[str, str]]:
        """Create triggers in the target tenant by re-creating them the source tenant.

        For each trigger from the source tenant:
            1. Find the corresponding copied question and section.
            2. Format a trigger payload using updated questionnaire IDs.
            3. Create the trigger in the new tenant.
            4. Record a mapping from the old trigger ID to the new one.

        Args:
            triggers (JSONList): List of trigger objects from the source tenant.

        Returns:
            (List[Dict[str, str]]): List of trigger mappings of the form:
                {"old_trigger_id": "new_trigger_id"}
        """
        try:
            section_map = self.q_copy_result.get("old_new_questionnaire_map", [])
            self.all_old_triggers = []
            trigger_mapping = []

            print(
                f"Creating triggers in: tenant={self.new_tenant},"
                f" copy_id={self.q_copy_id}"
            )

            for trigger in triggers:
                old_trigger_id = trigger.get("id", "")
                matching_section = self._find_matching_section_for_trigger(
                    trigger, section_map
                )
                if not matching_section:
                    continue

                self.all_old_triggers.append(old_trigger_id)
                payload = self._prepare_trigger_payload(trigger, matching_section)
                new_trigger_id = self.create_trigger(payload)

                trigger_mapping.append(
                    {
                        "old_trigger_id": old_trigger_id,
                        "new_trigger_id": new_trigger_id,
                    }
                )

            return trigger_mapping

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Failed to create triggers: {exc}",
                error_type="TriggersActionsError",
                details={"error_message": str(exc)},
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
                source="create_triggers",
            )

    def get_actions(self) -> JSONData:
        """Fetch all trigger actions from the source tenant.

        Trigger actions define the behavior executed when a trigger is activated.

        Returns:
            JSONData: A dictionary containing the trigger actions data.

        Raises:
            `APIError`: If the request fails due to an HTTP error (e.g., 4xx).
            `TriggersActionsError`: For unexpected non-request-related failures during
                execution.
        """
        try:
            print(f"Fetching trigger actions from: {self.old_tenant}")
            url = f"{self.old_base_path}/api/v2/{self.old_tenant}/trigger_actions"
            response = requests.get(url, headers=self.old_headers)
            response.raise_for_status()
            json_data = response.json().get("data", [])
            print(f"Trigger actions retrieved: {len(json_data)}")
            return response.json()
        except requests.RequestException as exc:
            raise APIError(
                message=f"Failed to retrieve trigger actions: {exc}",
                error_type="APIError",
                status_code=getattr(exc.response, "status_code", None),
                details=getattr(exc.response, "json", lambda: {})(),
                source="get_actions",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )
        except Exception as exc:
            raise TriggersActionsError(
                message=f"Unexpected error while getting trigger actions: {exc}"
            )

    def _prepare_action_payload(
        self,
        old_new_trigger_map: Dict[str, str],
        matching_action: Dict[str, Any],
    ) -> JSONData:
        """Format an API payload for an action (associated with a trigger).

        Args:
            old_new_trigger_map (Dict[str, str]): Dict mapping old to new trigger IDs.
            matching_action (Dict[str, Any]): Orig action obj from the source tenant.

        Returns:
            JSONData: JSON-formatted payload for action creation.

        Raises:
            `ValueError`: If there is no `new_trigger_id` to map to.
            `TriggersActionsError`: If action formatting fails.
        """
        try:
            attributes = matching_action.get("attributes", {})
            data = attributes.get("data", {})
            old_question_id = data.get("question_id", "")
            old_section_id = data.get("section_id", "")

            # Map IDs if present.
            if old_question_id:
                data["question_id"] = self._map_questionnaire_id(
                    self.q_copy_result.get("old_new_questionnaire_map", {}),
                    old_question_id,
                )
            if old_section_id:
                data["section_id"] = self._map_questionnaire_id(
                    self.q_copy_result.get("old_new_questionnaire_map", {}),
                    old_section_id,
                )

            # Validate required fields.
            if "new_trigger_id" not in old_new_trigger_map:
                raise ValueError("Missing `new_trigger_id` in trigger mapping.")

            payload = {
                "data": {
                    "attributes": {
                        "type": attributes.get("type", ""),
                        "description": attributes.get("description", ""),
                        "show_visual_alert": attributes.get("show_visual_alert", False),
                        "data": data,
                        "trigger_ids": [old_new_trigger_map["new_trigger_id"]],
                    }
                }
            }

            return payload

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Failed to format action: {exc}",
                error_type="TriggersActionsError",
                source="_prepare_action_payload",
                details={
                    "error_message": str(exc),
                    "matching_action": matching_action,
                    "trigger_map": old_new_trigger_map,
                },
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def _find_matching_actions(self, actions: JSONData) -> List[Tuple[JSONData, str]]:
        """Find actions linked to triggers in `self.all_old_triggers`.

        Iterate through all known actions and identify those associated with a known
        trigger ID. Logs a warning if an action has multiple triggers assigned.

        Args:
            actions (JSONData): JSON-formatted dictionary with a top-level `"data"` key
                holding a list of action objects.

        Returns:
            (List[Tuple[JSONData, str]]): A list of tuples of the form:
                (`action`, `matching_trigger_id`)

        Raises:
            `TriggersActionsError`: If the matching process fails.
        """
        try:
            matches = []

            for action in actions.get("data", []):
                attrs = action.get("attributes", {})
                trigger_ids = attrs.get("trigger_ids", [])

                matching_tids = [
                    tid for tid in trigger_ids if tid in self.all_old_triggers
                ]

                if matching_tids:
                    if len(trigger_ids) > 1:
                        print(f"Multiple triggers found for action: {action.get('id')}")
                    for tid in matching_tids:
                        matches.append((action, tid))

            return matches

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Failed to find matching actions: {exc}",
                error_type="TriggersActionsError",
                source="find_matching_action",
                details={"error_message": str(exc)},
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def create_action(self, action: JSONDict) -> Optional[Dict[str, Any]]:
        """Create a trigger action in the target tenant via API.

        Args:
            action (JSONDict): JSON-formatted payload containing action details.

        Returns:
            (Optional[Dict[str, Any]]): The created action response JSON if successful,
                or None if skipped.

        Raises:
            `TriggersActionsError`: If the request fails or encounters unexpected
                issues.
        """
        try:
            attrs = action.get("data", {}).get("attributes", {})
            trigger_ids = attrs.get("trigger_ids", [])
            action_type = attrs.get("type", "")
            trigger_id = trigger_ids[0] if trigger_ids else "unknown"

            print(f"Creating new action for trigger ID: {trigger_id}")

            url = f"{self.old_base_path}/api/v2/{self.new_tenant}/trigger_actions"
            response = requests.post(url, headers=self.new_headers, json=action)

            if response.status_code == 201:
                print(f"Successfully created action type: {action_type}")
                return response.json()
            if response.status_code == 422:
                self.skip_count += 1
                print("Action already exists. Skipping...")
                return None
            response.raise_for_status()

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Failed to create action: {exc}",
                error_type="TriggersActionsError",
                status_code=getattr(response, "status_code", None),
                details={
                    "error_message": str(exc),
                    "response_text": getattr(response, "text", None),
                    "request_url": getattr(response.request, "url", None),
                    "payload": action,
                },
                source="create_action",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def create_actions(
        self, actions: JSONDict, triggers_mapping: List[Dict[str, str]]
    ) -> JSONList:
        """Create all trigger actions in the target tenant based on trigger ID mappings.

        For each matched action and trigger, format the payload using the new trigger
        ID and post it to the destination tenant's API. Handles multiple trigger
        mappings per action if applicable.

        Args:
            actions (JSONDict): Raw action data from the source tenant ("data" key req).
            triggers_mapping (List[Dict[str, str]])): List of dicts with old -> new
                trigger ID mappings of the form:
                    `[{"old_trigger_id": "abc", "new_trigger_id": "xyz"}, ...]`

        Returns:
            JSONList: A list of successfully created action response objects.

        Raises:
            `TriggersActionsError`: If creation fails for unexpected reasons.
        """
        created = []
        print(f"Creating actions in tenant: {self.new_tenant} (QID: {self.q_copy_id})")
        try:
            matches = self._find_matching_actions(actions)
            if not matches:
                print("No matching actions found.")
                return []

            for action, old_trigger_id in matches:
                matching_pairs = [
                    pair
                    for pair in triggers_mapping
                    if pair["old_trigger_id"] == old_trigger_id
                ]
                if not matching_pairs:
                    print(f"No action found for old trigger ID: {old_trigger_id}")
                    continue

                for pair in matching_pairs:
                    payload = self._prepare_action_payload(pair, action)
                    created_action = self.create_action(payload)
                    if created_action:
                        created.append(created_action)
            return created

        except Exception as exc:
            raise TriggersActionsError(
                message=f"Failed to create actions: {exc}",
                error_type="TriggersActionsError",
                details={"error_message": str(exc)},
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )

    def _map_questionnaire_id(
        self, section_pairs: List[Dict[str, Dict]], id: str
    ) -> str:
        """Map a section or question ID between original and copied questionnaires.

        Args:
            section_pairs (List[Dict[str, Dict]]): List of section pairs, each with
                'original section' and 'copy section'.
            id (str): The ID to map.

        Returns:
            The mapped ID if found, otherwise a blank string.
        """

        id_map = {}

        for pair in section_pairs:
            orig, copy = pair["original"], pair["copy"]
            id_map[orig["id"]] = copy["id"]
            id_map[copy["id"]] = orig["id"]

            for oq, cq in zip(orig.get("questions", []), copy.get("questions", [])):
                id_map[oq["id"]] = cq["id"]
                id_map[cq["id"]] = oq["id"]

        return id_map.get(id, "")


def main():
    """Run the end-to-end trigger and action migration for a copied questionnaire.

    This function orchestrates the following steps:
    1. Downloads a questionnaire from the source tenant.
    2. Uploads a copy of the questionnaire to the target tenant.
    3. Creates triggers in the target tenant based on the original.
    4. Retrieves and recreates associated actions using mapped trigger IDs.
    """
    q_orig = QuestionnaireDownloader().get_questionnaire()
    q_copy_result = QuestionnaireUploader(q_orig).upload_questionnaire_copy()
    tna = TriggersAndActions(q_copy_result)
    triggers = tna.get_triggers().get("data", [])
    trigger_mapping = tna.create_triggers(triggers)
    actions = tna.get_actions()
    created_actions = tna.create_actions(actions, trigger_mapping)
    print(f"Number of triggers created: {tna.success_count}")
    print(f"Number of actions created: {len(created_actions)}")


if __name__ == "__main__":
    sys.exit(main())
