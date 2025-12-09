"""
Quiz Requirements Analyzer for PyQuizHub.

Analyzes quiz JSON to detect what permissions/capabilities are required:
- API integrations (external HTTP calls)
- File uploads (user file attachments)
- External URLs in attachments
- Regex patterns in questions

This allows validating quiz requirements against creator permissions
before storing, ensuring creators can only create quizzes that
match their permission level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urlunparse

from pyquizhub.logging.setup import get_logger

logger = get_logger(__name__)


@dataclass
class URLAccessPattern:
    """
    Represents a URL access pattern with fixed and variable parts.

    Examples:
    - "https://api.example.com/v1/data" -> fully fixed
    - "https://api.example.com/v1/{city}" -> fixed base + variable suffix
    - "{variables.api_url}" -> fully dynamic

    The pattern is stored as:
    - fixed_prefix: The part of URL that is always the same
    - has_variable_suffix: Whether there's a variable part after fixed prefix
    - is_fully_dynamic: Whether the entire URL comes from a variable
    """
    original_template: str
    fixed_prefix: str  # e.g., "https://api.example.com/v1/" or full URL if fixed
    has_variable_suffix: bool  # True if there's {variable} after fixed part
    # True if entire URL is a variable like {variables.url}
    is_fully_dynamic: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_template": self.original_template,
            "fixed_prefix": self.fixed_prefix,
            "has_variable_suffix": self.has_variable_suffix,
            "is_fully_dynamic": self.is_fully_dynamic,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "URLAccessPattern":
        return cls(
            original_template=data["original_template"],
            fixed_prefix=data["fixed_prefix"],
            has_variable_suffix=data["has_variable_suffix"],
            is_fully_dynamic=data["is_fully_dynamic"],
        )

    @classmethod
    def parse(cls, url_template: str) -> "URLAccessPattern":
        """
        Parse a URL template into fixed and variable parts.

        Examples:
        - "https://api.com/data" -> fixed_prefix="https://api.com/data", no variable
        - "https://api.com/{city}/weather" -> fixed_prefix="https://api.com/", variable suffix
        - "{variables.dynamic_url}" -> fully dynamic
        """
        if not url_template:
            return cls(
                original_template="",
                fixed_prefix="",
                has_variable_suffix=False,
                is_fully_dynamic=False,
            )

        # Check if entire URL is a variable
        if url_template.startswith("{") and url_template.endswith("}"):
            # Check if it's a single variable reference
            if url_template.count("{") == 1:
                return cls(
                    original_template=url_template,
                    fixed_prefix="",
                    has_variable_suffix=False,
                    is_fully_dynamic=True,
                )

        # Check if URL starts with a variable (dynamic host)
        if url_template.startswith("{"):
            return cls(
                original_template=url_template,
                fixed_prefix="",
                has_variable_suffix=True,
                is_fully_dynamic=True,
            )

        # Find the first variable placeholder
        var_match = re.search(r'\{[^}]+\}', url_template)

        if var_match:
            # Extract fixed prefix (everything before first variable)
            fixed_prefix = url_template[:var_match.start()]
            return cls(
                original_template=url_template,
                fixed_prefix=fixed_prefix,
                has_variable_suffix=True,
                is_fully_dynamic=False,
            )
        else:
            # No variables - fully fixed URL
            return cls(
                original_template=url_template,
                fixed_prefix=url_template,
                has_variable_suffix=False,
                is_fully_dynamic=False,
            )

    def matches_permission(self, allowed_pattern: str) -> bool:
        """
        Check if this URL pattern is allowed by a permission pattern.

        Permission patterns:
        - "*" - allow everything
        - "https://api.example.com/*" - allow anything under this host/path
        - "https://api.example.com/v1/data" - exact match only
        """
        if allowed_pattern == "*":
            return True

        if self.is_fully_dynamic:
            # Fully dynamic URLs need explicit "*" permission
            return allowed_pattern == "*"

        if allowed_pattern.endswith("/*"):
            # Wildcard pattern - check prefix match
            base = allowed_pattern[:-1]  # Remove the *
            return self.fixed_prefix.startswith(base)

        if self.has_variable_suffix:
            # URL has variable suffix - needs wildcard permission
            # Check if fixed_prefix is allowed with wildcard
            return allowed_pattern.endswith(
                "/*") and self.fixed_prefix.startswith(allowed_pattern[:-1])

        # Exact match required
        return self.fixed_prefix == allowed_pattern


@dataclass
class APIRequirement:
    """Represents a required API integration."""
    integration_id: str
    url_pattern: URLAccessPattern  # Parsed URL access pattern
    method: str
    timing: str
    question_id: int | None

    @property
    def host(self) -> str:
        """Extract host from fixed_prefix for backwards compatibility."""
        if self.url_pattern.is_fully_dynamic:
            return "*dynamic*"
        try:
            parsed = urlparse(self.url_pattern.fixed_prefix)
            return parsed.netloc.split(":")[0] if parsed.netloc else ""
        except Exception:
            return ""


@dataclass
class FileUploadRequirement:
    """Represents file upload requirement."""
    question_id: int
    allowed_types: list[str]  # e.g., ["image", "document"]
    required: bool


@dataclass
class AttachmentRequirement:
    """Represents external attachment (image, video, etc.)."""
    question_id: int
    attachment_type: str
    url_pattern: URLAccessPattern  # Parsed URL access pattern


@dataclass
class QuizRequirements:
    """
    Complete requirements manifest for a quiz.

    This is stored alongside the quiz data to enable:
    1. Permission checking at quiz creation time
    2. Runtime permission enforcement
    3. Audit trail of what a quiz can do
    """
    # API Integration requirements
    requires_api_integrations: bool = False
    api_integrations: list[APIRequirement] = field(default_factory=list)
    api_url_patterns: list[URLAccessPattern] = field(
        default_factory=list)  # All API URL patterns

    # File upload requirements
    requires_file_uploads: bool = False
    file_uploads: list[FileUploadRequirement] = field(default_factory=list)
    file_categories_needed: set[str] = field(default_factory=set)

    # Attachment requirements
    has_external_attachments: bool = False
    attachments: list[AttachmentRequirement] = field(default_factory=list)
    attachment_url_patterns: list[URLAccessPattern] = field(
        default_factory=list)  # All attachment URL patterns

    # Other requirements
    uses_regex: bool = False
    max_questions: int = 0
    has_score_updates: bool = False
    has_transitions: bool = False

    @property
    def api_hosts(self) -> set[str]:
        """Get all unique API hosts (for backwards compatibility)."""
        hosts = set()
        for api in self.api_integrations:
            host = api.host
            if host:
                hosts.add(host)
        return hosts

    @property
    def attachment_hosts(self) -> set[str]:
        """Get all unique attachment hosts (for backwards compatibility)."""
        hosts = set()
        for att in self.attachments:
            if not att.url_pattern.is_fully_dynamic:
                try:
                    parsed = urlparse(att.url_pattern.fixed_prefix)
                    if parsed.netloc:
                        hosts.add(parsed.netloc.split(":")[0])
                except Exception:
                    pass
        return hosts

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "requires_api_integrations": self.requires_api_integrations,
            "api_integrations": [
                {
                    "id": api.integration_id,
                    "url_pattern": api.url_pattern.to_dict(),
                    "method": api.method,
                    "timing": api.timing,
                    "question_id": api.question_id,
                }
                for api in self.api_integrations
            ],
            "api_url_patterns": [p.to_dict() for p in self.api_url_patterns],
            "requires_file_uploads": self.requires_file_uploads,
            "file_uploads": [
                {
                    "question_id": fu.question_id,
                    "allowed_types": fu.allowed_types,
                    "required": fu.required,
                }
                for fu in self.file_uploads
            ],
            "file_categories_needed": list(self.file_categories_needed),
            "has_external_attachments": self.has_external_attachments,
            "attachments": [
                {
                    "question_id": att.question_id,
                    "type": att.attachment_type,
                    "url_pattern": att.url_pattern.to_dict(),
                }
                for att in self.attachments
            ],
            "attachment_url_patterns": [p.to_dict() for p in self.attachment_url_patterns],
            "uses_regex": self.uses_regex,
            "max_questions": self.max_questions,
            "has_score_updates": self.has_score_updates,
            "has_transitions": self.has_transitions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuizRequirements":
        """Create from stored dictionary."""
        reqs = cls()
        reqs.requires_api_integrations = data.get(
            "requires_api_integrations", False)
        reqs.requires_file_uploads = data.get("requires_file_uploads", False)
        reqs.file_categories_needed = set(
            data.get("file_categories_needed", []))
        reqs.has_external_attachments = data.get(
            "has_external_attachments", False)
        reqs.uses_regex = data.get("uses_regex", False)
        reqs.max_questions = data.get("max_questions", 0)
        reqs.has_score_updates = data.get("has_score_updates", False)
        reqs.has_transitions = data.get("has_transitions", False)

        # Reconstruct API URL patterns
        for pattern_data in data.get("api_url_patterns", []):
            reqs.api_url_patterns.append(
                URLAccessPattern.from_dict(pattern_data))

        # Reconstruct attachment URL patterns
        for pattern_data in data.get("attachment_url_patterns", []):
            reqs.attachment_url_patterns.append(
                URLAccessPattern.from_dict(pattern_data))

        # Reconstruct complex objects
        for api_data in data.get("api_integrations", []):
            # Handle both old format (hosts list) and new format (url_pattern
            # dict)
            if "url_pattern" in api_data and isinstance(
                    api_data["url_pattern"], dict):
                url_pattern = URLAccessPattern.from_dict(
                    api_data["url_pattern"])
            else:
                # Legacy format - reconstruct from hosts (best effort)
                hosts = api_data.get("hosts", [])
                url_pattern = URLAccessPattern(
                    original_template="",
                    fixed_prefix=f"https://{hosts[0]}/" if hosts else "",
                    has_variable_suffix=False,
                    is_fully_dynamic="*dynamic*" in hosts if hosts else False,
                )
            reqs.api_integrations.append(APIRequirement(
                integration_id=api_data["id"],
                url_pattern=url_pattern,
                method=api_data["method"],
                timing=api_data["timing"],
                question_id=api_data.get("question_id"),
            ))

        for fu_data in data.get("file_uploads", []):
            reqs.file_uploads.append(FileUploadRequirement(
                question_id=fu_data["question_id"],
                allowed_types=fu_data["allowed_types"],
                required=fu_data["required"],
            ))

        for att_data in data.get("attachments", []):
            # Handle both old format and new format
            if "url_pattern" in att_data and isinstance(
                    att_data["url_pattern"], dict):
                url_pattern = URLAccessPattern.from_dict(
                    att_data["url_pattern"])
            else:
                # Legacy format
                old_pattern = att_data.get("url_pattern", "fixed")
                hosts = att_data.get("hosts", [])
                url_pattern = URLAccessPattern(
                    original_template="",
                    fixed_prefix=f"https://{hosts[0]}/" if hosts else "",
                    has_variable_suffix=old_pattern == "variable",
                    is_fully_dynamic=old_pattern == "variable" and not hosts,
                )
            reqs.attachments.append(AttachmentRequirement(
                question_id=att_data["question_id"],
                attachment_type=att_data["type"],
                url_pattern=url_pattern,
            ))

        return reqs


@dataclass
class PermissionCheckResult:
    """Result of checking quiz requirements against permissions."""
    allowed: bool
    missing_permissions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "allowed": self.allowed,
            "missing_permissions": self.missing_permissions,
            "warnings": self.warnings,
        }


class QuizRequirementsAnalyzer:
    """
    Analyzes quiz JSON to determine required permissions.

    Usage:
        analyzer = QuizRequirementsAnalyzer()
        requirements = analyzer.analyze(quiz_data)

        # Check against creator permissions
        result = analyzer.check_permissions(requirements, creator_permissions)
        if not result.allowed:
            raise PermissionError(result.missing_permissions)
    """

    @staticmethod
    def analyze(quiz_data: dict[str, Any]) -> QuizRequirements:
        """
        Analyze quiz data and extract all requirements.

        Args:
            quiz_data: Complete quiz JSON structure

        Returns:
            QuizRequirements with all detected requirements
        """
        reqs = QuizRequirements()

        # Analyze API integrations
        QuizRequirementsAnalyzer._analyze_api_integrations(quiz_data, reqs)

        # Analyze questions for file uploads and attachments
        QuizRequirementsAnalyzer._analyze_questions(quiz_data, reqs)

        # Analyze transitions
        if "transitions" in quiz_data and quiz_data["transitions"]:
            reqs.has_transitions = True

        logger.debug(
            f"Quiz requirements analysis complete: api={
                reqs.requires_api_integrations}, " f"files={
                reqs.requires_file_uploads}, attachments={
                reqs.has_external_attachments}")

        return reqs

    @staticmethod
    def _analyze_api_integrations(
            quiz_data: dict[str, Any], reqs: QuizRequirements) -> None:
        """Extract API integration requirements."""
        api_integrations = quiz_data.get("api_integrations", [])

        if not api_integrations:
            return

        reqs.requires_api_integrations = True

        for api_config in api_integrations:
            # Parse URL template into access pattern
            url_template = api_config.get(
                "prepare_request", {}).get(
                "url_template", "")
            url_pattern = URLAccessPattern.parse(url_template)

            reqs.api_integrations.append(APIRequirement(
                integration_id=api_config.get("id", "unknown"),
                url_pattern=url_pattern,
                method=api_config.get("method", "GET"),
                timing=api_config.get("timing", "before_question"),
                question_id=api_config.get("question_id"),
            ))

            reqs.api_url_patterns.append(url_pattern)

    @staticmethod
    def _analyze_questions(
            quiz_data: dict[str, Any], reqs: QuizRequirements) -> None:
        """Analyze questions for file uploads, attachments, and other features."""
        questions = quiz_data.get("questions", [])
        reqs.max_questions = len(questions)

        for question in questions:
            question_id = question.get("id", 0)
            data = question.get("data", {})
            question_type = data.get("type", "")

            # Check for file upload questions
            if question_type == "file_upload":
                reqs.requires_file_uploads = True
                allowed_types = data.get("allowed_types", ["document"])
                reqs.file_uploads.append(FileUploadRequirement(
                    question_id=question_id,
                    allowed_types=allowed_types,
                    required=data.get("required", True),
                ))
                reqs.file_categories_needed.update(allowed_types)

            # Check for attachments (images, audio, video, etc.)
            attachments = data.get("attachments", [])
            for attachment in attachments:
                att_type = attachment.get("type", "image")
                url = attachment.get("url", "")

                # Parse URL into access pattern
                url_pattern = URLAccessPattern.parse(url)

                reqs.has_external_attachments = True
                reqs.attachments.append(AttachmentRequirement(
                    question_id=question_id,
                    attachment_type=att_type,
                    url_pattern=url_pattern,
                ))
                reqs.attachment_url_patterns.append(url_pattern)

            # Check for regex validation in constraints
            constraints = data.get("constraints", {})
            if constraints.get("pattern"):
                reqs.uses_regex = True

            # Check for score updates
            if question.get("score_updates"):
                reqs.has_score_updates = True

    @staticmethod
    def check_permissions(
        requirements: QuizRequirements,
        role_permissions: "RolePermissions"
    ) -> PermissionCheckResult:
        """
        Check if quiz requirements match the creator's permissions.

        Args:
            requirements: Analyzed quiz requirements
            role_permissions: Creator's role permissions from config

        Returns:
            PermissionCheckResult indicating if creation is allowed
        """
        from pyquizhub.config.settings import RolePermissions

        result = PermissionCheckResult(allowed=True)

        # Check API integration permissions
        if requirements.requires_api_integrations:
            api_perms = role_permissions.api_integrations

            if not api_perms.enabled:
                result.allowed = False
                result.missing_permissions.append(
                    "API integrations are not allowed for your role. "
                    "This quiz requires external API calls."
                )
            else:
                # Check each API URL pattern against allowed patterns
                allowed_patterns = api_perms.allowed_hosts  # Now treated as URL patterns

                for url_pattern in requirements.api_url_patterns:
                    if url_pattern.is_fully_dynamic:
                        # Fully dynamic URLs need "*" permission
                        if "*" not in allowed_patterns:
                            result.warnings.append(
                                f"Quiz uses fully dynamic API URL '{url_pattern.original_template}' - "
                                "cannot verify permissions statically. Requires '*' permission."
                            )
                    elif url_pattern.has_variable_suffix:
                        # URL with variable suffix - check if fixed prefix is
                        # allowed with wildcard
                        pattern_allowed = QuizRequirementsAnalyzer._check_url_pattern_allowed(
                            url_pattern, allowed_patterns)
                        if not pattern_allowed:
                            result.allowed = False
                            result.missing_permissions.append(
                                f"API URL pattern '{url_pattern.fixed_prefix}*' is not allowed. "
                                f"Quiz needs access to: {url_pattern.original_template}"
                            )
                    else:
                        # Fixed URL - check exact match or wildcard
                        pattern_allowed = QuizRequirementsAnalyzer._check_url_pattern_allowed(
                            url_pattern, allowed_patterns)
                        if not pattern_allowed:
                            result.allowed = False
                            result.missing_permissions.append(
                                f"API URL '{url_pattern.fixed_prefix}' is not allowed. "
                                f"Allowed patterns: {allowed_patterns}"
                            )

                # Check request count limit
                if len(
                        requirements.api_integrations) > api_perms.max_requests_per_quiz:
                    result.allowed = False
                    result.missing_permissions.append(
                        f"Quiz has {len(requirements.api_integrations)} API integrations, "
                        f"but your limit is {api_perms.max_requests_per_quiz}"
                    )

        # Check file upload permissions
        if requirements.requires_file_uploads:
            file_perms = role_permissions.file_uploads

            if not file_perms.enabled:
                result.allowed = False
                result.missing_permissions.append(
                    "File uploads are not allowed for your role. "
                    "This quiz requires file upload questions."
                )
            else:
                # Check if all required file categories are allowed
                allowed_categories = set(file_perms.allowed_categories)
                for category in requirements.file_categories_needed:
                    if category not in allowed_categories:
                        result.allowed = False
                        result.missing_permissions.append(
                            f"File category '{category}' is not allowed for your role. " f"Allowed: {
                                list(allowed_categories)}")

        # External attachments - check URL patterns
        if requirements.has_external_attachments:
            dynamic_attachments = [
                p for p in requirements.attachment_url_patterns
                if p.is_fully_dynamic
            ]
            variable_attachments = [
                p for p in requirements.attachment_url_patterns
                if p.has_variable_suffix and not p.is_fully_dynamic
            ]
            fixed_attachments = [
                p for p in requirements.attachment_url_patterns
                if not p.has_variable_suffix and not p.is_fully_dynamic
            ]

            warnings = []
            if dynamic_attachments:
                warnings.append(
                    f"{len(dynamic_attachments)} fully dynamic attachment URLs (runtime determined)"
                )
            if variable_attachments:
                warnings.append(
                    f"{len(variable_attachments)} attachments with variable URL suffixes"
                )
            if fixed_attachments:
                hosts = set()
                for p in fixed_attachments:
                    try:
                        parsed = urlparse(p.fixed_prefix)
                        if parsed.netloc:
                            hosts.add(parsed.netloc)
                    except Exception:
                        pass
                if hosts:
                    warnings.append(
                        f"Fixed attachments from: {
                            ', '.join(hosts)}")

            if warnings:
                result.warnings.append(
                    f"Quiz includes {
                        len(
                            requirements.attachments)} external attachments. " +
                    "; ".join(warnings))

        return result

    @staticmethod
    def _check_url_pattern_allowed(
        url_pattern: URLAccessPattern,
        allowed_patterns: list[str]
    ) -> bool:
        """
        Check if a URL pattern is allowed by the permission patterns.

        Permission patterns can be:
        - "*" - allow everything
        - "localhost" or "127.0.0.1" - localhost access (legacy, converts to http://localhost/*)
        - "https://api.example.com/*" - wildcard for host
        - "https://api.example.com/v1/data" - exact URL
        """
        if "*" in allowed_patterns:
            return True

        for allowed in allowed_patterns:
            # Handle legacy host-only patterns (localhost, 127.0.0.1)
            if allowed in ["localhost", "127.0.0.1"]:
                # Check if URL is localhost
                if url_pattern.fixed_prefix:
                    try:
                        parsed = urlparse(url_pattern.fixed_prefix)
                        if parsed.netloc and parsed.netloc.split(
                                ":")[0] in ["localhost", "127.0.0.1"]:
                            return True
                    except Exception:
                        pass
                continue

            # Handle wildcard patterns
            if allowed.endswith("/*"):
                base = allowed[:-1]  # Remove *
                if url_pattern.fixed_prefix.startswith(base):
                    return True
            elif allowed.endswith("*"):
                base = allowed[:-1]  # Remove *
                if url_pattern.fixed_prefix.startswith(base):
                    return True
            else:
                # Exact match (only for fully fixed URLs)
                if not url_pattern.has_variable_suffix and url_pattern.fixed_prefix == allowed:
                    return True

        return False


__all__ = [
    'URLAccessPattern',
    'QuizRequirements',
    'QuizRequirementsAnalyzer',
    'PermissionCheckResult',
    'APIRequirement',
    'FileUploadRequirement',
    'AttachmentRequirement',
]
