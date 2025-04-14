import requests
from typing import Dict
from q_manager_utils import BaseError, CustomFieldsError, APIError
from dotenv import load_dotenv
import os
from get_bearer_token import TokenManager
import sys

load_dotenv(dotenv_path=".env", override=True)

class CustomFieldsDownloader:
    def __init__(self):
        try:
            token_manager = TokenManager(version="old")
            old_token=token_manager.run()          
            token_manager = TokenManager(version="new")
            new_token=token_manager.run()
            
            self.base_path = os.getenv("OLD_BASE_PATH")
            self.tenant_old = os.getenv("OLD_TENANT")
            self.tenant_new = os.getenv("NEW_TENANT")
            self.headers_old = {"Authorization": f"Bearer {old_token}"}
            self.headers_new = {"Authorization": f"Bearer {new_token}"}
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0
        except Exception as e:
            print(f"Error during custom fields initialization: {e}")
            raise CustomFieldsError(f"Failed to initialize custom fields: {str(e)}")
    
    def get_custom_fields(self):
        """
        Retrieves custom fields from the old tenant via API call.

        Makes a GET request to fetch all custom fields from the old tenant's endpoint.
        Custom fields define additional metadata and attributes that can be attached to 
        questionnaire elements.

        Returns:
            dict: JSON response containing custom fields data if successful

        Raises:
            CustomFieldsError: If there is an error retrieving the custom fields,
                             with detailed error information including:
                             - Request URL
                             - Request headers
                             - Error message
                             - Source function
                             - Error line number
        """
        try:
            print(f"=== Getting Custom Fields from {self.tenant_old} === ")
            response = requests.get(f"{self.base_path}/api/v2/{self.tenant_old}/custom_fields", headers = self.headers_old)
            if response.status_code in [200, 201]:
                print(f"✓ Successfully retrieved Custom Fields from {self.tenant_old}\n")
                return response.json()
        except Exception as e:
            details = {
                    "request_url": f"{self.base_path}/api/v2/{self.tenant_old}/custom_fields",
                    "request_headers": self.headers_old,
                    "error_message": str(e)
                }
            raise CustomFieldsError(
                message="Failed to retrieve custom fields",
                error_type="RetrievalError",
                details=details,
                source="get_custom_fields",
                error_line=sys.exc_info()[2].tb_lineno
            )
    
    def run(self):
        return self.get_custom_fields()

def main():
    custom_fields_downloader = CustomFieldsDownloader()
    custom_fields_downloader.run()
    # print(custom_fields)
    # write_to_json = WriteToJson(custom_fields, "custom_fields.json")
    # write_to_json.write_pretty_json()
if __name__ == "__main__":
    main()