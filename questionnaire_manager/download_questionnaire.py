import requests
from typing import Dict
from q_manager_utils import BaseError, QuestionnaireError, APIError
from write_to_json import WriteToJson
from dotenv import load_dotenv
import os
from get_bearer_token import TokenManager
import sys

load_dotenv(dotenv_path=".env", override=True)

class Questionnaire:
    def __init__(self):
        try:
            token_manager = TokenManager(version="old")
            token=token_manager.run()          
            self.questionnaire_id = os.getenv("OLD_QUESTIONNAIRE_ID")
            self.questionnaire_version = os.getenv("OLD_QUESTIONNAIRE_VERSION")
            self.base_path = os.getenv("OLD_BASE_PATH")
            self.tenant = os.getenv("OLD_TENANT")
            self.jwt_token = os.getenv("OLD_JWT_TOKEN")
            self.headers = {"Authorization": f"Bearer {token}"}
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0
        except Exception as e:
            print(f"Error during questionnaire initialization: {e}")
            raise QuestionnaireError(f"Failed to initialize questionnaire: {str(e)}")
    
    def get_questionnaire(self):
        try:
            print(f"Getting questionnaire: {self.questionnaire_id}+{self.questionnaire_version} from {self.tenant}")
            response = requests.get(f"{self.base_path}/api/v2/{self.tenant}/questionnaires/{self.questionnaire_id}+{self.questionnaire_version}", headers = self.headers)
            if response.status_code in [200, 201]:
                print(f"✓ Successfully retrieved {self.questionnaire_id}+{self.questionnaire_version} from {self.tenant}")
                write_to_json = WriteToJson(response.json(), "questionnaire.json")
                write_to_json.write_pretty_json()
                response.raise_for_status()
                return response.json()
            else:
                response.raise_for_status()
            
        except Exception as e:
            details = {
                    "questionnaire_id": self.questionnaire_id,
                    "questionnaire_version": self.questionnaire_version,
                    "response_status": response.status_code,
                    "response_body": response.text, 
                    "request_url": response.request.url,
                    "request_headers": response.request.headers
                }
            raise QuestionnaireError(
                message="Failed to retrieve questionnaire",
                error_type="RetrievalError",
                status_code=getattr(e.response, 'status_code', None),
                details=details,
                source="get_questionnaire",
                error_line=sys.exc_info()[2].tb_lineno
            )
       
def main():
    questionnaire_manager = Questionnaire()
    questionnaire = questionnaire_manager.get_questionnaire()
    write_to_json = WriteToJson(questionnaire, "questionnaire.json")
    write_to_json.write_pretty_json()
if __name__ == "__main__":
    main()