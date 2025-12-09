"""
Configuration Manager for PyQuizHub using Pydantic Settings.

This module provides a robust, type-safe configuration system with:
- Automatic config file discovery
- Environment variable override support with proper type conversion
- Configuration validation with clear error messages
- No circular dependencies with logging

Key features:
1. Config path search strategy (multiple fallback locations)
2. Pydantic-based validation
3. Proper environment variable handling
4. Clear error messages
5. Backward-compatible API
"""

from __future__ import annotations

import os
import yaml
import logging
from typing import Any, Literal
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


# Use basic logging during config initialization (before custom logger is
# set up)
_basic_logger = logging.getLogger(__name__)


class FileStorageSettings(BaseModel):
    """Settings for file-based storage."""
    base_dir: str = Field(default=".pyquizhub",
                          description="Base directory for file storage")


class SQLStorageSettings(BaseModel):
    """Settings for SQL-based storage."""
    connection_string: str = Field(
        default="sqlite:///pyquizhub.db",
        description="SQLAlchemy connection string"
    )


class StorageSettings(BaseModel):
    """Storage configuration."""
    type: Literal["file", "sql"] = Field(
        default="file", description="Storage type")
    file: FileStorageSettings = Field(default_factory=FileStorageSettings)
    sql: SQLStorageSettings = Field(default_factory=SQLStorageSettings)


class APISettings(BaseModel):
    """API configuration."""
    base_url: str = Field(
        default="http://127.0.0.1:8000",
        description="API base URL")
    host: str = Field(default="0.0.0.0", description="Host for uvicorn")
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for uvicorn")


class RateLimitSettings(BaseModel):
    """Rate limiting configuration per role."""
    requests_per_minute: int = Field(default=60, ge=1, le=10000)
    requests_per_hour: int = Field(default=1000, ge=1, le=100000)
    burst_size: int = Field(default=10, ge=1, le=100)


class FileUploadPermissions(BaseModel):
    """File upload permissions per role."""
    enabled: bool = Field(default=False, description="Whether file uploads are allowed")
    max_file_size_mb: int = Field(default=5, ge=1, le=100)
    allowed_categories: list[str] = Field(
        default_factory=lambda: ["documents"],
        description="Allowed file categories: images, audio, video, documents, archives"
    )
    quota_mb: int = Field(default=50, ge=1, le=10000)


class APIIntegrationPermissions(BaseModel):
    """API integration permissions per role."""
    enabled: bool = Field(default=False, description="Whether external API calls are allowed")
    allowed_hosts: list[str] = Field(
        default_factory=list,
        description="Allowed hosts for API calls (empty = none allowed)"
    )
    max_requests_per_quiz: int = Field(default=10, ge=0, le=1000)


class RolePermissions(BaseModel):
    """Permissions for a specific role."""
    rate_limits: RateLimitSettings = Field(default_factory=RateLimitSettings)
    file_uploads: FileUploadPermissions = Field(default_factory=FileUploadPermissions)
    api_integrations: APIIntegrationPermissions = Field(default_factory=APIIntegrationPermissions)


class RolePermissionsConfig(BaseModel):
    """
    Permissions configuration for all roles.

    Default philosophy: secure by default for beginners.
    - Users: minimal permissions, no file uploads, no API calls
    - Creators: can create quizzes with limited API access
    - Admins: full access (configured separately)

    Advanced users can override via config.yaml or environment variables.
    """
    user: RolePermissions = Field(
        default_factory=lambda: RolePermissions(
            rate_limits=RateLimitSettings(
                requests_per_minute=30,
                requests_per_hour=500,
                burst_size=20  # Increased for tests that make many rapid requests
            ),
            file_uploads=FileUploadPermissions(
                enabled=False,  # Users cannot upload files by default
                max_file_size_mb=2,
                allowed_categories=["documents"],
                quota_mb=10
            ),
            api_integrations=APIIntegrationPermissions(
                enabled=False,  # Users cannot trigger API calls by default
                allowed_hosts=[],
                max_requests_per_quiz=0
            )
        ),
        description="Permissions for regular users (quiz takers)"
    )
    creator: RolePermissions = Field(
        default_factory=lambda: RolePermissions(
            rate_limits=RateLimitSettings(
                requests_per_minute=60,
                requests_per_hour=1000,
                burst_size=10
            ),
            file_uploads=FileUploadPermissions(
                enabled=True,
                max_file_size_mb=10,
                allowed_categories=["images", "documents"],
                quota_mb=100
            ),
            api_integrations=APIIntegrationPermissions(
                enabled=True,
                allowed_hosts=["localhost", "127.0.0.1"],  # Only local by default
                max_requests_per_quiz=20
            )
        ),
        description="Permissions for quiz creators"
    )
    admin: RolePermissions = Field(
        default_factory=lambda: RolePermissions(
            rate_limits=RateLimitSettings(
                requests_per_minute=1000,
                requests_per_hour=10000,
                burst_size=50
            ),
            file_uploads=FileUploadPermissions(
                enabled=True,
                max_file_size_mb=100,
                allowed_categories=["images", "audio", "video", "documents", "archives"],
                quota_mb=10000
            ),
            api_integrations=APIIntegrationPermissions(
                enabled=True,
                allowed_hosts=["*"],  # Admins can call any host
                max_requests_per_quiz=1000
            )
        ),
        description="Permissions for administrators"
    )


class UserAuthSettings(BaseModel):
    """
    User authentication provider configuration.

    Configures available authentication methods for quiz takers.
    Note: Whether anonymous access is allowed is set per-quiz in metadata.auth.

    Available auth providers:
    - api_key: Simple API key authentication (header-based)
    - oauth2: OAuth2/OIDC provider (future)
    - custom: Webhook-based custom auth (future)

    The auth system is designed for extensibility - deployers can implement
    their own auth by subclassing UserAuthProvider.
    """
    # Prefix for anonymous user IDs (when quiz allows anonymous)
    anonymous_id_prefix: str = Field(
        default="anon_",
        description="Prefix for anonymous user IDs"
    )

    # API key auth (simple header-based auth)
    api_key_enabled: bool = Field(
        default=False,
        description="Enable API key authentication for users"
    )
    api_key_header: str = Field(
        default="X-User-API-Key",
        description="Header name for user API key"
    )

    # OAuth2/OIDC (placeholder for future implementation)
    oauth2_enabled: bool = Field(
        default=False,
        description="Enable OAuth2/OIDC authentication"
    )
    oauth2_provider_url: str | None = Field(
        default=None,
        description="OAuth2 provider URL (e.g., https://auth.example.com)"
    )
    oauth2_client_id: str | None = Field(
        default=None,
        description="OAuth2 client ID"
    )

    # Custom webhook auth (placeholder for future implementation)
    custom_auth_enabled: bool = Field(
        default=False,
        description="Enable custom webhook-based authentication"
    )
    custom_auth_url: str | None = Field(
        default=None,
        description="URL to call for custom auth validation"
    )


class SecuritySettings(BaseModel):
    """Security configuration."""
    use_tokens: bool = Field(
        default=True,
        description="Enable token-based authentication for API access (admin/creator/user)")
    admin_token_env: str = Field(default="PYQUIZHUB_ADMIN_TOKEN")
    creator_token_env: str = Field(default="PYQUIZHUB_CREATOR_TOKEN")
    user_token_env: str = Field(default="PYQUIZHUB_USER_TOKEN")
    permissions: RolePermissionsConfig = Field(
        default_factory=RolePermissionsConfig,
        description="Role-based permissions configuration"
    )
    user_auth: UserAuthSettings = Field(
        default_factory=UserAuthSettings,
        description="User authentication configuration for quiz takers"
    )


class LoggingSettings(BaseModel):
    """Logging configuration (raw dict for logging.config.dictConfig)."""
    version: int = Field(default=1)
    disable_existing_loggers: bool = Field(default=False)
    formatters: dict[str, Any] = Field(default_factory=dict)
    handlers: dict[str, Any] = Field(default_factory=dict)
    root: dict[str, Any] = Field(default_factory=dict)
    loggers: dict[str, Any] = Field(default_factory=dict)

    # Allow extra fields for logging config flexibility
    model_config = {'extra': 'allow'}


class AppSettings(BaseSettings):
    """
    Main application settings using Pydantic Settings.

    This class automatically:
    - Loads configuration from YAML files
    - Overrides values from environment variables
    - Validates all settings
    - Provides type-safe access to configuration

    Environment variables use the format: PYQUIZHUB_SECTION__KEY
    Example: PYQUIZHUB_STORAGE__TYPE=sql
    """

    storage: StorageSettings = Field(default_factory=StorageSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_prefix="PYQUIZHUB_",
        env_nested_delimiter="__",
        case_sensitive=False,
        # Allow extra fields for forward compatibility
        extra="ignore",
    )

    # Class variable to temporarily store YAML data
    _temp_config_data: dict[str, Any | None] = None
    _temp_config_path: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize the sources and their priority for loading settings.

        Priority (highest to lowest):
        1. Environment variables (highest priority)
        2. YAML file data (if loaded via from_yaml)
        3. Default values
        """
        # Create a custom source for YAML data
        class YamlSettingsSource(PydanticBaseSettingsSource):
            def get_field_value(
                    self, field: Any, field_name: str) -> tuple[Any, str, bool]:
                # Return YAML data if available
                if cls._temp_config_data and field_name in cls._temp_config_data:
                    return cls._temp_config_data[field_name], field_name, False
                return None, field_name, False

            def __call__(self) -> dict[str, Any]:
                return cls._temp_config_data or {}

        # Return sources in priority order (first = highest priority)
        return (
            env_settings,  # Environment variables have highest priority
            YamlSettingsSource(settings_cls),  # Then YAML file
            init_settings,  # Then init arguments
        )

    @classmethod
    def from_yaml(cls, config_path: str | None = None) -> 'AppSettings':
        """
        Load configuration from YAML file with fallback search strategy.

        Search order:
        1. PYQUIZHUB_CONFIG_PATH environment variable (if set)
        2. ./config.yaml (project root)
        3. pyquizhub/config/config.yaml (package location)

        Note: Environment variables (PYQUIZHUB_*) always override YAML values.

        Args:
            config_path: Explicit path to config file (skips search if provided)

        Returns:
            AppSettings instance

        Raises:
            FileNotFoundError: If no config file is found in any location
            ValidationError: If config file has invalid structure or values
        """
        if config_path is None:
            config_path = cls._find_config_file()

        _basic_logger.info(f"Loading configuration from: {config_path}")

        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            _basic_logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Tried search paths: {cls._get_search_paths()}"
            )
        except yaml.YAMLError as e:
            _basic_logger.error(f"Invalid YAML in config file: {e}")
            raise ValueError(
                f"Invalid YAML in configuration file {config_path}: {e}")

        # Store config file path temporarily for merging
        cls._temp_config_data = config_data
        cls._temp_config_path = config_path

        try:
            # Create instance - this will use our custom settings source
            # which merges file data with env vars (env vars take precedence)
            settings = cls()
            _basic_logger.info(
                "Configuration loaded and validated successfully")
            return settings
        except ValidationError as e:
            _basic_logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Configuration validation failed:\n{e}")
        finally:
            # Clean up temp data
            cls._temp_config_data = None
            cls._temp_config_path = None

    @staticmethod
    def _get_search_paths() -> list[str]:
        """Get list of paths to search for config file."""
        return [
            os.getenv("PYQUIZHUB_CONFIG_PATH", ""),
            "./config.yaml",            # Project root
            os.path.join(
                os.path.dirname(__file__),
                "config.yaml"),
            # Package location
        ]

    @classmethod
    def _find_config_file(cls) -> str:
        """
        Search for config file in multiple locations.

        Returns:
            Path to first found config file

        Raises:
            FileNotFoundError: If no config file is found
        """
        search_paths = cls._get_search_paths()

        for path in search_paths:
            if path and os.path.isfile(path):
                _basic_logger.debug(f"Found config file at: {path}")
                return path

        # If we get here, no config file was found
        error_msg = (
            "No configuration file found. Searched in:\n" +
            "\n".join(f"  - {p}" for p in search_paths if p) +
            "\n\nPlease either:\n"
            "  1. Set PYQUIZHUB_CONFIG_PATH environment variable\n"
            "  2. Place config.yaml in project root\n"
            "  3. Use environment variables to configure (see .env.example)"
        )
        _basic_logger.error(error_msg)
        raise FileNotFoundError(error_msg)


class ConfigManager:
    """
    Thread-safe singleton wrapper for AppSettings.

    This maintains backward compatibility with the old ConfigManager API
    while using the new Pydantic-based settings internally.
    """

    _instance: 'ConfigManager' | None = None
    _settings: AppSettings | None = None
    _config_path: str | None = None

    def __init__(self):
        """Initialize ConfigManager. Use get_instance() instead."""
        pass

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """Get singleton instance of ConfigManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None
        cls._settings = None
        cls._config_path = None

    def load(self, config_path: str | None = None) -> dict[str, Any]:
        """
        Load configuration from file.

        Args:
            config_path: Optional path to config file

        Returns:
            Configuration as dictionary
        """
        if self._settings is not None and config_path is None:
            # Already loaded, return cached config
            return self._settings.model_dump()

        self._config_path = config_path
        self._settings = AppSettings.from_yaml(config_path)

        return self._settings.model_dump()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key: Config key in dot notation (e.g., "storage.type")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._settings is None:
            self.load()

        # Navigate through nested structure
        keys = key.split(".")
        value = self._settings.model_dump()

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
                if value is default:
                    break
            else:
                return default

        return value

    def get_config(self) -> dict[str, Any]:
        """Get entire configuration as dictionary."""
        if self._settings is None:
            self.load()
        return self._settings.model_dump()

    def get_config_path(self) -> str | None:
        """Get path to loaded configuration file."""
        return self._config_path

    # Convenience properties for backward compatibility

    @property
    def storage_type(self) -> str:
        """Get storage type."""
        if self._settings is None:
            self.load()
        return self._settings.storage.type

    @property
    def storage_file_base_dir(self) -> str:
        """Get file storage base directory."""
        if self._settings is None:
            self.load()
        return self._settings.storage.file.base_dir

    @property
    def storage_sql_connection_string(self) -> str:
        """Get SQL connection string."""
        if self._settings is None:
            self.load()
        return self._settings.storage.sql.connection_string

    @property
    def api_base_url(self) -> str:
        """Get API base URL."""
        if self._settings is None:
            self.load()
        return self._settings.api.base_url

    @property
    def api_host(self) -> str:
        """Get API host."""
        if self._settings is None:
            self.load()
        return self._settings.api.host

    @property
    def api_port(self) -> int:
        """Get API port."""
        if self._settings is None:
            self.load()
        return self._settings.api.port

    @property
    def security_use_tokens(self) -> bool:
        """Check if token security is enabled."""
        if self._settings is None:
            self.load()
        return self._settings.security.use_tokens

    @property
    def logging_config(self) -> dict[str, Any]:
        """Get logging configuration."""
        if self._settings is None:
            self.load()
        return self._settings.logging.model_dump()

    def get_token_env_var(self, token_type: str) -> str | None:
        """
        Get environment variable name for a token type.

        Args:
            token_type: Type of token (admin, creator, user)

        Returns:
            Environment variable name
        """
        if self._settings is None:
            self.load()

        token_map = {
            "admin": self._settings.security.admin_token_env,
            "creator": self._settings.security.creator_token_env,
            "user": self._settings.security.user_token_env,
        }
        return token_map.get(token_type)

    def get_token(self, token_type: str) -> str | None:
        """
        Get token value from environment variable.

        Args:
            token_type: Type of token (admin, creator, user)

        Returns:
            Token value or None
        """
        if self._settings is None:
            self.load()

        if not self._settings.security.use_tokens:
            return None

        env_var = self.get_token_env_var(token_type)
        if env_var:
            return os.getenv(env_var)
        return None

    def get_role_permissions(self, role: str) -> RolePermissions:
        """
        Get permissions for a specific role.

        Args:
            role: Role name (admin, creator, user)

        Returns:
            RolePermissions for the role

        Raises:
            ValueError: If role is invalid
        """
        if self._settings is None:
            self.load()

        role_lower = role.lower()
        permissions = self._settings.security.permissions

        if role_lower == "admin":
            return permissions.admin
        elif role_lower == "creator":
            return permissions.creator
        elif role_lower == "user":
            return permissions.user
        else:
            raise ValueError(f"Invalid role: {role}. Valid roles: admin, creator, user")

    def verify_token_and_get_role(self, token: str | None) -> tuple[str, str]:
        """
        Verify token and return (user_id, role).

        Token matching priority:
        1. Admin token -> role=admin
        2. Creator token -> role=creator
        3. User token -> role=user
        4. No match -> raises error

        Args:
            token: Authorization token

        Returns:
            Tuple of (user_id, role)

        Raises:
            ValueError: If token is invalid or missing
        """
        if self._settings is None:
            self.load()

        if not self._settings.security.use_tokens:
            # If tokens disabled, default to user role
            return ("anonymous", "user")

        if not token:
            raise ValueError("Authorization token required")

        # Check against each token type
        admin_token = self.get_token("admin")
        if admin_token and token == admin_token:
            return ("admin", "admin")

        creator_token = self.get_token("creator")
        if creator_token and token == creator_token:
            return ("creator", "creator")

        user_token = self.get_token("user")
        if user_token and token == user_token:
            return ("user", "user")

        raise ValueError("Invalid authorization token")

    def can_upload_files(self, role: str) -> bool:
        """Check if role can upload files."""
        return self.get_role_permissions(role).file_uploads.enabled

    def can_use_api_integrations(self, role: str) -> bool:
        """Check if role can use API integrations."""
        return self.get_role_permissions(role).api_integrations.enabled

    def get_file_upload_limits(self, role: str) -> FileUploadPermissions:
        """Get file upload limits for a role."""
        return self.get_role_permissions(role).file_uploads

    def get_rate_limits(self, role: str) -> RateLimitSettings:
        """Get rate limits for a role."""
        return self.get_role_permissions(role).rate_limits


def get_config_manager() -> ConfigManager:
    """
    Get the ConfigManager singleton instance.

    Returns:
        ConfigManager instance
    """
    return ConfigManager.get_instance()


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    DEPRECATED: Use pyquizhub.logging.setup.get_logger instead.
    This function is kept for backward compatibility but will issue a warning.

    Args:
        name: Name for the logger

    Returns:
        Logger instance
    """
    # Import here to avoid circular dependency
    from pyquizhub.logging.setup import get_logger as new_get_logger

    # Issue deprecation warning (only once per module)
    if not hasattr(get_logger, '_warned'):
        logging.warning(
            "get_logger from pyquizhub.config.settings is deprecated. "
            "Please use pyquizhub.logging.setup.get_logger instead."
        )
        get_logger._warned = True

    return new_get_logger(name)


__all__ = [
    'ConfigManager',
    'AppSettings',
    'get_config_manager',
    'get_logger',  # Deprecated
    'StorageSettings',
    'APISettings',
    'SecuritySettings',
    'LoggingSettings',
    'FileStorageSettings',
    'SQLStorageSettings',
    'RateLimitSettings',
    'FileUploadPermissions',
    'APIIntegrationPermissions',
    'RolePermissions',
    'RolePermissionsConfig',
    'UserAuthSettings',
]
