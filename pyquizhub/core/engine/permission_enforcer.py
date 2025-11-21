"""
Permission enforcement for creator and user access control.

This module implements the multi-tier permission system:
- Creator tiers: RESTRICTED, STANDARD, ADVANCED, ADMIN
- User levels: GUEST, BASIC, PREMIUM, RESTRICTED
- API access control based on permissions
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, parse_qs
import re

from pyquizhub.core.engine.variable_types import (
    CreatorPermissionTier,
    UserPermissionLevel,
    VariableStore,
    VariableTag
)
from pyquizhub.core.engine.url_validator import URLValidator, APIAllowlistManager
from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


class PermissionEnforcer:
    """
    Enforces creator and user permissions for API integrations.

    Validates that:
    - Creators can only use APIs allowed by their tier
    - Variables used in APIs are safe
    - Users have access to required features
    """

    # Maximum API calls per session by tier
    MAX_API_CALLS_BY_TIER = {
        CreatorPermissionTier.RESTRICTED: 5,
        CreatorPermissionTier.STANDARD: 20,
        CreatorPermissionTier.ADVANCED: 50,
        CreatorPermissionTier.ADMIN: 999999,  # Effectively unlimited
    }

    def __init__(
        self,
        creator_tier: CreatorPermissionTier,
        user_level: UserPermissionLevel,
        variable_store: VariableStore,
        allowlist_manager: APIAllowlistManager | None = None
    ):
        """
        Initialize permission enforcer.

        Args:
            creator_tier: Creator's permission tier
            user_level: User's permission level
            variable_store: Variable store for checking variable safety
            allowlist_manager: API allowlist manager (uses default if None)
        """
        self.creator_tier = creator_tier
        self.user_level = user_level
        self.variable_store = variable_store
        self.allowlist_manager = allowlist_manager or APIAllowlistManager()

        # Track API calls in this session
        self.api_calls_made = 0

        logger.info(
            f"Permission enforcer initialized: creator={creator_tier.value}, "
            f"user={user_level.value}"
        )

    def validate_api_integration(self, api_config: dict[str, Any]) -> None:
        """
        Validate that API integration is allowed for creator tier.

        Args:
            api_config: API integration configuration

        Raises:
            PermissionError: If creator tier doesn't allow this API configuration
            ValueError: If API configuration is invalid
        """
        # Check rate limit
        max_calls = self.MAX_API_CALLS_BY_TIER[self.creator_tier]
        if self.api_calls_made >= max_calls:
            raise PermissionError(
                f"API call limit reached for tier {self.creator_tier.value}: "
                f"{max_calls} calls per session"
            )

        # Extract URL (could be 'url' or 'base_url')
        url = api_config.get("url") or api_config.get("base_url")
        if not url:
            raise ValueError("API integration missing 'url' or 'base_url'")

        # Validate URL format
        URLValidator.validate_url(url)

        # Check allowlist (RESTRICTED tier only uses allowlisted APIs)
        if self.creator_tier == CreatorPermissionTier.RESTRICTED:
            if not self.allowlist_manager.is_allowed(url):
                raise PermissionError(
                    f"Tier {self.creator_tier.value} can only use allowlisted APIs. "
                    f"URL not allowed: {url}"
                )

        # Validate variable usage in URL based on tier
        self._validate_variable_usage_in_url(url, api_config)

        # Validate method based on tier
        method = api_config.get("method", "GET").upper()
        self._validate_http_method(method)

        # Validate body templates (ADVANCED+ only)
        if "body" in api_config or "body_template" in api_config:
            if self.creator_tier not in (
                    CreatorPermissionTier.ADVANCED,
                    CreatorPermissionTier.ADMIN):
                raise PermissionError(
                    f"Tier {self.creator_tier.value} cannot use request body templates. "
                    f"Upgrade to ADVANCED tier."
                )
            self._validate_body_template(
                api_config.get("body") or api_config.get("body_template"))

        logger.debug(
            f"API integration validated for tier {self.creator_tier.value}")

    def _validate_variable_usage_in_url(
            self, url: str, api_config: dict[str, Any]) -> None:
        """
        Validate that variable usage in URL is allowed for creator tier.

        RESTRICTED: No variables in URLs
        STANDARD: Variables only in query parameters
        ADVANCED+: Variables anywhere (with safety checks)

        Args:
            url: Base URL
            api_config: Full API configuration

        Raises:
            PermissionError: If variable usage violates tier restrictions
            ValueError: If variables used are not safe for API use
        """
        # Check for template variables in base URL
        # This was already rejected by URLValidator, but double-check
        if self._contains_template_variables(url):
            raise ValueError(
                "Template variables not allowed in base URL. "
                "Use query_params or body for dynamic values."
            )

        # RESTRICTED tier: No variables at all
        if self.creator_tier == CreatorPermissionTier.RESTRICTED:
            # Check query params
            if "query_params" in api_config or "param_source" in api_config:
                raise PermissionError(
                    f"Tier {self.creator_tier.value} cannot use variables in API requests. "
                    f"Only static URLs allowed."
                )
            return

        # STANDARD tier: Variables only in query parameters
        if self.creator_tier == CreatorPermissionTier.STANDARD:
            # Can use query params
            if "query_params" in api_config:
                self._validate_query_param_variables(
                    api_config["query_params"])

            # Cannot use path templates
            if "url_template" in api_config or "path_template" in api_config:
                raise PermissionError(
                    f"Tier {self.creator_tier.value} cannot use path templates. "
                    f"Upgrade to ADVANCED tier."
                )
            return

        # ADVANCED+ tier: Can use variables anywhere (with safety validation)
        if self.creator_tier in (
                CreatorPermissionTier.ADVANCED,
                CreatorPermissionTier.ADMIN):
            # Validate all variables used are safe
            if "url_template" in api_config:
                self._validate_url_template_variables(
                    api_config["url_template"])

            if "query_params" in api_config:
                self._validate_query_param_variables(
                    api_config["query_params"])

            if "param_source" in api_config:
                self._validate_param_source_variables(
                    api_config["param_source"])

    def _validate_http_method(self, method: str) -> None:
        """
        Validate HTTP method is allowed for creator tier.

        RESTRICTED/STANDARD: GET only
        ADVANCED+: GET, POST, PUT, PATCH, DELETE

        Args:
            method: HTTP method

        Raises:
            PermissionError: If method not allowed for tier
        """
        if self.creator_tier in (
                CreatorPermissionTier.RESTRICTED,
                CreatorPermissionTier.STANDARD):
            if method != "GET":
                raise PermissionError(
                    f"Tier {self.creator_tier.value} can only use GET requests. "
                    f"Upgrade to ADVANCED tier for {method} requests."
                )

        # ADVANCED+ can use any method
        allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
        if method not in allowed_methods:
            raise ValueError(f"Invalid HTTP method: {method}")

    def _validate_query_param_variables(
            self, query_params: dict[str, Any]) -> None:
        """
        Validate that variables used in query parameters are safe.

        Args:
            query_params: Query parameters configuration

        Raises:
            ValueError: If unsafe variables are used
        """
        for param_name, param_value in query_params.items():
            # If param_value references a variable
            if isinstance(param_value, str):
                vars_used = self._extract_variable_references(param_value)
                for var_name in vars_used:
                    if not self.variable_store.is_safe_for_api_use(var_name):
                        raise ValueError(
                            f"Variable '{var_name}' cannot be used in API requests. "
                            f"User input strings without enum constraints are unsafe. "
                            f"Use string type with enum constraint for safe variable usage."
                        )

    def _validate_url_template_variables(self, url_template: str) -> None:
        """
        Validate variables used in URL template.

        Args:
            url_template: URL template with {variable} placeholders

        Raises:
            ValueError: If unsafe variables are used
        """
        vars_used = self._extract_variable_references(url_template)
        for var_name in vars_used:
            if not self.variable_store.is_safe_for_api_use(var_name):
                raise ValueError(
                    f"Variable '{var_name}' cannot be used in URL template. "
                    f"Only safe variables (numeric, enum strings) allowed in URLs."
                )

    def _validate_param_source_variables(
            self, param_source: dict[str, str]) -> None:
        """
        Validate variables referenced in param_source mapping.

        Args:
            param_source: Mapping of param -> variable reference

        Raises:
            ValueError: If unsafe variables are used
        """
        for param_name, var_ref in param_source.items():
            # var_ref format: "variables.var_name"
            if var_ref.startswith("variables."):
                var_name = var_ref.replace("variables.", "")
                if not self.variable_store.is_safe_for_api_use(var_name):
                    raise ValueError(
                        f"Variable '{var_name}' cannot be used in API parameter. "
                        f"Unsafe for API use (untrusted user input)."
                    )

    def _validate_body_template(self, body: Any) -> None:
        """
        Validate request body template (ADVANCED+ only).

        Args:
            body: Request body (can contain variable references)

        Raises:
            ValueError: If unsafe variables are used
        """
        if isinstance(body, dict):
            for key, value in body.items():
                if isinstance(value, str):
                    vars_used = self._extract_variable_references(value)
                    for var_name in vars_used:
                        if not self.variable_store.is_safe_for_api_use(
                                var_name):
                            raise ValueError(
                                f"Variable '{var_name}' cannot be used in request body. "
                                f"Unsafe variables not allowed in API requests."
                            )
                elif isinstance(value, dict):
                    self._validate_body_template(value)

    def _contains_template_variables(self, text: str) -> bool:
        """Check if text contains template variable syntax."""
        return "{" in text or "}" in text or "${" in text

    def _extract_variable_references(self, text: str) -> list[str]:
        """
        Extract variable names from template string.

        Supports formats:
        - {var_name}
        - {variables.var_name}
        - ${var_name}

        Args:
            text: Template string

        Returns:
            List of variable names
        """
        var_names = []

        # Match {var_name} or {variables.var_name}
        for match in re.finditer(r'\{([^}]+)\}', text):
            var_ref = match.group(1)
            # Strip "variables." prefix if present
            if var_ref.startswith("variables."):
                var_ref = var_ref.replace("variables.", "")
            var_names.append(var_ref)

        # Match ${var_name}
        for match in re.finditer(r'\$\{([^}]+)\}', text):
            var_ref = match.group(1)
            if var_ref.startswith("variables."):
                var_ref = var_ref.replace("variables.", "")
            var_names.append(var_ref)

        return var_names

    def check_user_can_access_api(self, api_config: dict[str, Any]) -> bool:
        """
        Check if user's permission level allows access to this API.

        Args:
            api_config: API configuration with access_level

        Returns:
            True if user can access, False otherwise
        """
        access_level = api_config.get("access_level", "public_safe")

        # Map access levels to required user levels
        if access_level == "public_safe":
            # Everyone can access
            return True

        elif access_level == "basic":
            # BASIC+ users
            return self.user_level in (
                UserPermissionLevel.BASIC,
                UserPermissionLevel.PREMIUM
            )

        elif access_level == "premium":
            # PREMIUM users only
            return self.user_level == UserPermissionLevel.PREMIUM

        elif access_level == "admin":
            # No regular users can access (admin-only APIs)
            return False

        # Unknown access level - deny by default
        logger.warning(f"Unknown access_level: {access_level}, denying access")
        return False

    def increment_api_call_count(self) -> None:
        """Increment the API call counter."""
        self.api_calls_made += 1
        logger.debug(
            f"API calls: {self.api_calls_made}/{self.MAX_API_CALLS_BY_TIER[self.creator_tier]}"
        )

    def get_remaining_api_calls(self) -> int:
        """Get number of remaining API calls for this session."""
        max_calls = self.MAX_API_CALLS_BY_TIER[self.creator_tier]
        return max(0, max_calls - self.api_calls_made)


def validate_creator_permissions(
    creator_tier: CreatorPermissionTier,
    quiz_data: dict[str, Any],
    variable_store: VariableStore
) -> None:
    """
    Validate that quiz respects creator's permission tier.

    This is called during quiz upload/validation.

    Args:
        creator_tier: Creator's permission tier
        quiz_data: Complete quiz JSON
        variable_store: Variable store for the quiz

    Raises:
        PermissionError: If quiz violates creator's permissions
        ValueError: If quiz configuration is invalid
    """
    # Create enforcer (user level doesn't matter for quiz validation)
    enforcer = PermissionEnforcer(
        creator_tier=creator_tier,
        user_level=UserPermissionLevel.PREMIUM,  # Dummy value
        variable_store=variable_store
    )

    # Validate all API integrations
    api_integrations = quiz_data.get("api_integrations", [])
    for api_config in api_integrations:
        enforcer.validate_api_integration(api_config)

    logger.info(
        f"Quiz validated for creator tier {creator_tier.value}: "
        f"{len(api_integrations)} API integrations"
    )
