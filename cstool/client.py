from typing import Optional, Dict, Any, Literal

from .api.custom_fields import CustomFieldsAPI
from .api.questionnaires import QuestionnairesAPI
from .api.triggers import TriggersAPI
from .api.actions import ActionsAPI
from .auth.token_manager import TokenManager
from .config import Config
from .exceptions import CSToolError

TenantType = Literal["src", "dest"]

class Client:
    """Client for interacting with CS Tool API endpoints.

    Provides access to various API endpoints for managing questionnaires,
    custom fields, triggers, and actions. Automatically handles authentication.
    """

    def __init__(self, env_path: Optional[str] = None):
        """Initialize the client with authentication for source and destination tenants.

        Args:
            env_path: Optional path to .env file. Defaults to current working directory.

        Raises:
            `CSToolError`: If authentication fails or required config is missing.
        """
        # Load configuration
        self.config = Config(env_path)

        # Authenticate with both tenants
        self._authenticate()

        # Initialize API endpoints
        self.CustomFields = CustomFieldsAPI(self)
        self.Questionnaires = QuestionnairesAPI(self)
        self.Triggers = TriggersAPI(self)
        self.Actions = ActionsAPI(self)

    def _authenticate(self) -> None:
        """Authenticate with source and destination tenants."""
        try:
            src_token_manager = TokenManager(version="src", config=self.config)
            self.src_token = src_token_manager.get_token()
            dest_token_manager = TokenManager(version="dest", config=self.config)
            self.dest_token = dest_token_manager.get_token()

            self.src_headers = {"Authorization": f"Bearer {self.src_token}"}
            self.dest_headers = {"Authorization": f"Bearer {self.dest_token}"}

        except Exception as e:
            raise CSToolError(f"Authentication failed: {e}")

    def get_headers(self, tenant: TenantType) -> Dict[str, str]:
        """Get authentication headers for the specified tenant.

        Args:
            tenant: Either 'src' or 'dest'

        Returns:
            Headers dictionary with authorization token

        Raises:
            ValueError: If an invalid tenant is specified
        """
        if tenant == "src":
            return self.src_headers
        elif tenant == "dest":
            return self.dest_headers
        else:
            raise ValueError(f"Invalid tenant '{tenant}'. Must be 'src' or 'dest'")

    def get_base_url(self, tenant: TenantType) -> str:
        """Get base URL for the specified tenant.

        Args:
            tenant: Either 'src' or 'dest'

        Returns:
            Base URL for the specified tenant

        Raises:
            ValueError: If an invalid tenant is specified
        """
        if tenant == "src":
            return self.config.get("SRC_BASE_PATH")
        elif tenant == "dest":
            return self.config.get("DEST_BASE_PATH")
        else:
            raise ValueError(f"Invalid tenant '{tenant}'. Must be 'src' or 'dest'")

    def get_tenant_id(self, tenant: TenantType) -> str:
        """Get tenant ID for the specified tenant.

        Args:
            tenant: Either 'src' or 'dest'

        Returns:
            Tenant ID for the specified tenant

        Raises:
            ValueError: If an invalid tenant is specified
        """
        if tenant == "src":
            return self.config.get("SRC_TENANT")
        elif tenant == "dest":
            return self.config.get("DEST_TENANT")
        else:
            raise ValueError(f"Invalid tenant '{tenant}'. Must be 'src' or 'dest'")