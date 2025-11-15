"""
Variable type system for PyQuizHub.

This module defines the variable type system that replaces the old "scores" system.
It provides strong typing, safety classification, and validation capabilities.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from dataclasses import dataclass, field
from pyquizhub.config.settings import get_logger

logger = get_logger(__name__)


class VariableType(Enum):
    """
    Variable types supported in PyQuizHub.

    Types define the data structure, while tags define purpose and safety.
    """

    # Numeric types
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"

    # String type (safety determined by tags and constraints)
    STRING = "string"

    # Complex type (object type not allowed for security reasons)
    ARRAY = "array"    # JSON array (homogeneous - all items same type)


class VariableTag(Enum):
    """
    Tags classify variables by purpose, visibility, and safety.

    Variables can have multiple tags. Tags are used for:
    - Determining what variables can be used where
    - Public vs private data
    - Security and safety enforcement
    - Analytics and leaderboards
    """

    # === Purpose Tags (what the variable is for) ===

    # Score tag: Numerical metrics for public display/analysis
    # - Must be numeric type (int or float)
    # - Automatically tagged as 'public'
    # - Used for analytics, comparisons
    # - Multiple score variables allowed
    SCORE = "score"

    # Leaderboard tag: THE primary score for leaderboard ranking
    # - Must be numeric type (int or float)
    # - Automatically tagged as 'score' and 'public'
    # - Only ONE variable per quiz can have this tag
    # - This is the single score shown on leaderboards
    LEADERBOARD = "leaderboard"

    # State tag: Internal quiz state management
    # - Not shown in final results
    # - Used for quiz flow control
    STATE = "state"

    # User input tag: Directly from user answers
    # - Automatically tagged as 'untrusted'
    # - Requires sanitization before use in APIs
    USER_INPUT = "user_input"

    # API data tag: From external API responses
    # - Automatically tagged as 'sanitized'
    # - Can be used safely (already validated)
    API_DATA = "api_data"

    # Computed tag: Calculated from other variables
    # - Derived value, not direct input
    COMPUTED = "computed"

    # === Visibility Tags (who can see it) ===

    # Public: Visible in results, leaderboards, analytics
    PUBLIC = "public"

    # Private: Only visible to quiz logic, not in results
    PRIVATE = "private"

    # Admin only: Only administrators can see this
    ADMIN_ONLY = "admin_only"

    # === Safety Tags (automatically applied based on source) ===

    # Safe for API: Can be used in API request construction
    # - Numeric types get this automatically
    # - Strings with enum constraints get this
    # - Literal strings get this
    SAFE_FOR_API = "safe_for_api"

    # Sanitized: Has passed security validation
    SANITIZED = "sanitized"

    # Untrusted: Comes from user, needs careful handling
    UNTRUSTED = "untrusted"

    # === Special Purpose Tags ===

    # Immutable: Cannot be changed after initialization
    IMMUTABLE = "immutable"

    # Temporary: Cleared between questions
    TEMPORARY = "temporary"


class MutableBy(Enum):
    """Who can modify a variable."""
    USER = "user"      # User answers
    API = "api"        # API responses
    ENGINE = "engine"  # Quiz logic / score updates


class FallbackBehavior(Enum):
    """Fallback behavior when API call fails or permission denied."""
    SKIP = "skip"                    # Skip API call, continue quiz
    USE_DEFAULT = "use_default"      # Use default value from variable
    DEGRADE = "degrade"              # Continue with reduced functionality
    FAIL = "fail"                    # Block quiz execution (error message)


class CreatorPermissionTier(Enum):
    """
    Creator permission tiers controlling API access.

    Each tier has increasing levels of control over API integrations.
    """

    # Tier 1: Restricted (default for new users)
    RESTRICTED = "restricted"
    # - Can only use pre-approved API endpoints (allowlist)
    # - Cannot use variables in API URLs
    # - Fixed authentication only (no dynamic auth)
    # - Max 5 API calls per quiz session

    # Tier 2: Standard (verified creators)
    STANDARD = "standard"
    # - Can use variables in query parameters only
    # - Can add path segments after approved base URL
    # - Can use custom headers (validated)
    # - Max 20 API calls per quiz session

    # Tier 3: Advanced (trusted creators)
    ADVANCED = "advanced"
    # - Can construct full URLs with variables (with validation)
    # - Can use custom authentication schemes
    # - Can use POST/PUT requests with body templates
    # - Max 50 API calls per quiz session

    # Tier 4: Admin (platform administrators)
    ADMIN = "admin"
    # - Bypass some validations (still security-checked)
    # - Unlimited API calls
    # - Can use internal APIs


class UserPermissionLevel(Enum):
    """
    User permission levels controlling access to quiz features.

    Different users have different access to API-enabled features.
    """

    # Guest users (not logged in)
    GUEST = "guest"
    # - Cannot trigger API calls
    # - Quiz runs in "safe mode" with fallbacks

    # Basic users (free tier)
    BASIC = "basic"
    # - Can trigger API calls marked as "public_safe"
    # - Limited to 10 API calls per day

    # Premium users (paid)
    PREMIUM = "premium"
    # - Can trigger all API calls in quiz
    # - Normal rate limits apply

    # Restricted users (flagged for abuse)
    RESTRICTED = "restricted"
    # - API calls disabled
    # - Quiz runs with fallbacks only


@dataclass
class VariableConstraints:
    """
    Constraints for variable validation.

    Different constraints apply to different variable types.
    """

    # Numeric constraints
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None

    # String constraints
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern (validated against ReDoS)
    enum: Optional[List[str]] = None  # Allowed values (makes string safe)

    # Array constraints
    min_items: Optional[int] = None
    max_items: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert constraints to dictionary, excluding None values."""
        return {
            k: v for k, v in {
                "min_value": self.min_value,
                "max_value": self.max_value,
                "min_length": self.min_length,
                "max_length": self.max_length,
                "pattern": self.pattern,
                "enum": self.enum,
                "min_items": self.min_items,
                "max_items": self.max_items,
            }.items() if v is not None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VariableConstraints':
        """Create constraints from dictionary."""
        return cls(
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            pattern=data.get("pattern"),
            enum=data.get("enum"),
            min_items=data.get("min_items"),
            max_items=data.get("max_items"),
        )


@dataclass
class FallbackConfig:
    """
    Fallback configuration for API-sourced variables.

    Defines what happens when API call fails or user lacks permission.
    """

    behavior: FallbackBehavior
    default_value: Optional[Any] = None
    reason_message: Optional[str] = None

    # For DEGRADE behavior
    hide_questions: Optional[List[int]] = None
    alternative_flow: Optional[Dict[str, int]] = None  # {"from": 4, "to": 7}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"behavior": self.behavior.value}

        if self.default_value is not None:
            result["default_value"] = self.default_value
        if self.reason_message:
            result["reason_message"] = self.reason_message
        if self.hide_questions:
            result["hide_questions"] = self.hide_questions
        if self.alternative_flow:
            result["alternative_flow"] = self.alternative_flow

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FallbackConfig':
        """Create from dictionary."""
        return cls(
            behavior=FallbackBehavior(data["behavior"]),
            default_value=data.get("default_value"),
            reason_message=data.get("reason_message"),
            hide_questions=data.get("hide_questions"),
            alternative_flow=data.get("alternative_flow"),
        )


@dataclass
class VariableDefinition:
    """
    Complete definition of a quiz variable.

    Uses a tag-based system for flexible classification:
    - Type: data structure (int, float, string, etc.)
    - Tags: purpose, visibility, safety properties
    - Constraints: validation rules
    """

    name: str
    type: VariableType
    default: Any
    mutable_by: List[MutableBy]
    tags: Set[VariableTag] = field(default_factory=set)
    description: Optional[str] = None

    # Array type specification (required for arrays, must be homogeneous)
    array_item_type: Optional[VariableType] = None

    # Security and validation
    constraints: Optional[VariableConstraints] = None

    # Fallback configuration (for API-sourced variables, defined in API
    # integration)
    fallback: Optional[FallbackConfig] = None

    def __post_init__(self):
        """Validate variable definition and auto-apply tags."""
        # Ensure mutable_by is a list of MutableBy enums
        if isinstance(self.mutable_by, list):
            self.mutable_by = [
                MutableBy(m) if isinstance(m, str) else m
                for m in self.mutable_by
            ]

        # Ensure type is VariableType enum
        if isinstance(self.type, str):
            self.type = VariableType(self.type)

        # Convert array_item_type to enum if string
        if self.array_item_type and isinstance(self.array_item_type, str):
            self.array_item_type = VariableType(self.array_item_type)

        # Validate array requirements
        if self.type == VariableType.ARRAY:
            if not self.array_item_type:
                raise ValueError(
                    f"Variable '{self.name}' is type 'array' but missing 'array_item_type'. "
                    f"Arrays must specify the type of items they contain (all items must be same type)."
                )
            # Validate array_item_type is not ARRAY (no nested arrays for
            # security)
            if self.array_item_type == VariableType.ARRAY:
                raise ValueError(
                    f"Variable '{self.name}' has array_item_type='array'. "
                    f"Nested arrays are not supported for security reasons."
                )
        elif self.array_item_type:
            # If array_item_type is specified but type is not array, that's an
            # error
            raise ValueError(
                f"Variable '{
                    self.name}' has array_item_type but type is '{
                    self.type.value}'. " f"Only array variables can have array_item_type.")

        # Convert tags list to set of VariableTag enums
        if isinstance(self.tags, (list, set)):
            self.tags = {
                VariableTag(t) if isinstance(t, str) else t
                for t in self.tags
            }

        # Auto-apply tags based on properties
        self._auto_apply_tags()

        # Validate tag combinations
        self._validate_tags()

    def _auto_apply_tags(self):
        """Automatically apply tags based on variable properties."""

        # LEADERBOARD tag validation and auto-tagging
        if VariableTag.LEADERBOARD in self.tags:
            # Leaderboard variable must be numeric
            if self.type not in (VariableType.INTEGER, VariableType.FLOAT):
                raise ValueError(
                    f"Variable '{
                        self.name}' has 'leaderboard' tag but type is {
                        self.type.value}. " f"Leaderboard variable must be integer or float.")
            # LEADERBOARD automatically implies SCORE and PUBLIC
            self.tags.add(VariableTag.SCORE)
            self.tags.add(VariableTag.PUBLIC)

        # SCORE tag validation and auto-tagging
        if VariableTag.SCORE in self.tags:
            # Scores must be numeric
            if self.type not in (VariableType.INTEGER, VariableType.FLOAT):
                raise ValueError(
                    f"Variable '{
                        self.name}' has 'score' tag but type is {
                        self.type.value}. " f"Scores must be integer or float.")
            # Scores are automatically public
            self.tags.add(VariableTag.PUBLIC)

        # Numeric types are automatically safe for API use
        if self.type in (
                VariableType.INTEGER,
                VariableType.FLOAT,
                VariableType.BOOLEAN):
            self.tags.add(VariableTag.SAFE_FOR_API)

        # Strings with enum constraints are safe for API use
        if self.type == VariableType.STRING:
            if self.constraints and self.constraints.enum:
                self.tags.add(VariableTag.SAFE_FOR_API)
                self.tags.add(VariableTag.SANITIZED)

        # USER_INPUT tag implies UNTRUSTED
        if VariableTag.USER_INPUT in self.tags:
            self.tags.add(VariableTag.UNTRUSTED)
            # Numeric types with min/max constraints are considered sanitized
            if self.type in (VariableType.INTEGER, VariableType.FLOAT):
                if self.constraints and (self.constraints.min_value is not None or
                                         self.constraints.max_value is not None):
                    self.tags.add(VariableTag.SANITIZED)
            # User input strings are NOT safe for API unless they have enum
            # constraint
            elif self.type == VariableType.STRING:
                if not (self.constraints and self.constraints.enum):
                    # Remove SAFE_FOR_API if it was added
                    self.tags.discard(VariableTag.SAFE_FOR_API)

        # API_DATA tag implies SANITIZED and SAFE_FOR_API
        if VariableTag.API_DATA in self.tags:
            self.tags.add(VariableTag.SANITIZED)
            self.tags.add(VariableTag.SAFE_FOR_API)

        # IMMUTABLE tag implies empty mutable_by
        if VariableTag.IMMUTABLE in self.tags:
            if len(self.mutable_by) > 0:
                raise ValueError(
                    f"Variable '{
                        self.name}' has 'immutable' tag but mutable_by is not empty")

        # Default visibility: if no visibility tag, default to PRIVATE
        visibility_tags = {
            VariableTag.PUBLIC,
            VariableTag.PRIVATE,
            VariableTag.ADMIN_ONLY}
        if not self.tags & visibility_tags:
            self.tags.add(VariableTag.PRIVATE)

    def _validate_tags(self):
        """Validate tag combinations for conflicts."""

        # Can't be both PUBLIC and PRIVATE
        if VariableTag.PUBLIC in self.tags and VariableTag.PRIVATE in self.tags:
            raise ValueError(
                f"Variable '{self.name}' cannot be both PUBLIC and PRIVATE"
            )

        # Can't be SAFE_FOR_API and UNTRUSTED (unless sanitized via enum)
        if (VariableTag.SAFE_FOR_API in self.tags and
            VariableTag.UNTRUSTED in self.tags and
                VariableTag.SANITIZED not in self.tags):
            # This is allowed only if there's an enum constraint
            if not (self.constraints and self.constraints.enum):
                raise ValueError(
                    f"Variable '{
                        self.name}' cannot be SAFE_FOR_API and UNTRUSTED without sanitization")

    def is_immutable(self) -> bool:
        """Check if variable is immutable."""
        return VariableTag.IMMUTABLE in self.tags or len(self.mutable_by) == 0

    def is_safe_for_api_use(self) -> bool:
        """
        Check if variable can be safely used in API request construction.

        Returns:
            True if variable has SAFE_FOR_API tag
        """
        return VariableTag.SAFE_FOR_API in self.tags

    def is_score(self) -> bool:
        """Check if variable is a score (for public analysis)."""
        return VariableTag.SCORE in self.tags

    def is_public(self) -> bool:
        """Check if variable is publicly visible."""
        return VariableTag.PUBLIC in self.tags

    def has_tag(self, tag: VariableTag) -> bool:
        """Check if variable has a specific tag."""
        return tag in self.tags

    def can_be_modified_by(self, actor: MutableBy) -> bool:
        """Check if variable can be modified by given actor."""
        if self.is_immutable():
            return False
        return actor in self.mutable_by

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "type": self.type.value,
            "default": self.default,
            "mutable_by": [m.value for m in self.mutable_by],
            "tags": [t.value for t in self.tags],
        }

        if self.array_item_type:
            result["array_item_type"] = self.array_item_type.value
        if self.description:
            result["description"] = self.description
        if self.constraints:
            result["constraints"] = self.constraints.to_dict()
        if self.fallback:
            result["fallback"] = self.fallback.to_dict()

        return result

    @classmethod
    def from_dict(cls,
                  name: str,
                  data: Dict[str,
                             Any]) -> 'VariableDefinition':
        """Create VariableDefinition from dictionary."""
        return cls(
            name=name,
            type=VariableType(
                data["type"]),
            default=data["default"],
            mutable_by=[
                MutableBy(m) for m in data["mutable_by"]],
            tags={
                VariableTag(t) for t in data.get(
                    "tags",
                    [])},
            array_item_type=VariableType(
                data["array_item_type"]) if "array_item_type" in data else None,
            description=data.get("description"),
            constraints=VariableConstraints.from_dict(
                data["constraints"]) if "constraints" in data else None,
            fallback=FallbackConfig.from_dict(
                data["fallback"]) if "fallback" in data else None,
        )


class VariableStore:
    """
    Runtime storage and management of quiz variables.

    Provides type-safe get/set operations with validation.
    """

    def __init__(self, definitions: Dict[str, VariableDefinition]):
        """
        Initialize variable store.

        Args:
            definitions: Dictionary of variable name -> VariableDefinition

        Raises:
            ValueError: If multiple variables have LEADERBOARD tag
        """
        self.definitions = definitions
        self.values: Dict[str, Any] = {}

        # Validate LEADERBOARD tag uniqueness
        leaderboard_vars = [
            name for name, defn in definitions.items()
            if VariableTag.LEADERBOARD in defn.tags
        ]
        if len(leaderboard_vars) > 1:
            raise ValueError(
                f"Only ONE variable can have 'leaderboard' tag. "
                f"Found {len(leaderboard_vars)}: {', '.join(leaderboard_vars)}"
            )

        # Initialize all variables with defaults
        for name, defn in definitions.items():
            self.values[name] = defn.default

        logger.debug(
            f"Initialized variable store with {
                len(definitions)} variables")

    def get(self, name: str) -> Any:
        """
        Get variable value.

        Args:
            name: Variable name

        Returns:
            Variable value

        Raises:
            KeyError: If variable doesn't exist
        """
        if name not in self.definitions:
            raise KeyError(f"Variable '{name}' not defined")

        return self.values[name]

    def set(self, name: str, value: Any, actor: MutableBy) -> None:
        """
        Set variable value with validation.

        Args:
            name: Variable name
            value: New value
            actor: Who is setting the variable (user, api, engine)

        Raises:
            KeyError: If variable doesn't exist
            PermissionError: If actor cannot modify variable
            ValueError: If value fails validation
        """
        if name not in self.definitions:
            raise KeyError(f"Variable '{name}' not defined")

        defn = self.definitions[name]

        # Check mutability permission
        if not defn.can_be_modified_by(actor):
            raise PermissionError(
                f"Actor '{actor.value}' cannot modify variable '{name}'. "
                f"Allowed actors: {[m.value for m in defn.mutable_by]}"
            )

        # Validate value
        validated_value = self._validate_value(name, value, defn)

        # Set value
        self.values[name] = validated_value
        logger.debug(
            f"Set variable '{name}' = {validated_value} (by {
                actor.value})")

    def _validate_value(
            self,
            name: str,
            value: Any,
            defn: VariableDefinition) -> Any:
        """
        Validate value against variable definition.

        Args:
            name: Variable name (for error messages)
            value: Value to validate
            defn: Variable definition

        Returns:
            Validated (possibly coerced) value

        Raises:
            ValueError: If validation fails
        """
        # Type validation and coercion
        if defn.type == VariableType.INTEGER:
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Variable '{name}' expects integer, got {
                        type(value).__name__}")

        elif defn.type == VariableType.FLOAT:
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Variable '{name}' expects float, got {
                        type(value).__name__}")

        elif defn.type == VariableType.BOOLEAN:
            if not isinstance(value, bool):
                # Allow string coercion for booleans
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes')
                else:
                    value = bool(value)

        elif defn.type == VariableType.STRING:
            if not isinstance(value, str):
                value = str(value)

        elif defn.type == VariableType.ARRAY:
            if not isinstance(value, list):
                raise ValueError(
                    f"Variable '{name}' expects array, got {
                        type(value).__name__}")
            # Validate homogeneous array items
            if defn.array_item_type and len(value) > 0:
                self._validate_array_items(name, value, defn.array_item_type)

        # Constraint validation
        if defn.constraints:
            self._validate_constraints(
                name, value, defn.constraints, defn.type)

        return value

    def _validate_array_items(
            self,
            name: str,
            value: list,
            item_type: VariableType) -> None:
        """
        Validate that all array items are of the same type (homogeneous array).

        Args:
            name: Variable name (for error messages)
            value: Array value to validate
            item_type: Expected type of all items

        Raises:
            ValueError: If items are not all the expected type
        """
        for idx, item in enumerate(value):
            # Type check based on item_type
            if item_type == VariableType.INTEGER:
                if not isinstance(item, int) or isinstance(item, bool):
                    raise ValueError(
                        f"Variable '{name}' array item at index {idx} must be integer, got {
                            type(item).__name__}")
            elif item_type == VariableType.FLOAT:
                if not isinstance(
                        item, (int, float)) or isinstance(
                        item, bool):
                    raise ValueError(
                        f"Variable '{name}' array item at index {idx} must be float, got {
                            type(item).__name__}")
            elif item_type == VariableType.BOOLEAN:
                if not isinstance(item, bool):
                    raise ValueError(
                        f"Variable '{name}' array item at index {idx} must be boolean, got {
                            type(item).__name__}")
            elif item_type == VariableType.STRING:
                if not isinstance(item, str):
                    raise ValueError(
                        f"Variable '{name}' array item at index {idx} must be string, got {
                            type(item).__name__}")
            # ARRAY type not allowed as item_type (already validated in
            # __post_init__)

    def _validate_constraints(
        self,
        name: str,
        value: Any,
        constraints: VariableConstraints,
        var_type: VariableType
    ) -> None:
        """
        Validate value against constraints.

        Args:
            name: Variable name (for error messages)
            value: Value to validate
            constraints: Constraints to check
            var_type: Variable type

        Raises:
            ValueError: If constraints violated
        """
        # Numeric constraints
        if var_type in (VariableType.INTEGER, VariableType.FLOAT):
            if constraints.min_value is not None and value < constraints.min_value:
                raise ValueError(
                    f"Variable '{name}' value {value} below minimum {
                        constraints.min_value}")
            if constraints.max_value is not None and value > constraints.max_value:
                raise ValueError(
                    f"Variable '{name}' value {value} above maximum {
                        constraints.max_value}")

        # String constraints
        if var_type == VariableType.STRING:
            if constraints.min_length is not None and len(
                    value) < constraints.min_length:
                raise ValueError(
                    f"Variable '{name}' length {
                        len(value)} below minimum {
                        constraints.min_length}")
            if constraints.max_length is not None and len(
                    value) > constraints.max_length:
                raise ValueError(
                    f"Variable '{name}' length {
                        len(value)} above maximum {
                        constraints.max_length}")

            # Enum validation (whitelist)
            if constraints.enum is not None:
                if value not in constraints.enum:
                    raise ValueError(
                        f"Variable '{name}' value '{value}' not in allowed values: {
                            constraints.enum}")

            # Pattern validation
            if constraints.pattern is not None:
                import re
                # Pattern should already be validated for ReDoS in variable
                # definition
                if not re.match(constraints.pattern, value):
                    raise ValueError(
                        f"Variable '{name}' value '{value}' does not match pattern {
                            constraints.pattern}")

        # Array constraints
        if var_type == VariableType.ARRAY:
            if constraints.min_items is not None and len(
                    value) < constraints.min_items:
                raise ValueError(
                    f"Variable '{name}' has {
                        len(value)} items, minimum {
                        constraints.min_items}")
            if constraints.max_items is not None and len(
                    value) > constraints.max_items:
                raise ValueError(
                    f"Variable '{name}' has {
                        len(value)} items, maximum {
                        constraints.max_items}")

    def get_all(self) -> Dict[str, Any]:
        """Get all variable values."""
        return self.values.copy()

    def is_safe_for_api_use(self, name: str) -> bool:
        """Check if variable is safe for API use."""
        if name not in self.definitions:
            return False
        return self.definitions[name].is_safe_for_api_use()

    def get_by_tag(self, tag: VariableTag) -> Dict[str, Any]:
        """
        Get all variables with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            Dictionary of variable_name -> value for all variables with that tag
        """
        result = {}
        for name, defn in self.definitions.items():
            if defn.has_tag(tag):
                result[name] = self.values[name]
        return result

    def get_scores(self) -> Dict[str, Union[int, float]]:
        """
        Get all score variables (for leaderboards/analytics).

        Returns:
            Dictionary of score_name -> score_value
        """
        return self.get_by_tag(VariableTag.SCORE)

    def get_public_variables(self) -> Dict[str, Any]:
        """
        Get all public variables (for display in results).

        Returns:
            Dictionary of variable_name -> value for public variables
        """
        return self.get_by_tag(VariableTag.PUBLIC)

    def get_leaderboard_score(self) -> Optional[Tuple[str, Union[int, float]]]:
        """
        Get the leaderboard score variable (the primary score for ranking).

        Returns:
            Tuple of (variable_name, score_value) or None if no leaderboard variable
        """
        leaderboard_vars = self.get_by_tag(VariableTag.LEADERBOARD)
        if not leaderboard_vars:
            return None
        # Should only be one due to validation in __init__
        var_name = list(leaderboard_vars.keys())[0]
        return (var_name, leaderboard_vars[var_name])
