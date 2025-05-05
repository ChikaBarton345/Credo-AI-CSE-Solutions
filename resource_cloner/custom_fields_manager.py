from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from env_manager import EnvManager
from logging_config import setup_logger
from utils import JSONData, export_to_json

LOGGER = setup_logger(Path(__file__).stem)


@dataclass
class CustomFieldDefinition:
    element_type: str
    metadata: Dict[str, Any]
    multiple: bool
    name: str
    options: Dict[str, Any]
    target: str
    type: str


class CustomFieldsManager:
    """GET custom fields from a source tenant or POST to a dest tenant."""

    def __init__(self, env_manager: EnvManager) -> None:
        """Initialize the `CustomFieldsManager` with proper credentials.

        Args:
            env_manager (EnvManager): `EnvManager` object containing critical
                auth and config environment variables.
        """
        self.em = env_manager
        self.src_headers = {"Authorization": f"Bearer {self.em.src.jwt_token}"}
        self.dest_headers = {"Authorization": f"Bearer {self.em.dest.jwt_token}"}

    def get_custom_fields(self) -> JSONData:
        """Retrieve custom fields from the source tenant.

        Returns:
            JSONData: JSON response containing custom fields data.

        Raises:
            `CustomFieldsError`: If retrieval fails.
        """
        url = f"{self.em.src.base_path}/api/v2/{self.em.src.tenant}/custom_fields"
        LOGGER.info(f"Retrieving custom fields from: {self.em.src.tenant}")

        try:
            response = requests.get(url, headers=self.src_headers)
            response.raise_for_status()
            data = response.json()
            count = len(data.get("data", []))
            LOGGER.info(f"Number of custom fields retrieved: {count}")
            return data

        except requests.HTTPError:
            LOGGER.exception(f"API error: {response.status_code} - {response.text}")
        except Exception:
            LOGGER.exception("Error retrieving custom fields.")
        LOGGER.warning("Falling back to empty custom fields list.")
        return {"data": []}

    def _prepare_custom_field_payload(
        self, custom_field: JSONData
    ) -> Optional[JSONData]:
        """Restructure custom field data into formatted JSON.

        Args:
            custom_field (JSONData): Source custom field object.

        Returns:
            (Optional[JSONData]): API-ready payload, otherwise None on prep failure.

        Raises:
            `TypeError`: If field contains missing or invalid attributes.
        """
        try:
            src_attrs = custom_field.get("attributes", {})
            field_obj = CustomFieldDefinition(**src_attrs)  # Enforce strong typing.
            payload = {
                "data": {"attributes": asdict(field_obj), "type": "custom_fields"}
            }
            LOGGER.debug(
                f"Prepared payload for '{src_attrs.get('name')}' with keys:"
                f" {list(payload['data']['attributes'].keys())}"
            )
            return payload
        except TypeError:
            LOGGER.exception("Custom field validation error.")
        except Exception:
            LOGGER.exception("Unexpected error while preparing custom field payload.")
        return None

    def _post_single_custom_field(self, custom_field: JSONData) -> bool:
        """Upload a custom field to the destination tenant.

        Args:
            custom_field (JSONData): API-ready payload for the custom field.

        Returns:
            bool: True if created, False if skipped (already exists).

        Raises:
            `requests.HTTPError`: For general errors during upload.
        """

        field_name = custom_field.get("data", {}).get("attributes", {}).get("name")
        url = f"{self.em.dest.base_path}/api/v2/{self.em.dest.tenant}/custom_fields"
        LOGGER.info(f"Uploading custom field: {field_name}")

        try:
            response = requests.post(url, headers=self.dest_headers, json=custom_field)

            if response.status_code in (200, 201):
                LOGGER.info(f"Successfully uploaded custom field: {field_name}")
                return True

            if response.status_code == 422:
                LOGGER.info(f"Custom field already exists (skipped): {field_name}")
                return False
            LOGGER.warning(
                f"Unexpected status code {response.status_code} for field"
                f" '{field_name}': {response.text}"
            )
            return False
        except requests.RequestException:
            LOGGER.exception(f"Upload failed for custom field: {field_name}")
        except Exception:
            LOGGER.exception(f"Unhandled error uploading: {field_name}")
        return False

    def upload_custom_fields(self, custom_fields: JSONData) -> Dict[str, int]:
        """Upload all custom fields to the destination tenant.

        Iterates through all custom fields retrieved from the source tenant,
        prepares their payloads, and attempts to upload each to the destination tenant.

        Args:
            custom_fields (JSONData): Custom fields JSON data from the source tenant.

        Returns:
            (Dict[str, int]): A dictionary summarizing the upload results ("success",
                "skipped", and "error").
        """
        success_count = 0
        skip_count = 0
        error_count = 0

        fields = custom_fields.get("data", [])
        tenant = self.em.dest.tenant
        total = len(fields)
        LOGGER.info(f"Uploading {total} custom fields to tenant: {tenant}")

        for idx, field in enumerate(fields, start=1):
            field_name = field.get("attributes", {}).get("name", "unknown")
            LOGGER.info(f"[{idx}/{total}] Processing field: {field_name}")

            try:
                payload = self._prepare_custom_field_payload(field)
                if not payload:
                    LOGGER.warning(
                        f"Skipping field due to payload prep failure: {field_name}"
                    )
                    error_count += 1
                    continue
                uploaded = self._post_single_custom_field(payload)
                success_count += uploaded
                skip_count += not uploaded
            except Exception as exc:
                error_count += 1
                LOGGER.warning(f"[{idx}/{total}] Field upload failed: {exc}")

        stats = {
            "success": success_count,
            "skipped": skip_count,
            "error": error_count,
        }
        LOGGER.info(f"Custom field upload summary: {stats}")
        return stats


def main():
    """Retrieve all custom fields from the source tenant."""
    em = EnvManager()
    cfm = CustomFieldsManager(em)
    custom_fields = cfm.get_custom_fields()
    export_to_json(custom_fields, "src-custom-fields.json")
    upload_stats = cfm.upload_custom_fields(custom_fields)
    export_to_json(upload_stats, "custom-field-upload-stats.json")
    print(upload_stats)


if __name__ == "__main__":
    main()
