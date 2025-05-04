import sys
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import dotenv_values, load_dotenv
from download_custom_fields import CustomFieldsDownloader
from get_bearer_token import TokenManager
from q_manager_utils import APIError, CustomFieldsError
from utils import JSONData, export_to_json

load_dotenv(dotenv_path=".env", override=True)


class CustomFieldsUploader:
    """Handle uploading custom fields to add metadata to questionnaire elements."""

    REQUIRED_ATTRIBUTES = {
        "element_type": str,
        "metadata": Dict[str, Any],
        "multiple": bool,
        "name": str,
        "options": Dict[str, Any],
        "target": str,
        "type": str,
    }

    def __init__(self, custom_fields: Dict[str, Any]) -> None:
        """Initialize the uploader with credentials and tracking counters.

        Raises:
            CustomFieldsError: When initialization fails due to missing credentials
                or token retrieval errors.
        """
        self.custom_fields = custom_fields

        try:
            token = TokenManager(version="new").get_token()
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("NEW_BASE_PATH")
            self.tenant = env_vars.get("NEW_TENANT")
            self.headers = {"Authorization": f"Bearer {token}"}
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0
        except Exception as exc:
            error_msg = f"Error during custom fields initialization: {exc}"
            print(error_msg)
            raise CustomFieldsError(error_msg)

    def _prepare_custom_field_payload(self, custom_field: Dict[str, Any]) -> JSONData:
        """Restructure custom field data into formatted JSON.

        Args:
            custom_field (Dict[str, Any]): Source custom field object.

        Returns:
            JSONData: API-ready payload with proper structure.

        Raises:
            `CustomFieldsError`: If field contains missing or invalid attributes.
        """
        try:
            # Extract attributes from source, validating they exist.
            source_attrs = custom_field.get("attributes", {})
            missing_attrs = [
                attr for attr in self.REQUIRED_ATTRIBUTES if attr not in source_attrs
            ]
            if missing_attrs:
                raise CustomFieldsError(
                    f"Missing required attributes: {', '.join(missing_attrs)}"
                )
            attributes = {attr: source_attrs[attr] for attr in self.REQUIRED_ATTRIBUTES}

            # Return the properly-formatted payload.
            return {"data": {"attributes": attributes, "type": "custom_fields"}}

        except KeyError as key_err:
            error_msg = f"Missing key in custom field: {key_err}"
            print(error_msg)
            raise CustomFieldsError(error_msg)
        except Exception as exc:
            error_msg = f"Failed to format custom field: {exc}"
            print(error_msg)
            raise CustomFieldsError(error_msg)

    def _post_single_custom_field(self, custom_field: JSONData) -> bool:
        """Upload a custom field to the target tenant.

        Args:
            custom_field (JSONData): The formatted custom field payload to upload.

        Returns:
            bool: True if created, False if skipped (already exists).

        Raises:
            `CustomFieldsError`: For general errors during upload.
            `APIError`: For API-specific errors with status codes.
        """
        try:
            field_name = (
                custom_field.get("data", {})
                .get("attributes", {})
                .get("name", "unknown")
            )
            print(f"Creating custom field: {field_name}")
            url = f"{self.base_path}/api/v2/{self.tenant}/custom_fields"
            response = requests.post(url, headers=self.headers, json=custom_field)

            if response.status_code in (200, 201):
                print(f"Successfully uploaded custom field: {field_name}")
                self.success_count += 1
                return True

            if response.status_code == 422:
                print(f"Custom field already exists (upload skipped): {field_name}")
                self.skip_count += 1
                return False

            raise APIError(
                f"Failed custom field upload: {response.status_code} - {response.text}"
            )
        except Exception as exc:
            print(f"Error during custom field upload: {exc}")
            self.error_count += 1
            raise CustomFieldsError(f"Error during custom field upload: {exc}")

    def upload_custom_fields(self) -> Dict[str, int]:
        """Upload all custom fields to the target tenant.

        Returns:
            (Dict[str, int]): Statistics about the upload operation.

        Raises:
            `CustomFieldsError`: If there's an error during the upload process.
        """
        # Reset batch upload statistics on each method call.
        self.success_count = 0
        self.skip_count = 0
        self.error_count = 0

        try:
            print(f"Creating custom fields on: {self.tenant}")
            fields = self.custom_fields.get("data", [])
            num_fields = len(fields)
            for i, custom_field in enumerate(fields, start=1):
                try:
                    print(f"Processing custom field: {i}/{num_fields}")
                    formatted_field = self._prepare_custom_field_payload(custom_field)
                    self._post_single_custom_field(formatted_field)
                except Exception as field_exc:
                    # Continue with next field instead of failing the entire process.
                    print(f"Error during custom field upload: {field_exc}")
                    self.error_count += 1

            cf_upload_stats = {
                "success": self.success_count,
                "skipped": self.skip_count,
                "error": self.error_count,
            }
            return cf_upload_stats

        except Exception as exc:
            print(f"Error during custom fields upload: {exc}")
            raise CustomFieldsError(
                message="Failed to upload custom fields.",
                error_type="CustomFieldsUploadError",
                source="upload_custom_fields",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )


def main():
    """Download custom fields from the source tenant, then upload them to the target."""
    custom_fields = CustomFieldsDownloader().get_custom_fields()
    export_to_json(custom_fields, "src-custom-fields.json")
    cf_upload_stats = CustomFieldsUploader(custom_fields).upload_custom_fields()
    export_to_json(cf_upload_stats, "custom-field-upload-stats.json")
    print(cf_upload_stats)
    print(1)


if __name__ == "__main__":
    main()
