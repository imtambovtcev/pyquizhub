"""
Quiz JSON schema validation module.

This module provides validation capabilities for quiz JSON structures to ensure:
- Required fields are present
- Data types are correct
- Expressions and conditions are valid
- Quiz flow is properly defined
- Variable definitions are valid (new format)
- Backward compatibility with old 'scores' format
"""

import json
from typing import Dict, Any, List, Set
from .safe_evaluator import SafeEvaluator
from .variable_types import (
    VariableDefinition, VariableType, VariableTag, MutableBy,
    VariableConstraints, VariableStore, CreatorPermissionTier
)
from pyquizhub.config.settings import get_logger

logger = get_logger(__name__)


class QuizJSONValidator:
    """
    Validates quiz JSON structure and content.

    This class performs comprehensive validation of quiz definitions including:
    - Schema validation
    - Expression validation
    - Question flow validation
    - Type checking
    """

    @staticmethod
    def validate(
            quiz_data: dict,
            creator_tier: CreatorPermissionTier = CreatorPermissionTier.RESTRICTED) -> dict:
        """
        Validate the JSON structure and contents of a quiz.

        Args:
            quiz_data (dict): The quiz data to validate
            creator_tier (CreatorPermissionTier): The permission tier of the quiz creator.
                Defaults to RESTRICTED for maximum security.

        Returns:
            dict: Validation results containing:
                - errors (list): List of validation errors
                - warnings (list): List of validation warnings
                - permission_errors (list): List of permission violations

        Examples:
            >>> result = QuizJSONValidator.validate(quiz_data)
            >>> if result["errors"]:
            >>>     print("Validation failed:", result["errors"])
            >>> if result["permission_errors"]:
            >>>     print("Permission denied:", result["permission_errors"])
        """
        logger.debug(f"Validating quiz data: {quiz_data}")
        errors = []
        warnings = []
        permission_errors = []

        # Ensure the data is a dictionary
        if not isinstance(quiz_data, dict):
            errors.append("Top-level JSON structure must be a dictionary.")
            return {
                "errors": errors,
                "warnings": warnings,
                "permission_errors": permission_errors}

        # Check for new vs old format
        has_variables = "variables" in quiz_data
        has_scores = "scores" in quiz_data

        # Validate top-level keys (support both formats)
        if has_variables:
            required_keys = {
                "metadata",
                "variables",
                "questions",
                "transitions"}
        else:
            required_keys = {"metadata", "scores", "questions", "transitions"}

        missing_keys = required_keys - quiz_data.keys()
        if missing_keys:
            errors.append(f"Missing required top-level keys: {missing_keys}")
            return {
                "errors": errors,
                "warnings": warnings,
                "permission_errors": permission_errors}

        # Deprecation warning for old format
        if has_scores and not has_variables:
            warnings.append(
                "DEPRECATED: Using old 'scores' format. "
                "Please migrate to new 'variables' format with type definitions and tags. "
                "See documentation for migration guide.")

        # Validate and build variable definitions
        variable_definitions = {}
        default_variables = {}

        if has_variables:
            # NEW FORMAT: Validate variables field
            var_errors, var_warnings, variable_definitions = QuizJSONValidator._validate_variables(
                quiz_data.get("variables", {}))
            errors.extend(var_errors)
            warnings.extend(var_warnings)

            # Build default values for expression validation
            for var_name, var_def in variable_definitions.items():
                default_variables[var_name] = var_def.default

        else:
            # OLD FORMAT: Validate scores field
            if not isinstance(quiz_data["scores"], dict):
                errors.append("The 'scores' field must be a dictionary.")
            elif "answer" in quiz_data["scores"]:
                errors.append(
                    "The 'scores' field must not contain the special variable 'answer'."
                )
            default_variables = quiz_data.get("scores", {}).copy()

        # Validate API integrations structure if present
        if "api_integrations" in quiz_data and quiz_data["api_integrations"]:
            api_errors, api_warnings = QuizJSONValidator._validate_api_integrations(
                quiz_data["api_integrations"], variable_definitions if has_variables else {})
            errors.extend(api_errors)
            warnings.extend(api_warnings)

        # If quiz has API integrations, add mock 'api' variable for validation
        if "api_integrations" in quiz_data and quiz_data["api_integrations"]:
            # Create a mock api object with empty dictionaries for each API
            api_mock = {}
            for api_config in quiz_data["api_integrations"]:
                if "id" in api_config:
                    # Use placeholder values for validation - actual values
                    # will come at runtime
                    api_mock[api_config["id"]] = 0  # Numeric placeholder
            default_variables["api"] = api_mock

        # Validate questions
        question_ids = set()
        questions = quiz_data.get("questions", [])
        if not isinstance(questions, list):
            errors.append("The 'questions' field must be a list.")
            questions = []

        for question in questions:
            if not isinstance(question, dict):
                errors.append(f"Question must be a dictionary: {question}")
                continue

            if not all(key in question for key in ["id", "data"]):
                errors.append(f"Invalid question format: {question}")
                continue

            if question["id"] in question_ids:
                errors.append(f"Duplicate question ID found: {question['id']}")
            question_ids.add(question["id"])

            data = question["data"]
            if not isinstance(data, dict):
                errors.append(f"Question data must be a dictionary: {data}")
                continue

            if not all(key in data for key in ["text", "type"]):
                errors.append(f"Invalid question data format: {data}")
                continue

            current_answer_type = None
            if data["type"] == "multiple_choice":
                current_answer_type = str
                if "options" not in data:
                    errors.append(
                        f"Multiple choice question missing options: {data}")
            elif data["type"] == "multiple_select":
                current_answer_type = list
                if "options" not in data:
                    errors.append(
                        f"Multiple select question missing options: {data}")
            elif data["type"] == "text":
                current_answer_type = str
                if "options" in data:
                    errors.append(
                        f"Question type '{
                            data['type']}' should not have options: {data}")
            elif data["type"] == "integer":
                current_answer_type = int
                if "options" in data:
                    errors.append(
                        f"Question type '{
                            data['type']}' should not have options: {data}")
            elif data["type"] == "float":
                current_answer_type = float
                if "options" in data:
                    errors.append(
                        f"Question type '{
                            data['type']}' should not have options: {data}")
            elif data["type"] == "final_message":
                # final_message type doesn't require an answer
                current_answer_type = type(None)
                if "options" in data:
                    errors.append(
                        f"Question type '{
                            data['type']}' should not have options: {data}")

            if "score_updates" in question:
                score_updates = question["score_updates"]
                if not isinstance(score_updates, list):
                    errors.append(
                        f"Score updates must be a list in question {
                            question['id']}.")
                    continue
                for update in score_updates:
                    if not isinstance(update, dict):
                        errors.append(
                            f"Score update must be a dictionary in question {
                                question['id']}.")
                        continue
                    if not all(
                        key in update for key in [
                            "condition",
                            "update"]):
                        errors.append(
                            f"Invalid score update format in question {
                                question['id']}: {update}")
                        continue
                    # Validate conditions and updates
                    try:

                        allowed_variables = {
                            **default_variables,
                            "answer": current_answer_type()} if current_answer_type else default_variables
                        SafeEvaluator.eval_expr(
                            update["condition"], allowed_variables)
                        for expr in update["update"].values():
                            SafeEvaluator.eval_expr(
                                expr, allowed_variables)
                    except Exception as e:
                        errors.append(
                            f"Invalid score update condition or expression in question {
                                question['id']}: {e}")

        # Validate transitions
        transitions = quiz_data.get("transitions", {})
        if not isinstance(transitions, dict):
            errors.append("The 'transitions' field must be a dictionary.")
            transitions = {}

        for question_id, conditions in transitions.items():
            if not isinstance(conditions, list):
                errors.append(
                    f"Transitions for question {question_id} must be a list.")
                continue

            trivial_condition_found = False
            for idx, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    errors.append(
                        f"Transition condition must be a dictionary in question {question_id}: {condition}")
                    continue

                expression = condition.get("expression", "true")
                next_question_id = condition.get("next_question_id")

                # Validate condition expression
                try:
                    SafeEvaluator.eval_expr(
                        expression, {
                            **default_variables, "answer": current_answer_type()})
                except Exception as e:
                    errors.append(
                        f"Invalid transition expression in question {question_id}: {e}")
                    continue

                # Check for warnings
                if expression == "true":
                    trivial_condition_found = True
                elif trivial_condition_found:
                    warnings.append(
                        f"Non-trivial condition after trivial condition in question {question_id}.")

                # Warn if there's no trivial condition at the end
                if idx == len(conditions) - 1 and expression != "true":
                    warnings.append(
                        f"Last condition in transitions for question {question_id} is not trivial, which may result in unexpected quiz termination.")

                # Validate next_question_id
                if next_question_id is not None and next_question_id not in question_ids:
                    errors.append(
                        f"Invalid next_question_id in question {question_id}: {next_question_id} does not exist.")

        # Validate permissions - check if creator_tier has rights to use
        # requested features
        perm_errors = QuizJSONValidator._validate_permissions(
            quiz_data, creator_tier)
        permission_errors.extend(perm_errors)

        return {
            "errors": errors,
            "warnings": warnings,
            "permission_errors": permission_errors}

    @staticmethod
    def _validate_variables(variables_data: dict) -> tuple:
        """
        Validate the variables field in new format.

        Args:
            variables_data: Dictionary of variable definitions

        Returns:
            Tuple of (errors, warnings, variable_definitions)
        """
        errors = []
        warnings = []
        variable_definitions = {}

        if not isinstance(variables_data, dict):
            errors.append("The 'variables' field must be a dictionary.")
            return (errors, warnings, variable_definitions)

        # Reserved variable names
        if "answer" in variables_data:
            errors.append(
                "The 'variables' field must not contain the special variable 'answer'."
            )

        for var_name, var_config in variables_data.items():
            if not isinstance(var_config, dict):
                errors.append(
                    f"Variable '{var_name}' definition must be a dictionary, got {
                        type(var_config).__name__}")
                continue

            # Validate required fields
            required_fields = {"type", "mutable_by"}
            missing_fields = required_fields - var_config.keys()
            if missing_fields:
                errors.append(
                    f"Variable '{var_name}' missing required fields: {missing_fields}")
                continue

            # Validate type
            var_type = var_config.get("type")
            try:
                if isinstance(var_type, str):
                    var_type_enum = VariableType(var_type)
                else:
                    errors.append(
                        f"Variable '{var_name}' type must be a string, got {
                            type(var_type).__name__}")
                    continue
            except ValueError:
                valid_types = [t.value for t in VariableType]
                errors.append(
                    f"Variable '{var_name}' has invalid type '{var_type}'. "
                    f"Valid types: {valid_types}"
                )
                continue

            # Validate mutable_by
            mutable_by = var_config.get("mutable_by")
            if not isinstance(mutable_by, list):
                errors.append(
                    f"Variable '{var_name}' mutable_by must be a list, got {
                        type(mutable_by).__name__}")
                continue

            try:
                mutable_by_enums = [
                    MutableBy(m) if isinstance(
                        m, str) else m for m in mutable_by]
            except ValueError as e:
                valid_actors = [m.value for m in MutableBy]
                errors.append(
                    f"Variable '{var_name}' has invalid mutable_by value. "
                    f"Valid values: {valid_actors}. Error: {e}"
                )
                continue

            # Validate tags if present
            tags = var_config.get("tags", [])
            if not isinstance(tags, list):
                errors.append(
                    f"Variable '{var_name}' tags must be a list, got {
                        type(tags).__name__}")
                continue

            try:
                tag_enums = {
                    VariableTag(t) if isinstance(
                        t, str) else t for t in tags}
            except ValueError as e:
                valid_tags = [t.value for t in VariableTag]
                errors.append(
                    f"Variable '{var_name}' has invalid tag. "
                    f"Valid tags: {valid_tags}. Error: {e}"
                )
                continue

            # Validate and auto-apply constraints
            constraints = None
            if "constraints" in var_config:
                constraints_data = var_config["constraints"]
                if not isinstance(constraints_data, dict):
                    errors.append(
                        f"Variable '{var_name}' constraints must be a dictionary")
                    continue

                try:
                    constraints = VariableConstraints(**constraints_data)
                except Exception as e:
                    errors.append(
                        f"Variable '{var_name}' has invalid constraints: {e}"
                    )
                    continue

            # Auto-apply default constraints if none provided
            if constraints is None:
                constraints = QuizJSONValidator._auto_apply_constraints(
                    var_type_enum,
                    mutable_by_enums,
                    tag_enums
                )

            # Validate array_item_type for arrays
            array_item_type = None
            if var_type_enum == VariableType.ARRAY:
                if "array_item_type" not in var_config:
                    errors.append(
                        f"Variable '{var_name}' is type 'array' but missing 'array_item_type'. "
                        f"Arrays must specify the type of items (all items must be same type)."
                    )
                    continue

                array_item_type_str = var_config["array_item_type"]
                try:
                    array_item_type = VariableType(array_item_type_str)
                    # No nested arrays
                    if array_item_type == VariableType.ARRAY:
                        errors.append(
                            f"Variable '{var_name}' has array_item_type='array'. "
                            f"Nested arrays are not supported."
                        )
                        continue
                except ValueError:
                    valid_types = [
                        t.value for t in VariableType if t != VariableType.ARRAY]
                    errors.append(
                        f"Variable '{var_name}' has invalid array_item_type '{array_item_type_str}'. "
                        f"Valid types: {valid_types}"
                    )
                    continue
            elif "array_item_type" in var_config:
                errors.append(
                    f"Variable '{var_name}' has array_item_type but type is '{var_type}'. "
                    f"Only array variables can have array_item_type."
                )
                continue

            # Auto-generate default value if not provided
            if "default" not in var_config:
                type_defaults = {
                    VariableType.INTEGER: 0,
                    VariableType.FLOAT: 0.0,
                    VariableType.BOOLEAN: False,
                    VariableType.STRING: "",
                    VariableType.ARRAY: [],
                }
                default_value = type_defaults.get(var_type_enum)
                if default_value is None:
                    errors.append(
                        f"Variable '{var_name}' missing 'default' and no auto-default for type {var_type_enum.value}"
                    )
                    continue
            else:
                default_value = var_config["default"]

            # Try to create VariableDefinition to validate everything together
            try:
                var_def = VariableDefinition(
                    name=var_name,
                    type=var_type_enum,
                    default=default_value,
                    mutable_by=mutable_by_enums,
                    tags=tag_enums,
                    array_item_type=array_item_type,
                    description=var_config.get("description"),
                    constraints=constraints,
                    fallback=None  # TODO: Validate fallback config when needed
                )
                variable_definitions[var_name] = var_def

            except Exception as e:
                errors.append(
                    f"Variable '{var_name}' validation failed: {e}"
                )
                continue

        # Validate that only one variable has LEADERBOARD tag
        if variable_definitions:
            try:
                # This will raise ValueError if multiple leaderboard variables
                VariableStore(variable_definitions)
            except ValueError as e:
                if "leaderboard" in str(e).lower():
                    errors.append(str(e))
                else:
                    # Re-raise if it's a different error
                    raise

        return (errors, warnings, variable_definitions)

    @staticmethod
    def _auto_apply_constraints(
        var_type: VariableType,
        mutable_by: List[MutableBy],
        tags: Set[VariableTag]
    ) -> VariableConstraints:
        """
        Auto-apply reasonable default constraints to prevent abuse.

        Args:
            var_type: Variable type
            mutable_by: Who can modify this variable
            tags: Variable tags

        Returns:
            VariableConstraints with reasonable defaults
        """
        # String constraints - prevent excessively long strings
        if var_type == VariableType.STRING:
            # User input strings need tighter limits
            if MutableBy.USER in mutable_by or VariableTag.USER_INPUT in tags:
                return VariableConstraints(
                    max_length=1000,  # Max 1000 characters for user input
                    min_length=None   # No minimum
                )
            # API or engine strings can be slightly longer
            else:
                return VariableConstraints(
                    max_length=10000,  # Max 10000 characters for API/engine
                    min_length=None
                )

        # Numeric constraints - prevent unreasonably large numbers
        elif var_type == VariableType.INTEGER:
            # Score variables need reasonable bounds
            if VariableTag.SCORE in tags or VariableTag.LEADERBOARD in tags:
                return VariableConstraints(
                    min_value=-1_000_000_000,  # -1 billion
                    max_value=1_000_000_000    # +1 billion
                )
            # Other integers
            else:
                return VariableConstraints(
                    min_value=-9_223_372_036_854_775_808,  # Min 64-bit signed int
                    max_value=9_223_372_036_854_775_807    # Max 64-bit signed int
                )

        elif var_type == VariableType.FLOAT:
            # Score variables need reasonable bounds
            if VariableTag.SCORE in tags or VariableTag.LEADERBOARD in tags:
                return VariableConstraints(
                    min_value=-1_000_000_000.0,  # -1 billion
                    max_value=1_000_000_000.0    # +1 billion
                )
            # Other floats
            else:
                return VariableConstraints(
                    min_value=-1.7976931348623157e+308,  # Min 64-bit float
                    max_value=1.7976931348623157e+308    # Max 64-bit float
                )

        # Array constraints - prevent excessively large arrays
        elif var_type == VariableType.ARRAY:
            # User input arrays need tighter limits
            if MutableBy.USER in mutable_by or VariableTag.USER_INPUT in tags:
                return VariableConstraints(
                    max_items=100,   # Max 100 items for user input
                    min_items=None   # No minimum
                )
            # API or engine arrays can be larger
            else:
                return VariableConstraints(
                    max_items=10000,  # Max 10000 items for API/engine
                    min_items=None
                )

        # Boolean has no numeric constraints
        else:
            return VariableConstraints()

    @staticmethod
    def _validate_api_integrations(
            api_integrations: list,
            variable_definitions: dict) -> tuple:
        """
        Validate the api_integrations structure.

        Args:
            api_integrations: List of API integration configurations
            variable_definitions: Dictionary of variable definitions to check references

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        if not isinstance(api_integrations, list):
            errors.append("The 'api_integrations' field must be a list.")
            return (errors, warnings)

        api_ids = set()

        for idx, api_config in enumerate(api_integrations):
            if not isinstance(api_config, dict):
                errors.append(
                    f"API integration at index {idx} must be a dictionary.")
                continue

            # Validate required fields
            api_id = api_config.get("id")
            if not api_id:
                errors.append(
                    f"API integration at index {idx} missing required 'id' field.")
                continue

            # Check for duplicate API IDs
            if api_id in api_ids:
                errors.append(f"Duplicate API integration ID: '{api_id}'")
            api_ids.add(api_id)

            # Validate HTTP method
            method = api_config.get("method", "GET").upper()
            valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
            if method not in valid_methods:
                errors.append(
                    f"API '{api_id}': Invalid HTTP method '{method}'. "
                    f"Must be one of: {valid_methods}"
                )

            # Validate that either 'url' or 'prepare_request' is present
            has_url = "url" in api_config
            has_prepare_request = "prepare_request" in api_config

            if not has_url and not has_prepare_request:
                errors.append(
                    f"API '{api_id}': Must have either 'url' (fixed URL) or "
                    f"'prepare_request' (dynamic URL) field."
                )
            elif has_url and has_prepare_request:
                errors.append(
                    f"API '{api_id}': Cannot have both 'url' and 'prepare_request'. "
                    f"Use 'url' for fixed URLs or 'prepare_request' for dynamic URLs."
                )

            # Validate prepare_request structure if present
            if has_prepare_request:
                prepare_request = api_config["prepare_request"]
                if not isinstance(prepare_request, dict):
                    errors.append(
                        f"API '{api_id}': 'prepare_request' must be a dictionary.")
                else:
                    # Validate url_template
                    if "url_template" not in prepare_request:
                        errors.append(
                            f"API '{api_id}': 'prepare_request' must contain 'url_template' field.")

                    # Validate body_template if present (for POST/PUT/PATCH)
                    if "body_template" in prepare_request:
                        if method not in ["POST", "PUT", "PATCH"]:
                            warnings.append(
                                f"API '{api_id}': 'body_template' specified but method is {method}. "
                                f"Body templates are typically used with POST, PUT, or PATCH."
                            )

            # Validate extract_response structure if present
            if "extract_response" in api_config:
                extract_response = api_config["extract_response"]
                if not isinstance(extract_response, dict):
                    errors.append(
                        f"API '{api_id}': 'extract_response' must be a dictionary.")
                else:
                    # extract_response should have a 'variables' key with
                    # nested structure
                    if "variables" not in extract_response:
                        errors.append(
                            f"API '{api_id}': 'extract_response' must contain 'variables' field.")
                    else:
                        variables_config = extract_response["variables"]
                        if not isinstance(variables_config, dict):
                            errors.append(
                                f"API '{api_id}': 'extract_response.variables' must be a dictionary.")
                        else:
                            # Each variable should have path and type
                            for var_name, extraction_config in variables_config.items():
                                if not isinstance(extraction_config, dict):
                                    errors.append(
                                        f"API '{api_id}': extract_response.variables['{var_name}'] must be a dictionary.")
                                    continue

                                # Check for required fields in extraction
                                # config
                                if "path" not in extraction_config:
                                    errors.append(
                                        f"API '{api_id}': extract_response.variables['{var_name}'] must have 'path' field.")
                                if "type" not in extraction_config:
                                    errors.append(
                                        f"API '{api_id}': extract_response.variables['{var_name}'] must have 'type' field.")

                                # Check if variable exists in variable
                                # definitions
                                if var_name not in variable_definitions:
                                    warnings.append(
                                        f"API '{api_id}': extract_response references variable '{var_name}' "
                                        f"which is not defined in 'variables'. Ensure this variable is defined."
                                    )

            # Validate authentication structure if present
            if "authentication" in api_config:
                auth = api_config["authentication"]
                if not isinstance(auth, dict):
                    errors.append(
                        f"API '{api_id}': 'authentication' must be a dictionary.")
                else:
                    auth_type = auth.get("type")
                    if not auth_type:
                        errors.append(
                            f"API '{api_id}': 'authentication' must have 'type' field.")

        return (errors, warnings)

    @staticmethod
    def _validate_permissions(
            quiz_data: dict,
            creator_tier: CreatorPermissionTier) -> List[str]:
        """
        Validate that the creator's permission tier allows the features used in the quiz.

        This method is permission-tier aware but user-agnostic. It checks if the given
        permission tier has rights to use the features requested in the quiz JSON.

        Args:
            quiz_data: The quiz JSON data
            creator_tier: The permission tier of the creator

        Returns:
            List of permission error messages (empty if all permissions are satisfied)
        """
        permission_errors = []

        # Get API integrations if present
        api_integrations = quiz_data.get("api_integrations", [])

        if not api_integrations:
            # No API integrations, no permission checks needed
            return permission_errors

        # Check API integration count limits
        api_count = len(api_integrations)
        max_apis = {
            CreatorPermissionTier.RESTRICTED: 5,
            CreatorPermissionTier.STANDARD: 20,
            CreatorPermissionTier.ADVANCED: 50,
            CreatorPermissionTier.ADMIN: float('inf')
        }

        if api_count > max_apis.get(creator_tier, 0):
            permission_errors.append(
                f"Permission denied: {creator_tier.value} tier allows max {max_apis[creator_tier]} "
                f"API integrations, but quiz has {api_count}. Upgrade to a higher tier."
            )

        # Validate each API integration
        for idx, api_config in enumerate(api_integrations):
            api_id = api_config.get("id", f"api_{idx}")

            # Check HTTP method permissions
            method = api_config.get("method", "GET").upper()

            if creator_tier == CreatorPermissionTier.RESTRICTED:
                if method != "GET":
                    permission_errors.append(
                        f"Permission denied: API '{api_id}' uses {method} method. "
                        f"RESTRICTED tier only allows GET requests. Upgrade to ADVANCED tier."
                    )
            elif creator_tier == CreatorPermissionTier.STANDARD:
                if method != "GET":
                    permission_errors.append(
                        f"Permission denied: API '{api_id}' uses {method} method. "
                        f"STANDARD tier only allows GET requests. Upgrade to ADVANCED tier."
                    )

            # Check URL template permissions (dynamic URLs)
            # In the new format, url_template is inside prepare_request block
            prepare_request = api_config.get("prepare_request", {})
            has_url_template = "url_template" in prepare_request
            has_fixed_url = "url" in api_config

            if has_url_template:
                if creator_tier == CreatorPermissionTier.RESTRICTED:
                    permission_errors.append(
                        f"Permission denied: API '{api_id}' uses dynamic URL template (url_template). "
                        f"RESTRICTED tier only allows fixed URLs. Use 'url' field or upgrade to ADVANCED tier."
                    )
                elif creator_tier == CreatorPermissionTier.STANDARD:
                    permission_errors.append(
                        f"Permission denied: API '{api_id}' uses dynamic URL template (url_template). "
                        f"STANDARD tier only allows variables in query parameters. Upgrade to ADVANCED tier."
                    )

            # STANDARD tier can use variables in query params with fixed base
            # URL
            if creator_tier == CreatorPermissionTier.STANDARD and has_fixed_url:
                # Check if query parameters contain variables (this is allowed for STANDARD)
                # The actual URL should be fixed, only query params can have
                # variables
                pass  # This is allowed

            # Check request body permissions (for POST/PUT)
            # In the new format, body_template is inside prepare_request block
            has_body_template = "body_template" in prepare_request
            if has_body_template:
                if creator_tier in [
                        CreatorPermissionTier.RESTRICTED,
                        CreatorPermissionTier.STANDARD]:
                    permission_errors.append(
                        f"Permission denied: API '{api_id}' uses request body template. "
                        f"Only ADVANCED tier and above can use body templates. Upgrade required."
                    )

            # Check custom authentication
            auth_config = api_config.get("authentication", {})
            if auth_config:
                auth_type = auth_config.get("type", "")

                if creator_tier == CreatorPermissionTier.RESTRICTED:
                    # Restricted can only use pre-configured/fixed auth
                    if auth_type not in ["none", "fixed"]:
                        permission_errors.append(
                            f"Permission denied: API '{api_id}' uses '{auth_type}' authentication. "
                            f"RESTRICTED tier only allows fixed authentication. Upgrade required."
                        )

                # Custom auth schemes require ADVANCED
                if auth_type in [
                    "custom",
                        "dynamic"] and creator_tier != CreatorPermissionTier.ADVANCED and creator_tier != CreatorPermissionTier.ADMIN:
                    permission_errors.append(
                        f"Permission denied: API '{api_id}' uses custom authentication scheme. "
                        f"Only ADVANCED tier and above can use custom auth. Upgrade required."
                    )

        return permission_errors
