from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import requests
from utils import JSONData, JSONDict, JSONList, setup_logger

if TYPE_CHECKING:
    from trigger_manager import TriggerManager

LOGGER = setup_logger(Path(__file__).stem)


class ActionManager:
    def __init__(self, trigger_manager: TriggerManager):
        self.tm = trigger_manager  # `trigger_manager` is the parent `TriggerManager`.

    def get_actions(self) -> JSONData:
        """Fetch all trigger actions from the source tenant.

        Trigger actions define what occurs when a trigger is activated.

        Returns:
            JSONData: Parsed JSON containing all trigger actions.

        Raises:
            requests.RequestException: For any HTTP-level failure.
        """
        url = (
            f"{self.tm.em.src.base_path}/api/v2/{self.tm.em.src.tenant}/trigger_actions"
        )
        LOGGER.info(f"Fetching trigger actions from: {self.tm.em.src.tenant}")
        try:
            response = requests.get(url, headers=self.tm.src_headers)
            response.raise_for_status()
            actions = response.json().get("data", [])
            LOGGER.info(f"Number of trigger actions retrieved: {len(actions)}")
            return response.json()
        except requests.RequestException:
            LOGGER.exception("Failed to retrieve trigger actions.")
            raise

    def _prepare_action_payload(
        self,
        old_new_trigger_map: Dict[str, str],
        matching_action: JSONDict,
    ) -> JSONData:
        """Format an API payload for an action (associated with a trigger).

        Args:
            old_new_trigger_map (Dict[str, str]): Dict mapping old to new trigger IDs.
            matching_action (JSONDict): Orig action obj from the source tenant.

        Returns:
            JSONData: JSON-formatted payload for action creation.

        Raises:
            ValueError: If required mapping or fields are missing.
        """
        attrs = matching_action.get("attributes", {})
        data = attrs.get("data", {})

        old_qid = data.get("question_id", "")
        old_sid = data.get("section_id", "")

        # Map IDs if present.
        if old_qid:
            data["question_id"] = self._map_qnaire_id(
                self.tm.q_copy_result.get("old_new_questionnaire_map", {}),
                old_qid,
            )
        if old_sid:
            data["section_id"] = self._map_qnaire_id(
                self.tm.q_copy_result.get("old_new_questionnaire_map", {}),
                old_sid,
            )

        new_trigger_id = old_new_trigger_map.get("new_trigger_id")
        if not new_trigger_id:
            raise ValueError("Missing `new_trigger_id` in trigger mapping.")

        payload = {
            "data": {
                "attributes": {
                    "type": attrs.get("type", ""),
                    "description": attrs.get("description", ""),
                    "show_visual_alert": attrs.get("show_visual_alert", False),
                    "data": data,
                    "trigger_ids": [new_trigger_id],
                }
            }
        }

        return payload

    def _find_matching_actions(
        self, actions: JSONData, all_old_triggers: JSONList
    ) -> List[Tuple[JSONData, str]]:
        """Find actions linked to known trigger IDs.

        Iterate through all known actions and identify those associated with a known
        trigger ID. Logs a warning if an action has multiple triggers assigned.

        Args:
            actions (JSONData): Response containing a list of action objects under
                "data".
            all_old_triggers (JSONList): List of old trigger IDs to match against.

        Returns:
            (List[Tuple[JSONData, str]]): A list of tuples of the form:
                (`action`, `matching_trigger_id`)

        Raises:
            `TriggersActionsError`: If the matching process fails.
        """
        matches = []

        for action in actions.get("data", []):
            trigger_ids = action.get("attributes", {}).get("trigger_ids", [])
            matching_ids = [tid for tid in trigger_ids if tid in all_old_triggers]

            if not matching_ids:
                continue

            if len(trigger_ids) > 1:
                LOGGER.warning(
                    f"Multiple triggers found for action: {action.get('id')}"
                )

            for tid in matching_ids:
                matches.append((action, tid))

        LOGGER.info(f"Number of matched trigger-action pairs: {len(matches)}")
        return matches

    def create_action(self, action: JSONDict) -> Optional[JSONDict]:
        """Create a trigger action in the destination tenant via API.

        Args:
            action (JSONDict): JSON-formatted payload containing action details.

        Returns:
            (Optional[JSONDict]): The JSON response if successful, or None if skipped.

        Raises:
            requests.RequestException: For failed API requests.
        """
        attrs = action.get("data", {}).get("attributes", {})
        trigger_ids = attrs.get("trigger_ids", [])
        action_type = attrs.get("type", "")
        trigger_id = trigger_ids[0] if trigger_ids else "unknown"

        LOGGER.info(
            f"Creating action (type={action_type}) for trigger ID: {trigger_id}"
        )
        url = (
            f"{self.tm.em.dest.base_path}/api/v2"
            f"/{self.tm.em.dest.tenant}/trigger_actions"
        )
        try:
            response = requests.post(url, headers=self.tm.dest_headers, json=action)

            if response.status_code == 201:
                LOGGER.info("Action created successfully.")
                return response.json()

            if response.status_code == 422:
                LOGGER.info("Action already exists (skipping).")
                return None

            LOGGER.error(f"Unexpected status: {response.status_code} - {response.text}")
            response.raise_for_status()

        except requests.RequestException:
            LOGGER.exception("Request failed while creating action.")
            raise

    def create_actions(
        self,
        actions: JSONDict,
        trigger_mapping: List[Dict[str, str]],
        all_old_triggers: List[str],
    ) -> JSONList:
        """Create all trigger actions in the destination tenant.

        Args:
            actions (JSONDict): Raw action data from the source tenant ("data" key req).
            trigger_mapping (List[Dict[str, str]]): List of trigger ID mappings:
                `[{"old_trigger_id": "abc", "new_trigger_id": "xyz"}, ...]`
            all_old_triggers (List[str]): List of all source tenant trigger IDs.

        Returns:
            JSONList: A list of successfully created action response objects.

        Raises:
            requests.RequestException: If any API call fails unexpectedly.
        """
        created = []
        LOGGER.info(
            f"Creating actions in tenant: {self.tm.em.dest.tenant}"
            f" (QID: {self.tm.q_copy_id})"
        )
        matches = self._find_matching_actions(actions, all_old_triggers)
        if not matches:
            LOGGER.info("No matching actions found.")
            return []

        for action, old_trigger_id in matches:
            trigger_matches = [
                pair
                for pair in trigger_mapping
                if pair["old_trigger_id"] == old_trigger_id
            ]
            if not trigger_matches:
                LOGGER.warning(f"No trigger mapping found for: {old_trigger_id}")
                continue

            for pair in trigger_matches:
                payload = self._prepare_action_payload(pair, action)
                created_action = self.create_action(payload)
                if created_action:
                    created.append(created_action)
        LOGGER.info(f"Successfully created {len(created)} actions.")
        return created

    def _map_qnaire_id(
        self, section_pairs: List[Dict[str, Dict]], lookup_id: str
    ) -> str:
        """Look up the corresponding ID between original and copied questionnaires.

        This method builds a bidirectional mapping between section and question IDs
        from the original and copied questionnaires. Given an ID from either side, it
        returns the matching ID from the other.

        Args:
            section_pairs (List[Dict[str, Dict]]): List of paired sections, each a dict
                with "original" and "copy" section objects containing their questions.
            lookup_id (str): A section or question ID to map.

        Returns:
            str: The corresponding mapped ID if found, otherwise an empty string.
        """
        id_map = {}
        for pair in section_pairs:
            orig, copy = pair["original"], pair["copy"]
            id_map[orig.get("id")] = copy.get("id")
            id_map[copy.get("id")] = orig.get("id")

            for oq, cq in zip(orig.get("questions", []), copy.get("questions", [])):
                id_map[oq.get("id")] = cq.get("id")
                id_map[cq.get("id")] = oq.get("id")

        return id_map.get(lookup_id, "")
