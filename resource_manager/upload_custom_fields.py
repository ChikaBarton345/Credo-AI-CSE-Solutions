import requests
from typing import Dict
from q_manager_utils import BaseError, CustomFieldsError, APIError
from download_custom_fields import CustomFieldsDownloader
from dotenv import load_dotenv
import os
from get_bearer_token import TokenManager
import sys

load_dotenv(dotenv_path=".env", override=True)

class CustomFieldsUploader:
    def __init__(self):
        try:
            token_manager = TokenManager(version="new")
            new_token=token_manager.run()            
            self.base_path = os.getenv("OLD_BASE_PATH")            
            self.tenant_new = os.getenv("NEW_TENANT")
            self.headers_new = {"Authorization": f"Bearer {new_token}"}
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0
        except Exception as e:
            print(f"Error during custom fields initialization: {e}")
            raise CustomFieldsError(f"Failed to initialize custom fields: {str(e)}")

    
    def format_custom_fields(self, custom_field):
        try:
            formatted_custom_fields = {
                "data": {
                    "attributes": {
                    "element_type": custom_field["attributes"]["element_type"],
                    "metadata": custom_field["attributes"]["metadata"],
                    "multiple": custom_field["attributes"]["multiple"],
                    "name": custom_field["attributes"]["name"],
                    "options": custom_field["attributes"]["options"],
                    "target": custom_field["attributes"]["target"],
                    "type": custom_field["attributes"]["type"]
                    },
                    "type": "custom_fields"
                }
                }
            
            return formatted_custom_fields
        except Exception as e:
            print(f"Error during custom fields formatting: {e}")
            raise CustomFieldsError(f"Failed to format custom fields: {str(e)}")
    
    def upload_custom_field(self, formatted_custom_field):
        try:
            print(f"Creating custom field: {formatted_custom_field.get('data').get('attributes').get('name')}")
            response = requests.post(f"{self.base_path}/api/v2/{self.tenant_new}/custom_fields", headers = self.headers_new, json=formatted_custom_field)
            if response.status_code in [200, 201]:
                print(f"✓ Successfully uploaded custom field: {formatted_custom_field.get('data').get('attributes').get('name')}\n")
            elif response.status_code == 422:
                print(f"✗ Custom field already exists: {formatted_custom_field.get('data').get('attributes').get('name')} Skipping...\n")
            else:
                raise APIError(f"Failed to upload custom field: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Error during custom field upload: {e}")
            raise CustomFieldsError(f"Failed to upload custom field: {(e)}")

    def upload_custom_fields(self):
        try:
            print(f"=== Creating Custom Fields on {self.tenant_new} === \n")
            for custom_field in self.custom_fields["data"]:
                self.formatted_custom_fields = self.format_custom_fields(custom_field)
                self.upload_custom_field(self.formatted_custom_fields)
        except Exception as e:
            print(f"Error during custom fields upload: {e}")
            raise CustomFieldsError(message=f"Failed to upload custom fields",
                                     error_type="CustomFieldsUploadError",
                                       source="upload_custom_fields",
                                         error_line=sys.exc_info()[2].tb_lineno
                                         )
        
    def run(self):
        custom_fields_downloader = CustomFieldsDownloader()
        self.custom_fields = custom_fields_downloader.run()
        self.upload_custom_fields()

def main():
    custom_fields_uploader = CustomFieldsUploader()
    custom_fields_uploader.run()

if __name__ == "__main__":
    main()