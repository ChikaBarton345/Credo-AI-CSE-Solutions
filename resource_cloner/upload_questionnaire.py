import requests
from typing import Dict
from q_manager_utils import BaseError, QuestionnaireError
from download_questionnaire import QuestionnaireDownloader
import os
import json
from dotenv import load_dotenv, dotenv_values
import sys
from get_bearer_token import TokenManager
from pathlib import Path

loaded = load_dotenv(dotenv_path=".env", override=True)

class QuestionnaireUploader:
    def __init__(self):
        try:
            token = TokenManager(version="new").get_token()
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("NEW_BASE_PATH")


            self.q_id = env_vars.get("OLD_QUESTIONNAIRE_ID")
            self.q_ver = env_vars.get("OLD_QUESTIONNAIRE_VERSION")
            self.q_orig = {}
            self.tenant = env_vars.get("NEW_TENANT")
            self.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0

        except Exception as exc:
            print(f"Error during questionnaire initialization: {exc}")
            raise QuestionnaireError(f"Failed to initialize questionnaire: {str(exc)}")

    def create_questionnaire_bases(self, id):
        """Create a questionnaire base and return the questionnaire base ID.

        Creates a new questionnaire base by making a POST request to the API with the
        questionnaire metadata. If successful, returns the new questionnaire base ID.
        If the questionnaire already exists (422 status), returns the original ID.

        Args:
            id (str): The ID to use for the new questionnaire base

        Returns:
            str: The questionnaire base ID (either newly created or existing)

        Raises:
            `QuestionnaireError`: If there is an error creating the questionnaire base.
        """
        try:
            print(f"Creating questionnaire base: {id}")
            payload = {
                "data": {
                    "attributes": {
                        "id": id,
                        "name": "Copy of " + self.q_orig.get('data', {}).get('attributes', {}).get('name'),
                        "info": self.q_orig.get('data', {}).get('attributes', {}).get("info", {}),
                        "metadata": self.q_orig.get('data', {}).get('attributes', {}).get("metadata", {}),
                    },
                    "type": "resource-type"
                }
            }
            response = requests.post(f"{self.base_path}/api/v2/{self.tenant}/questionnaire_bases", json=payload, headers=self.headers)
            if response.status_code in [200, 201]:
                self.success_count += 1
                print(f"✓ Successfully created questionnaire base: {id}")
                return response.json().get('data', {}).get('id')

            elif response.status_code == 422:
                self.skip_count += 1
                print(f"ℹ Skipping questionnaire base creation: {id} - Already exists")
                return id
            else:
               response.raise_for_status()

        except Exception as e:
            details = {"questionnaire_id": id,
                            "request_url": response.request.url if response.request else None,
                            "response_status": response.status_code if response.status_code else None,
                            "response_body": response.text if response.text else None
                           }
            raise QuestionnaireError(
                    message=f"Failed to create questionnaire base: {details}",
                    error_type="QuestionnaireError",
                    status_code=response.status_code,
                    details=details,
                    source="create_questionnaire_base",
                    error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None)

    def construct_questionnaire(self) -> Dict:
        """
        Construct a new questionnaire by copying sections and questions from an existing questionnaire.

        This function:
        - Extracts sections and questions from the original questionnaire
        - Creates a new questionnaire structure with the same metadata and info
        - Copies each section and its questions while preserving attributes like:
          - Question text, type, requirements
          - Select options and alert triggers
          - Hidden/required flags
          - Descriptions

        Returns:
            Dict: The constructed questionnaire dictionary with all sections and questions
        """
        try:
            existing_sections = self.q_orig.get('data', {}).get('attributes', {}).get('sections', [])
            self.current_version = self.q_orig.get('data', {}).get('attributes', {}).get('version', 0)
            print(f"Found {len(existing_sections)} sections in existing questionnaire")
            new_questionnaire = {
                "data": {
                    "attributes": {
                        "info": self.q_orig.get('data', {}).get('attributes', {}).get("info", {}),
                        "metadata": self.q_orig.get('data', {}).get('attributes', {}).get("metadata", {}),
                        "draft": False,
                        "sections": [],
                        "version": self.current_version
                    }
                }
            }
            for section_index, section in enumerate(existing_sections, 1):
                try:
                    print(f"\nProcessing section {section_index}/{len(existing_sections)}: {section.get('title', 'Untitled')}")

                    new_section = {
                        "description": section.get('description'),
                        "title": section.get('title'),
                        "questions": []
                    }

                    questions = section.get('questions', [])
                    print(f"Found {len(questions)} questions in section")
                    for q_index, question in enumerate(questions, 1):
                        try:
                            print(f"Processing question {q_index}/{len(questions)}")
                            new_question = {
                                "question": question.get('question'),
                                "evidence_type": question.get('evidence_type'),
                                "required": question.get('required'),
                                "hidden": question.get('hidden'),
                                "multiple": question.get('multiple'),
                                "alert_triggers": question.get('alert_triggers'),
                                "description": question.get('description')
                            }
                            if question.get('select_options'):
                                new_question["select_options"] = question['select_options']
                                print(f"Added {len(question['select_options'])} select options")

                            new_section["questions"].append(new_question)

                        except Exception as e:
                            print(f"Warning: Failed to process question {q_index}: {str(e)}")
                            continue

                    new_questionnaire["data"]["attributes"]["sections"].append(new_section)
                    print(f"✓ Successfully added section: {new_section['title']}")

                except Exception as e:
                    print(f"Warning: Failed to process section {section_index}: {str(e)}")
                    continue

            print(f"\nFinal questionnaire contains {len(new_questionnaire)} sections")
            print("\n=== Questionnaire Construction Completed Successfully ===")

            return new_questionnaire

        except Exception as e:
            raise QuestionnaireError(
                message=f"Error constructing questionnaire: {str(e)}",
                error_type="QuestionnaireError",
                details={
                    "questionnaire_id": id,
                    "error_line": sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None,
                },
                source="construct_questionnaire",
                error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
            )

    def post_questionnaire(self, questionnaire_base_id, payload):
        """
        Posts a questionnaire version with sections and questions to the API.

        Args:
            questionnaire_base_id (str): The ID of the base questionnaire to create a version for
            payload (dict): The questionnaire data containing sections and questions

        Returns:
            requests.Response: The API response object containing the created questionnaire data if successful

        Raises:
            QuestionnaireError: If the API request fails, with details about the failure
        """
        try:
            response = requests.post( f"{self.base_path}/api/v2/{self.tenant}/questionnaire_bases/{questionnaire_base_id}/versions", json=payload, headers=self.headers)
            return response
        except requests.exceptions.RequestException as e:
            error_details = {
                "request_url": e.request.url if e.request else None,
                "response_status": e.response.status_code if e.response else None,
                "response_body": e.response.text if e.response else None,
                "questionnaire_base_id": questionnaire_base_id,
                "operation": "questionnaire_creation"
            }
            raise QuestionnaireError(
                message="Failed to post questionnaire",
                error_type="RequestError",
                status_code=getattr(e.response, 'status_code', None),
                details=error_details,
                source="post_questionnaire",
                error_line=sys.exc_info()[2].tb_lineno
            )

    def create_questionnaire(self, questionnaire_base_id, new_questionnaire_payload):
        """
        Creates a new version of a questionnaire with sections and questions by making an API request.

        Args:
            questionnaire_base_id (str): The ID of the base questionnaire to create a version for
            new_questionnaire_payload (dict): The questionnaire data containing version, sections and questions

        Returns:
            dict: The API response data containing the created questionnaire version if successful.
                 Response includes questionnaire ID, version number and other metadata.

        Raises:
            requests.exceptions.RequestException: If the API request fails due to network or server errors
            ValueError: If required fields like questionnaire ID or version are missing from the response
            QuestionnaireError: If questionnaire creation fails due to validation or other API errors
        """
        try:
            response = self.post_questionnaire(questionnaire_base_id, new_questionnaire_payload)
            if response.status_code in [200, 201]:
                self.success_count += 1
                print(f"✓ Successfully created newquestionnaire version: {response.json().get('data', {}).get('id')} in {self.tenant} tenant \n")
                return response.json()
            elif response.status_code == 422:
                print(f"current version: {self.current_version}")
                new_version = int(self.current_version) + 1
                new_questionnaire_payload["data"]["attributes"]["version"] = f"{new_version}"
                retry = self.post_questionnaire(questionnaire_base_id, new_questionnaire_payload)
                if retry.status_code in [200, 201]:
                    self.success_count += 1
                    print(f"✓ Successfully created new questionnaire version: {retry.json().get('data', {}).get('id')}\n")
                    return retry.json()
                else:
                    self.skip_count += 1
                    print(f"ℹ No new questionnaire version created: {response.json().get('data', {}).get('id')}\n")
                    raise QuestionnaireError(
                        message=f"Failed to create version {new_version} of {questionnaire_base_id}: {response.json()}",
                        error_type="QuestionnaireError",
                        status_code=response.status_code,
                        details=response.json().get('detail'),
                        source="create_questionnaire",
                        error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
                    )
            else:
                response.raise_for_status()
                self.error_count += 1
                print(f"✗ Failed to create new questionnaire version: {response.status_code}\n")
                return None

        except requests.exceptions.RequestException as e:
            error_details = {
                "request_url": getattr(e.request, 'url', None),
                "response_status": getattr(e.response, 'status_code', None),
                "response_body": getattr(e.response, 'text', None),
                "questionnaire_id": self.q_id,
                "operation": "questionnaire_creation"
            }

            raise QuestionnaireError(
                message="Failed to create questionnaire",
                error_type="RequestError",
                status_code=getattr(e.response, 'status_code', None),
                details=error_details,
                source="create_questionnaire",
                error_line=sys.exc_info()[2].tb_lineno if sys.exc_info()[2] else None
            )

        except ValueError as e:
            raise QuestionnaireError(
                message="Invalid data for questionnaire creation",
                error_type="ValidationError",
                details={
                    "questionnaire_id": self.q_id,
                    "error_message": str(e),
                    "operation": "questionnaire_creation"
                }
            )

    def map_questionnaire(self, new_questionnaire, old_questionnaire):
            """
            Zips each section from the old and new questionnaires into pairs.
            Each entry contains: {"original": <old_section>, "copy": <new_section>}
            """
            try:
                zipped_sections = []
                old_sections = old_questionnaire.get('data', {}).get('attributes', {}).get('sections', [])
                new_sections = new_questionnaire.get('data', {}).get('attributes', {}).get('sections', [])
                for old_section, new_section in zip(old_sections, new_sections):
                    zipped_sections.append({
                        "original section": old_section,
                        "copy section": new_section
                    })
                return zipped_sections

            except Exception as e:
                raise QuestionnaireError(
                    message=f"Failed to zip questionnaire sections: {str(e)}"
                )

    def run(self):
        """
        Runs the questionnaire creation process.
        """
        try:
            old_questionnaire= QuestionnaireDownloader()
            self.q_orig = old_questionnaire.get_questionnaire()
            new_questionnaire_payload = self.construct_questionnaire()
            questionnaire_base_id = self.create_questionnaire_bases(f"{self.q_id}COPY")
            new_questionnaire = self.create_questionnaire(questionnaire_base_id, new_questionnaire_payload)
            return {"old_new_questionnaire_map": self.map_questionnaire(new_questionnaire, self.q_orig), "new_questionnaire_id": new_questionnaire.get('data', {}).get('id', {})}
        except Exception as e:
            raise QuestionnaireError(
                message=f"Questionnaire is not uploaded: {str(e)}",
            )

def main():
    questionnaire = QuestionnaireUploader()
    questionnaire.run()
if __name__ == "__main__":
    main()