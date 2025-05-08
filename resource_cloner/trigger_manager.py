from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from action_manager import ActionManager
from env_manager import EnvManager
from questionnaire_manager import QuestionnaireManager
from utils import JSONData, JSONList, setup_logger

LOGGER = setup_logger(Path(__file__).stem)


class TriggerManager:
    def __init__(self, env_manager: EnvManager, q_copy_result: JSONData):
        self.em = env_manager
        self.q_copy_result = q_copy_result
        self.src_dest_qnaire_map = q_copy_result.get("old_new_questionnaire_map", {})
        self.q_copy_id = q_copy_result.get("new_questionnaire_id")

        self.actions = ActionManager(self)

    def get_triggers(self) -> JSONData:
        """Fetch all triggers from the source tenant.

        Returns:
            JSONData: Parsed JSON response containing the list of triggers.

        Raises:
            requests.RequestException: If the request fails due to an HTTP error.
        """
        LOGGER.info(f"Fetching triggers from: {self.em.src.tenant}")
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/triggers"
        try:
            response = requests.get(url, headers=self.em.src_headers)
            response.raise_for_status()
            json_response = response.json()
            triggers = json_response.get("data", [])
            num_triggers = len(triggers)
            LOGGER.info(f"Triggers retrieved: {num_triggers}")
            return triggers
        except requests.RequestException:
            LOGGER.exception("Failed to retrieve triggers.")
            raise
        except Exception:
            LOGGER.exception("Unexpected error while retrieving triggers.")
            raise

    def _prep_trigger_payload(
        self, trigger: Dict[str, Any], matching_section: Dict[str, Any]
    ) -> JSONData:
        """Format an API payload for a trigger using mapped question and section IDs.

        Args:
            trigger (Dict[str, Any]): Trigger object containing attributes and nested
                data.
            matching_section (Dict[str, Any]): Dict with "new_question_id" and
                "section_id" from the copied questionnaire.

        Returns:
            JSONData: JSON-formatted payload for trigger creation.

        Raises:
            ValueError: If required fields are missing.
        """
        attributes = trigger.get("attributes", {})
        data = attributes.get("data", {})
        options = data.get("options", {})

        trigger_type = attributes.get("type")
        description = attributes.get("description")
        new_question_id = matching_section.get("new_question_id")
        section_id = matching_section.get("section_id")

        # Validate required fields.
        if not self.q_copy_id:
            raise ValueError("Missing questionnaire ID (`self.q_copy_id`).")
        if not description:
            raise ValueError("Missing trigger description.")
        if not new_question_id:
            raise ValueError("Missing `new_question_id` in matching section.")
        if not section_id:
            raise ValueError("Missing `section_id` in matching section.")
        if not trigger_type:
            raise ValueError("Missing trigger type.")

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

    def _map_trigger_to_section(
        self, trigger: JSONData, zipped_sections: JSONList
    ) -> Optional[Dict[str, str]]:
        """Find the copy section and question corresp. to a trigger's orig question ID.

        Args:
            trigger (JSONData): Trigger object containing the original `question_id`.
            zipped_sections (JSONList]): Paired sections from original and copied
                questionnaires.

        Returns:
            (Optional[Dict[str, str]]): A dict with `new_question_id` and `section_id`
                if a match is found, else None.
        """
        trigger_qid = trigger.get("attributes", {}).get("data", {}).get("question_id")
        if not trigger_qid:
            return None

        for pair in zipped_sections:
            orig_questions = pair.get("original", {}).get("questions", [])
            copy_section = pair.get("copy", {})
            copy_questions = copy_section.get("questions", [])
            section_id = copy_section.get("id")

            for orig_q in orig_questions:
                if orig_q.get("id") != trigger_qid:
                    continue
                target_text = orig_q.get("question")
                for copy_q in copy_questions:
                    if copy_q.get("question") == target_text:
                        return {
                            "new_question_id": copy_q.get("id"),
                            "section_id": section_id,
                        }
        return None

    def create_trigger(self, payload: JSONData) -> Optional[str]:
        """Create a trigger in the destination tenant.

        A trigger defines a rule attached to a question (e.g. validations or
        conditional logic). Returns the new trigger ID if created successfully, or None
        if the trigger already exists (HTTP 422).

        Args:
            payload (JSONData): Trigger payload with description, question_id, etc.

        Returns:
            (Optional[str]): ID of the created trigger, or None if skipped.
        """

        attrs = payload.get("data", {}).get("attributes", {})
        trigger_data = attrs.get("data", {})
        description = attrs.get("description")
        question_id = trigger_data.get("question_id")
        questionnaire_id = trigger_data.get("questionnaire_id")
        trigger_id = payload.get("data", {}).get("id")

        LOGGER.info(f"Creating trigger: {description}")
        url = f"{self.em.dest.base_path}/api/v2/{self.em.dest.tenant}/triggers"

        try:
            response = requests.post(url, headers=self.em.dest_headers, json=payload)
            if response.status_code == 201:
                LOGGER.info(f"Created trigger for question: {question_id}")
                return response.json().get("data", {}).get("id")
            if response.status_code == 422:
                self.skip_count += 1
                LOGGER.info(
                    f"Trigger already exists: {trigger_id} in {questionnaire_id}"
                )
                return None

            LOGGER.error(
                f"Unexpected error creating trigger: {response.status_code}"
                f" - {response.text}"
            )
            response.raise_for_status()

        except requests.RequestException:
            LOGGER.exception("Request failed while creating trigger.")
            raise

    def create_triggers(self, triggers: JSONList) -> List[Dict[str, str]]:
        """Create triggers in the destination tenant based on source triggers.

        For each trigger from the source tenant:
          1. Find the matching copied question/section.
          2. Format a trigger payload using updated IDs.
          3. Create the trigger in the destination tenant.
          4. Record a mapping of old to new trigger IDs.

        Args:
            triggers (JSONList): List of trigger objects from the source tenant.

        Returns:
            (List[Dict[str, str]]): List of mappings like:
                {"old_trigger_id": "new_trigger_id"}
        """

        section_map = self.src_dest_qnaire_map
        all_old_triggers = []
        trigger_mapping = []

        LOGGER.info(
            f"Creating triggers in tenant={self.em.dest.tenant}"
            f", copy_id={self.q_copy_id}"
        )

        for trigger in triggers:
            old_trigger_id = trigger.get("id")
            matching_section = self._map_trigger_to_section(trigger, section_map)
            if not matching_section:
                LOGGER.warning(
                    f"Skipped trigger (no matching section): {old_trigger_id}"
                )
                continue

            all_old_triggers.append(old_trigger_id)
            payload = self._prep_trigger_payload(trigger, matching_section)
            new_trigger_id = self.create_trigger(payload)

            trigger_mapping.append(
                {
                    "old_trigger_id": old_trigger_id,
                    "new_trigger_id": new_trigger_id,
                }
            )

        LOGGER.info(f"Created {len(trigger_mapping)} triggers.")
        return trigger_mapping, all_old_triggers


def main():
    """Retrieve all custom fields from the source tenant."""
    em = EnvManager()
    qm = QuestionnaireManager(em)
    qnaire = qm.get_qnaire()
    q_copy_result = qm.upload_qnaire_copy(qnaire)
    tm = TriggerManager(em, q_copy_result)
    triggers = tm.get_triggers()
    trigger_mapping, all_old_triggers = tm.create_triggers(triggers)
    actions = tm.actions.get_actions()
    created_actions = tm.actions.create_actions(
        actions, trigger_mapping, all_old_triggers
    )
    LOGGER.info(
        f"Migration complete: {len(trigger_mapping)} triggers and"
        f" {len(created_actions)} actions created."
    )


if __name__ == "__main__":
    main()
