import requests
import json
from typing import Dict, List, Optional, Union
import os
import sys
from download_questionnaire import Questionnaire as Questionnaire_download
from upload_questionnaire import Questionnaire as Questionnaire_upload
from get_bearer_token import TokenManager
from q_manager_utils import TriggersActionsError, APIError
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)

class TriggersAndActions:
    def __init__(self):
        try:
            self.questionnaire_id = os.getenv("OLD_QUESTIONNAIRE_ID")
            self.questionnaire_version = os.getenv("OLD_QUESTIONNAIRE_VERSION")            
            old_token_manager = TokenManager(version = "old")
            old_token = old_token_manager.run()
            new_token_manager = TokenManager(version = "new")
            new_token = new_token_manager.run()
            self.old_headers = {"Authorization": f"Bearer {old_token}"}
            self.new_headers = {"Authorization": f"Bearer {new_token}"}
            self.base_path = os.getenv("OLD_BASE_PATH")
            self.old_tenant = os.getenv("OLD_TENANT")
            self.new_tenant = os.getenv("NEW_TENANT")
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0
        except Exception as e:
            print(f"Error during triggers and actions initialization: {e}")
            raise TriggersActionsError(f"Failed to initialize triggers and actions : {str(e)}")
        
    def get_triggers(self):
        try:
            print(f"\n=== Getting triggers from tenant: {self.old_tenant} ===")
            response = requests.get(f"{self.base_path}/api/v2/{self.old_tenant}/triggers", headers=self.old_headers)
            if response.status_code in [200, 201]:
                print(f"✓ Successfully retrieved triggers from tenant {self.old_tenant}\n")
                response.raise_for_status()
                return response.json()
            else:
                raise APIError(
                    message=f"Failed to retrieve triggers: {response.json()}",
                    error_type="APIError",
                    status_code=response.status_code,
                    details=response.json(),
                    source="get_triggers",
                    error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
                )
        except Exception as e:
            raise TriggersActionsError(
                message=f"Unexpected error while getting triggers from Credo AI API: {str(e)}"
            )
    
    def format_trigger(self, trigger, matching_section):
        """
        Formats a trigger payload for API request by extracting and validating required fields from the input trigger and matching section.
        Maps questionnaire IDs, descriptions, question IDs, section IDs, options and trigger types to the expected payload structure.
        Raises ValueError if required fields are missing.

        Args:
            trigger: Original trigger object containing attributes and data
            matching_section: Section object containing mapped IDs for the new questionnaire

        Returns:
            Dictionary containing formatted trigger payload for API request
        """
        try:
            trigger_payload = {
                "data": {
                    "attributes": {
                        "data": {}
                    }
                }
            }
            if self.new_questionnaire_id:
                trigger_payload["data"]["attributes"]["data"]["questionnaire_id"] = self.new_questionnaire_id
            else:
                raise ValueError(f"No value found for questionnaire_id while formatting trigger: {trigger}")
            if trigger.get("attributes", {}).get("description", {}):
                description = trigger.get("attributes", {}).get("description", {})
                trigger_payload["data"]["attributes"]["description"] = description
            else:
                raise ValueError(f"No value found for description while formatting trigger with description: {description}")
            if matching_section.get('new_question_id', {}):
                trigger_payload["data"]["attributes"]["data"]["question_id"] = matching_section.get('new_question_id', {})        
            else:
                raise ValueError(f"No value found for question_id while formatting trigger with question_id: {matching_section.get('new_question_id', {})}")
            if matching_section.get('section_id', {}):
                trigger_payload["data"]["attributes"]["data"]["section_id"] = matching_section.get('section_id', {})
            else:
                raise ValueError(f"No value found for section_id while formatting trigger with description: {description}")
            if trigger.get("attributes").get("data").get("options"):
                options = trigger.get("attributes", {}).get("data", {}).get("options", {})
                trigger_payload["data"]["attributes"]["data"]["options"] = options
            else:
                print(f"No value found for options while formatting trigger")
            if trigger.get("attributes", {}).get("type", {}):
                trigger_payload["data"]["attributes"]["type"] = trigger.get("attributes", {}).get("type", {})
            else:
                raise ValueError(f"No value found for type while formatting trigger with description: {description}")
            return trigger_payload
        except Exception as e:
            details = {
                "error_message": str(e), 
                'trigger': trigger,
                'matching_section': matching_section
            }
            raise TriggersActionsError(
                message=f"Failed to format trigger: {str(e)}",
                error_type="TriggerFormatError",
                details=details,
                error_line=sys.exc_info()[2].tb_lineno,
                source="format_trigger"
            )

    def find_matching_section_for_trigger(self, trigger, zipped_sections):
        """
        Finds the matching section and question mapping between original and copied questionnaires.

        Given a trigger and zipped_sections (pairs of original and copied sections), this method:
        1. Extracts the question_id from the trigger
        2. Searches through original section questions to find a matching question_id
        3. When found, gets the corresponding copied section ID
        4. Finds the matching copied question by comparing question text
        5. Returns a dict with the new question ID and section ID mapping

        Args:
            trigger (dict): The trigger object containing question_id to match
            zipped_sections (list): List of section pairs containing original and copied sections

        Returns:
            dict: Contains 'new_question_id' and 'section_id' for the matching question/section
            or None if no match is found
        """
        try:
            
            trigger_question_id = trigger.get("attributes", {}).get("data", {}).get("question_id")
          
            if trigger_question_id:
                match = {}                
                for section_pair in zipped_sections:
                    original_section_questions = section_pair.get("original section", {}).get("questions")
                    for question in original_section_questions:
                        if question.get("id") == trigger_question_id:
                            section_id = section_pair.get("copy section", {}).get("id")
                            question = question.get("question")
                            copy_section_questions = section_pair.get("copy section", {}).get("questions", [])
                            for copy_question in copy_section_questions:
                                if copy_question.get("question") == question:
                                    new_question_id = copy_question.get("id")
                                    break
                            match = {"new_question_id": new_question_id, "section_id": section_id}
                            
                return match
        except Exception as e:
            details = {
                "error_message": str(e),
                "trigger": trigger,
                "zipped_sections": zipped_sections
            }
            raise TriggersActionsError(
                message=f"Unexpected error while finding matching section for trigger: {str(e)}",
                error_type="TriggersActionsError",
                source="find_matching_section_for_trigger",
                details=details,
                error_line=sys.exc_info()[2].tb_lineno
            )

    def create_trigger(self, payload):
        """
        Creates a new trigger in the new tenant using the provided payload. A trigger is a rule that can be 
        attached to a question to enforce certain conditions or validations. The trigger will be created via 
        an API call to the new tenant's endpoint.

        Args:
            payload (dict): The trigger payload containing the trigger configuration including:
                - description: Text description of what the trigger does
                - data: Dictionary containing trigger specific data like:
                    - question_id: ID of the question this trigger is attached to
                    - questionnaire_id: ID of the questionnaire containing the question
                    - conditions: List of conditions that activate the trigger
                    - actions: List of actions to take when conditions are met

        Returns:
            str: The ID of the newly created trigger if successful
            None: If trigger already exists (HTTP 422) or creation fails
        """
        try:    
            print(f"Creating trigger with description: {payload.get('data', {}).get('attributes', {}).get('description', {})}")    
            response = requests.post(f"{self.base_path}/api/v2/{self.new_tenant}/triggers", headers=self.new_headers, json=payload)
            if response.status_code == 201:
                self.success_count += 1
                print(f"✓ Sucessfully added trigger to quesiton id: {payload.get('data', {}).get('attributes', {}).get('data', {}).get('question_id', {})}\n")
                return response.json().get('data', {}).get('id', {})
            elif response.status_code == 422:
                self.skip_count += 1
                print(f"Trigger {payload.get('data', {}).get('id', {})} already exists in questionnaire id: {payload.get('data', {}).get('attributes', {}).get('data', {}).get('questionnaire_id', {})}")
            else:
                self.error_count += 1
                details = {
                    "request url": response.request.url if response.request else None,
                    "status_code": response.status_code if 'response' in locals() else None,
                    "response_text": response.text if 'response' in locals() and hasattr(response, 'text') else None,
                    "request payload": payload
                }
                raise APIError(
                    message=f"Failed to create trigger: {response.json()}",
                    error_type="APIError",
                    status_code=response.status_code,
                    details=details,
                    source="create_trigger",
                    error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
                )
            
        except Exception as e:
            
            raise TriggersActionsError(message=f"TriggersActionsError while creating trigger: {str(e)}")
    
    def create_triggers(self):
        """
        Creates triggers in the new tenant by mapping existing triggers from the old tenant.

        This method:
        1. Retrieves all triggers from the old tenant
        2. Finds matching sections and question mappings between original and copied questionnaires
        3. Formats trigger payloads for the new tenant
        4. Creates triggers in the new tenant
        
        Returns:
            list: List of trigger mappings (old_trigger_id to new_trigger_id)
        """
        try:
            
            triggers_response = self.get_triggers()
            self.all_old_triggers = []
            created_triggers = []
            trigger_mapping = []
            print(f"== Creating triggers in {self.new_tenant} questionnaire id: {self.new_questionnaire_id}==\n")
            for trigger in triggers_response.get('data', []):
                matching_section = self.find_matching_section_for_trigger(trigger, self.questionnaires.get('old_new_questionnaire_map', {}))
                
                if matching_section:
                    old_trigger_id = trigger.get("id")
                    self.all_old_triggers.append(old_trigger_id)
                    formatted_trigger_payload = self.format_trigger(trigger, matching_section)
                    new_trigger_id = self.create_trigger(formatted_trigger_payload)
                    old_new_trigger_map={"old_trigger_id": old_trigger_id, "new_trigger_id": new_trigger_id}
                    trigger_mapping.append(old_new_trigger_map)
                   
            return trigger_mapping
        except Exception as e:
            raise TriggersActionsError(
                message=f"Failed to create triggers: {str(e)}",
                error_type="TriggersActionsError",
                details={
                    "error_message": str(e)
                },
                error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None,
                source="create_triggers"
            )
   
    def get_actions(self):
       """
       Retrieves all trigger actions from the old tenant via API call.
       
       This method makes a GET request to fetch all trigger actions associated with
       the old tenant. Trigger actions define what happens when a trigger condition
       is met, such as showing alerts or requiring additional evidence.
       
       Returns:
           dict: JSON response containing the trigger actions data
           
       Raises:
           APIError: If the API request fails
           TriggersActionsError: If there is an unexpected error during execution
       """
       try:
           print(f"\n=== Getting actions from tenant: {self.old_tenant} ===")
           response = requests.get(f"{self.base_path}/api/v2/{self.old_tenant}/trigger_actions", headers=self.old_headers)
           if response.status_code in [200, 201]:
               print(f"✓ Successfully retrieved actions from tenant {self.old_tenant}\n")
               return response.json()
           else:
               response.raise_for_status()
       except Exception as e:
           details = {
               "request url": response.request.url if response.request else None,
               "status_code": response.status_code if 'response' in locals() else None,
               "response_text": response.text if 'response' in locals() and hasattr(response, 'text') else None,
               "request payload": None,
               "error_message": str(e)
           }
           raise TriggersActionsError(
                   message=f"Failed to get actions: {response.json()}",
                   error_type="APIError",
                   status_code=response.status_code,
                   details=details,
                   source="get_actions",
                   error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
               )
    
    def format_action(self, old_new_trigger_map, matching_action):
        """
        Formats a trigger action for the new tenant by updating IDs and structuring the payload.
        
        This method takes a trigger mapping (old to new IDs) and an action from the old tenant,
        updates any questionnaire-related IDs using the mapping, and formats it into the 
        required payload structure for creating an action in the new tenant.
        
        Args:
            old_new_trigger_map (dict): Mapping between old and new trigger IDs
            matching_action (dict): The action data from the old tenant to be formatted
            
        Returns:
            dict: Formatted action payload ready to be sent to the API
            
        Raises:
            TriggersActionsError: If there is an error during action formatting
        """
        try:
            
            if matching_action.get("attributes", {}).get("data", {}).get("question_id"):
                matching_action["attributes"]["data"]["question_id"] = self.map_questionnaire_id(self.questionnaires.get('old_new_questionnaire_map', {}), matching_action.get("attributes", {}).get("data", {}).get("question_id"))
                matching_action["attributes"]["data"]["section_id"] = self.map_questionnaire_id(self.questionnaires.get('old_new_questionnaire_map', {}), matching_action.get("attributes", {}).get("data", {}).get("section_id"))
            action_payload = {
                "data": {
                    "attributes": {
                        "data": matching_action.get("attributes", {}).get("data", {}),
                        "description": matching_action.get("attributes", {}).get("description", {}),
                        "show_visual_alert":matching_action.get("attributes", {}).get("show_visual_alert", {}),
                        "trigger_ids": [old_new_trigger_map.get("new_trigger_id")],
                        "type": matching_action.get("attributes", {}).get("type", {})
                    }
                }
                }
            return action_payload
        except Exception as e:
            raise TriggersActionsError(
                message=f"Failed to format action: {str(e)}",
                error_type="TriggersActionsError",
                details={
                    "error_message": str(e)
                },
                error_line=sys.exc_info()[2].tb_lineno,
                source="format_action"
            )
    
    def find_matching_action(self):
        """
        Finds actions that match triggers in self.all_old_triggers.
        
        Iterates through all actions and identifies those associated with triggers 
        in self.all_old_triggers. For each matching action, creates a tuple of 
        (action, matching_trigger_id) and adds it to the results. Logs a warning 
        if an action has multiple triggers.
        
        Returns:
            list or None: List of (action, trigger_id) tuples for matching actions,
                         or None if no matches found
                         
        Raises:
            TriggersActionsError: If there is an error during the matching process
        """
        try:
            matching_actions = []
            for action in self.actions["data"]:                
                matching_trigger_ids = [trigger_id for trigger_id in action.get('attributes', {}).get('trigger_ids', {}) 
                                     if trigger_id in self.all_old_triggers]
                if matching_trigger_ids:
                    if len(action.get('attributes', {}).get('trigger_ids', {})) > 1:
                        print(f"Action {action.get('id')} has multiple triggers, check this one!")
                    for matching_trigger_id in matching_trigger_ids:
                        matching_actions.append((action, matching_trigger_id))
            return matching_actions if matching_actions else None
        except Exception as e:
            raise TriggersActionsError(
                message=f"Failed to find matching action: {str(e)}",
                error_type="TriggersActionsError",
                details={
                    "error_message": str(e)
                },
                error_line=sys.exc_info()[2].tb_lineno,
                source="find_matching_action"
            )
    
    def create_action(self, action):
        """
        Creates a new trigger action in the system.
        
        Takes a formatted action payload and sends a POST request to create the action
        in the new tenant. The action is associated with a specific trigger ID.
        
        Args:
            action (dict): The formatted action payload containing the action details
                          and trigger ID mapping
        
        Returns:
            dict: The created action response from the API if successful
            
        Raises:
            TriggersActionsError: If there is an error creating the action,
                                 with detailed error information
        """
        try:
            print(f"Creating new action for trigger id: {action.get('data', {}).get('attributes', {}).get('trigger_ids', {})[0]}")
            response = requests.post(f"{self.base_path}/api/v2/{self.new_tenant}/trigger_actions", headers=self.new_headers, json=action)
            if response.status_code == 201:
                print(f"✓ Sucessfully added action type {action.get('data', {}).get('attributes', {}).get('type', {})} to trigger id: {action.get('data', {}).get('attributes', {}).get('trigger_ids', {})[0]}\n")
                return response.json()
            else:
                response.raise_for_status()
        except Exception as e:
            details = {
                "request url": response.request.url if response.request else None,
                "status_code": response.status_code if 'response' in locals() else None,
                "response_text": response.text if 'response' in locals() and hasattr(response, 'text') else None,
                "request payload": action
            }
            raise TriggersActionsError(
                    message=f"Failed to create action: {response.json()}",
                    error_type=TriggersActionsError,
                    status_code=response.status_code,
                    details=details,
                    source="create_action",
                    error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
                )
    
    def create_actions(self, triggers_mapping):
        """
        Creates multiple trigger actions based on a mapping of old to new trigger IDs.
        
        Iterates through existing actions in the old tenant, finds matching actions and triggers,
        formats the action payloads with new trigger IDs, and creates the actions in the new tenant.
        
        Args:
            triggers_mapping (list): List of dictionaries mapping old trigger IDs to new trigger IDs
                                   in the format [{"old_trigger_id": "123", "new_trigger_id": "456"}, ...]
        
        Returns:
            list: The created action responses from the API if successful
            
        Raises:
            TriggersActionsError: If there is an error creating the actions,
                                 with detailed error information
        """
        try:
            created_actions = []
            self.actions = self.get_actions()
            print(f"\n=== Creating actions in {self.new_tenant}questionnaires: {self.new_questionnaire_id} === \n")
            
            matching_actions = self.find_matching_action()
            if matching_actions:
                for matching_action, matching_trigger_id in matching_actions:
                    old_new_trigger_map = next((trigger_map for trigger_map in triggers_mapping 
                                              if trigger_map["old_trigger_id"] == matching_trigger_id), None)
                    if old_new_trigger_map:
                        formatted_action_payload = self.format_action(old_new_trigger_map, matching_action.copy())
                        created_action = self.create_action(formatted_action_payload)
                        created_actions.append(created_action)
            return created_actions
        except Exception as e:
            raise TriggersActionsError(
                message=f"Failed to create actions: {str(e)}",
                error_type="TriggersActionsError",
                details={
                    "error_message": str(e)
                },
                error_line=sys.exc_info()[2].tb_lineno,
                source="create_actions"
            )
    
    def map_questionnaire_id(self, section_pairs, id_):
        """
        Maps IDs between original and copied questionnaire sections/questions.
        
        Takes a list of section pairs (original and copy) and an ID to look up.
        Creates mappings between old and new IDs for both sections and questions.
        Returns the corresponding mapped ID if found in any of the mappings.

        Args:
            section_pairs (list): List of dictionaries containing original and copied section pairs
            id_ (str): ID to look up in the mappings

        Returns:
            str: The corresponding mapped ID if found, None otherwise
        """
        old_to_new_question_map = {}
        new_to_old_question_map = {}
        old_to_new_section_map = {}
        new_to_old_section_map = {}

        for pair in section_pairs:
            old_section = pair["original section"]
            new_section = pair["copy section"]

            old_to_new_section_map[old_section["id"]] = new_section["id"]
            new_to_old_section_map[new_section["id"]] = old_section["id"]

            old_questions = old_section["questions"]
            new_questions = new_section["questions"]

            for old_q, new_q in zip(old_questions, new_questions):
                old_to_new_question_map[old_q["id"]] = new_q["id"]
                new_to_old_question_map[new_q["id"]] = old_q["id"]

        return (
            old_to_new_question_map.get(id_)
            or new_to_old_question_map.get(id_)
            or old_to_new_section_map.get(id_)
            or new_to_old_section_map.get(id_)
        )

    def run(self):
        """
        Main execution method for the TriggersAndActions class.
        
        This method orchestrates the process of creating triggers and actions between
        the old and new tenants. It performs the following steps:
        1. Loads the original questionnaire from the local file
        2. Uploads the questionnaire to the new tenant
        3. Creates triggers in the new tenant
        4. Creates actions in the new tenant
        
        Returns:
            None
        """

        old_questionnaire= Questionnaire_download()
        self.original_questionnaire = old_questionnaire.get_questionnaire()  
        questionnaire_upload = Questionnaire_upload()
        self.questionnaires = questionnaire_upload.run() 
        self.original_questionnaire_id = self.original_questionnaire.get('data', {}).get('id', {})
        self.new_questionnaire_id = self.questionnaires.get('new_questionnaire_id', {}) 
        trigger_mapping = self.create_triggers()
        created_actions = self.create_actions(trigger_mapping)
        print(f"Sucessfully created {self.success_count} triggers")
        print(f"Sucessfully created {len(created_actions)} actions")

def main():

        triggers_and_actions = TriggersAndActions()
        triggers_and_actions.run()
if __name__ == "__main__":
    sys.exit(main())