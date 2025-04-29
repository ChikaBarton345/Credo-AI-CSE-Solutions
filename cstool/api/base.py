from typing import Dict, Any, List, Optional, Literal
import requests

from ..exceptions import APIError

TenantType = Literal["src", "dest"]

class BaseAPI:
    """Base class for all API endpoint handlers."""

    def __init__(self, client):
        """Initialize with client reference.

        Args:
            client: CS Tool client instance
        """
        self.client = client

    def _make_request(
        self,
        method: str,
        path: str,
        tenant: TenantType,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API.

        Args:
            method: HTTP method ('get', 'post', etc.)
            path: API path (added to base URL)
            tenant: Either 'src' or 'dest'
            json: Optional JSON payload
            params: Optional query parameters

        Returns:
            JSON response

        Raises:
            APIError: If the request fails
        """
        # Get base URL and headers for the specified tenant
        base_url = self.client.get_base_url(tenant)
        headers = self.client.get_headers(tenant)
        tenant_id = self.client.get_tenant_id(tenant)

        # Build complete URL
        url = f"{base_url}/api/v2/{tenant_id}/{path}"

        try:
            # Make the request
            request_func = getattr(requests, method.lower())
            response = request_func(
                url=url,
                headers=headers,
                json=json,
                params=params
            )

            # Check for success
            response.raise_for_status()

            # Return JSON response if content exists
            if response.status_code != 204 and response.content:  # No content
                return response.json()
            return {}

        except requests.exceptions.RequestException as e:
            # Handle request errors
            error_message = f"API request failed: {e}"
            if hasattr(e, 'response') and e.response:
                error_message = f"API error: {e.response.status_code} - {e.response.text}"

            raise APIError(error_message)