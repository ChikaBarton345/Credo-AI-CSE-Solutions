import sys
from pathlib import Path
from typing import Any, Dict, TypedDict

import requests
from dotenv import dotenv_values, load_dotenv
from download_custom_fields import CustomFieldsDownloader
from get_bearer_token import TokenManager
from q_manager_utils import APIError, CustomFieldsError

load_dotenv(dotenv_path=".env", override=True)


class CustomFieldAttributes(TypedDict):
    """Type definition for custom field attributes.

    Represents the structure of attributes in a custom field, including
    field type, metadata, configuration options, and targeting.
    """

    element_type: str
    metadata: Dict[str, Any]
    multiple: bool
    name: str
    options: Dict[str, Any]
    target: str
    type: str


class FormattedCustomField(TypedDict):
    """Type definition for API-ready custom field payloads."""

    data: Dict[str, Any]


class CustomFieldsUploader:
    """Handle uploading custom fields to add metadata to questionnaire elements."""

    REQUIRED_ATTRIBUTES = [
        "element_type",
        "metadata",
        "multiple",
        "name",
        "options",
        "target",
        "type",
    ]

    def __init__(self, custom_fields: Dict[str, Any]) -> None:
        """Initialize the uploader with credentials and tracking counters.

        Raises:
            CustomFieldsError: When initialization fails due to missing credentials
                or token retrieval errors.
        """
        self.custom_fields = custom_fields

        try:
            new_token = TokenManager(version="new").get_token()
            env_vars = dotenv_values(Path.cwd() / ".env")
            self.base_path = env_vars.get("OLD_BASE_PATH")
            self.tenant_new = env_vars.get("NEW_TENANT")
            self.headers_new = {"Authorization": f"Bearer {new_token}"}
            self.success_count = 0
            self.skip_count = 0
            self.error_count = 0
        except Exception as exc:
            error_msg = f"Error during custom fields initialization: {exc}"
            print(error_msg)
            raise CustomFieldsError(error_msg)

    def _format_custom_field(
        self, custom_field: Dict[str, Any]
    ) -> FormattedCustomField:
        """Transform source custom field into target API format.

        Restructure the custom field data to match API requirements while preserving
        essential attributes.

        Args:
            custom_field (dict): Source custom field object.

        Returns:
            dict: API-ready payload with proper structure.

        Raises:
            CustomFieldsError: If field contains missing or invalid attributes.
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

    def _upload_single_custom_field(self, custom_field: FormattedCustomField) -> bool:
        """Upload a custom field to the target tenant.

        Args:
            custom_field (dict): The formatted custom field payload to upload.

        Returns:
            bool: True if created, False if skipped (already exists).

        Raises:
            CustomFieldsError: For general errors during upload.
            APIError: For API-specific errors with status codes.
        """
        try:
            field_name = (
                custom_field.get("data", {})
                .get("attributes", {})
                .get("name", "unknown")
            )
            print(f"Creating custom field: {field_name}")
            response = requests.post(
                f"{self.base_path}/api/v2/{self.tenant_new}/custom_fields",
                headers=self.headers_new,
                json=custom_field,
            )

            if response.status_code in (200, 201):
                print(f"✓ Successfully uploaded custom field: {field_name}\n")
                self.success_count += 1
                return True

            if response.status_code == 422:
                print(f"↷ Custom field already exists: {field_name} Skipping...\n")
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

        Process each custom field in the collection, format it, and upload it to the target tenant.

        Returns:
            (Dict[str, int]): Statistics about the upload operation
                {
                    "success": count of successfully uploaded fields,
                    "skipped": count of fields that already existed,
                    "error": count of fields that failed to upload
                }

        Raises:
            CustomFieldsError: If there's an error during the upload process
        """
        self.success_count = 0
        self.skip_count = 0
        self.error_count = 0

        if not hasattr(self, "custom_fields") or not self.custom_fields:
            raise CustomFieldsError(
                message="No custom fields to upload. Download custom fields first.",
                error_type="CustomFieldsUploadError",
                source="upload_custom_fields",
            )

        try:
            print(f"Creating custom fields on: {self.tenant_new}")
            fields = self.custom_fields.get("data", [])
            total = len(fields)

            print(f"Processing {total} custom fields...")
            for i, custom_field in enumerate(fields, start=1):
                try:
                    print(f"Field {i}/{total}: Processing...")
                    formatted_field = self._format_custom_field(custom_field)
                    self._upload_single_custom_field(formatted_field)
                except Exception as field_exc:
                    # Continue with next field instead of failing the entire process.
                    print(f"Error with field {i}/{total}: {field_exc}")
                    self.error_count += 1

            return {
                "success": self.success_count,
                "skipped": self.skip_count,
                "error": self.error_count,
            }

        except Exception as exc:
            print(f"Error during custom fields upload: {exc}")
            raise CustomFieldsError(
                message="Failed to upload custom fields.",
                error_type="CustomFieldsUploadError",
                source="upload_custom_fields",
                error_line=getattr(sys.exc_info()[2], "tb_lineno", "unknown"),
            )


def main():
    custom_field_downloader = CustomFieldsDownloader()
    custom_fields = custom_field_downloader.get_custom_fields()
    custom_fields_uploader = CustomFieldsUploader(custom_fields)
    results = custom_fields_uploader.upload_custom_fields()
    print(results)


if __name__ == "__main__":
    main()
