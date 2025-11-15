Quiz Format Guide (Version 2.0)
================================

This document defines the quiz JSON format with the new variables system, API integrations, and execution flow.

Overview
--------

A quiz consists of:

1. **Variables** - Type-safe data storage with security tags
2. **Questions** - User interaction points with execution blocks
3. **Transitions** - Flow control between questions
4. **API Integrations** (optional) - External data sources

Each question can have multiple **execution blocks** that run in order:

1. **Variable updates** - Compute new values from existing variables
2. **API calls** - Fetch external data into variables
3. **User interaction** - Display question and collect answer (once per question)

JSON Structure
--------------

.. code-block:: json

    {
        "metadata": {
            "title": "Quiz Title",
            "description": "Quiz description",
            "author": "Author Name",
            "version": "2.0"
        },
        "variables": {
            "variable_name": {
                "type": "integer|float|boolean|string|array",
                "array_item_type": "integer|float|boolean|string",  // Required if type is array
                "mutable_by": ["user", "api", "engine"],
                "tags": ["score", "leaderboard", "user_input", ...],
                "description": "Optional description",
                "constraints": { /* optional validation rules */ }
            }
        },
        "api_integrations": [
            {
                "id": "api_id",
                "method": "GET|POST|PUT|PATCH|DELETE",
                "auth": { "type": "none|bearer|api_key" },
                "prepare_request": {
                    // Optional: For dynamic URLs or request bodies
                    "url_template": "https://api.example.com/{variables.city}/forecast",
                    "required_variables": ["city", "units"],
                    "body_template": {
                        "query": "{variables.search_term}",
                        "limit": "{variables.result_count}"
                    },
                    "headers": {
                        "Content-Type": "application/json"
                    }
                },
                "extract_response": {
                    // Required: Which variables to populate from response
                    "variables": {
                        "temperature": {
                            "path": "current.temperature_2m",
                            "type": "float"
                        },
                        "wind_speed": {
                            "path": "current.wind_speed_10m",
                            "type": "float"
                        }
                    }
                }
            }
        ],
        "questions": [
            {
                "id": 1,
                "execution_blocks": [
                    {
                        "type": "update_variables",
                        "timing": "before_user_interaction",
                        "updates": [
                            {
                                "condition": "true",
                                "variables": {
                                    "computed_value": "other_var * 2"
                                }
                            }
                        ]
                    },
                    {
                        "type": "api_call",
                        "timing": "before_user_interaction",
                        "api_id": "weather",
                        "on_success": "continue",
                        "on_failure": "use_fallbacks"
                    },
                    {
                        "type": "user_interaction",
                        "data": {
                            "type": "multiple_choice|text|integer|float|multiple_select",
                            "text": "Question text with {variables.value} interpolation",
                            "options": [ /* for choice questions */ ]
                        },
                        "store_answer_in": "user_answer"  // Optional: store raw answer
                    },
                    {
                        "type": "update_variables",
                        "timing": "after_user_interaction",
                        "updates": [
                            {
                                "condition": "answer == 'correct'",
                                "variables": {
                                    "score": "score + 10"
                                }
                            }
                        ]
                    }
                ]
            }
        ],
        "transitions": {
            "1": [
                {
                    "expression": "score > 50",
                    "next_question_id": 2
                },
                {
                    "expression": "true",
                    "next_question_id": null
                }
            ]
        }
    }

Variables System
----------------

Required Fields
^^^^^^^^^^^^^^^

* **type** - Data type (integer, float, boolean, string, array)
* **mutable_by** - Who can modify this variable: ["user", "api", "engine"]
* **array_item_type** - Type of items in array (required if type is "array")

Optional Fields
^^^^^^^^^^^^^^^

* **default** - Initial value (auto-generated from type if not provided: 0, 0.0, false, "", [])
* **tags** - Variable classification (see Tags section)
* **description** - Human-readable description
* **constraints** - Validation rules (min_value, max_value, enum, pattern, min_items, max_items, etc.)

**Note**: ``object`` type is NOT allowed for security reasons. Arrays must be homogeneous (all items same type).

Variable Tags
^^^^^^^^^^^^^

**Purpose Tags:**

* ``score`` - Numeric metrics for analytics (auto-tagged as public)
* ``leaderboard`` - THE primary score for ranking (only ONE per quiz, auto-tagged as score+public)
* ``state`` - Quiz state tracking
* ``user_input`` - Value comes from user (auto-tagged as untrusted)
* ``api_data`` - Value comes from API (auto-tagged as sanitized+safe_for_api)
* ``computed`` - Calculated from other variables

**Visibility Tags:**

* ``public`` - Visible in results
* ``private`` - Internal use only (default if no visibility tag)
* ``admin_only`` - Only visible to admins

**Safety Tags** (mostly auto-applied):

* ``safe_for_api`` - Safe to use in API requests (numeric types, enum strings)
* ``sanitized`` - Validated/constrained (API responses, enum strings, numeric with constraints)
* ``untrusted`` - Needs validation before use (user input)

**Special Tags:**

* ``immutable`` - Cannot be changed after initialization (requires mutable_by: [])
* ``temporary`` - Cleared between questions

Security Model
^^^^^^^^^^^^^^

**Type Safety:**

* Numeric types (integer, float, boolean) → automatically ``safe_for_api``
* String with enum constraint → automatically ``safe_for_api`` + ``sanitized``
* Free-text strings → NEVER ``safe_for_api`` (injection risk)
* User input → automatically ``untrusted``
* Numeric user input with constraints → ``untrusted`` + ``sanitized`` (constrained values are safe)

**API Variables:**

Variables with ``source_api`` must:

* Have ``response_path`` defined (how to extract from API response)
* Have "api" in ``mutable_by``
* Are automatically tagged: ``api_data``, ``sanitized``, ``safe_for_api``
* Are type-validated against their declared type
* Can have additional constraints (min_value, max_value) for extra validation

Example Variable Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "variables": {
            "total_score": {
                "type": "integer",
                "mutable_by": ["engine"],
                "tags": ["leaderboard"],
                "description": "Primary score for ranking"
                // default: 0 (auto-generated)
            },
            "user_name": {
                "type": "string",
                "mutable_by": ["user"],
                "tags": ["user_input", "private"],
                "constraints": {
                    "max_length": 50,
                    "pattern": "^[a-zA-Z0-9 ]+$"
                }
            },
            "city_choice": {
                "type": "string",
                "mutable_by": ["user"],
                "tags": ["user_input"],
                "constraints": {
                    "enum": ["berlin", "london", "paris", "tokyo"]
                }
                // This is SAFE for API use because of enum constraint
            },
            "actual_temperature": {
                "type": "float",
                "mutable_by": ["api"],
                "source_api": "weather",
                "response_path": "current.temperature_2m",
                "description": "Current temperature from API",
                "constraints": {
                    "min_value": -100,
                    "max_value": 100
                }
                // Auto-tagged: api_data, sanitized, safe_for_api
            },
            "user_prediction": {
                "type": "float",
                "mutable_by": ["user", "engine"],
                "tags": ["user_input", "public"],
                "constraints": {
                    "min_value": -50,
                    "max_value": 50
                }
                // Numeric with constraints: untrusted + sanitized
            },
            "selected_options": {
                "type": "array",
                "array_item_type": "string",
                "mutable_by": ["user"],
                "tags": ["user_input"],
                "constraints": {
                    "min_items": 1,
                    "max_items": 5,
                    "enum": ["option_a", "option_b", "option_c", "option_d"]
                }
                // Array of strings with enum constraint - safe for API use
            },
            "score_history": {
                "type": "array",
                "array_item_type": "integer",
                "mutable_by": ["engine"],
                "tags": ["private"],
                "constraints": {
                    "max_items": 100
                }
                // Array of integers - numeric types are safe
            }
        }
    }

API Integrations
----------------

API integrations have two main blocks:

1. **prepare_request** (optional) - For dynamic URLs or request bodies
2. **extract_response** (required) - Which variables to populate from response

Simple API Integration (Static URL)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "api_integrations": [
            {
                "id": "weather",
                "method": "GET",
                "url": "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m",
                "auth": {"type": "none"},
                "extract_response": {
                    "variables": {
                        "temperature": {
                            "path": "current.temperature_2m",
                            "type": "float"
                        },
                        "humidity": {
                            "path": "current.relative_humidity_2m",
                            "type": "integer"
                        }
                    }
                }
            }
        ]
    }

Dynamic API Integration (Variable-Based Request)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "api_integrations": [
            {
                "id": "city_weather",
                "method": "GET",
                "auth": {"type": "none"},
                "prepare_request": {
                    "url_template": "https://api.example.com/weather/{variables.city_code}",
                    "required_variables": ["city_code"],
                    "query_params": {
                        "units": "{variables.temperature_units}",
                        "lang": "en"
                    },
                    "headers": {
                        "Accept": "application/json"
                    }
                },
                "extract_response": {
                    "variables": {
                        "temperature": {
                            "path": "main.temp",
                            "type": "float"
                        }
                    }
                }
            }
        ]
    }

POST Request with Body
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "api_integrations": [
            {
                "id": "search_api",
                "method": "POST",
                "url": "https://api.example.com/search",
                "auth": {"type": "bearer", "token": "..."},
                "prepare_request": {
                    "required_variables": ["search_query", "max_results"],
                    "body_template": {
                        "query": "{variables.search_query}",
                        "limit": "{variables.max_results}",
                        "filters": {
                            "type": "article"
                        }
                    },
                    "headers": {
                        "Content-Type": "application/json"
                    }
                },
                "extract_response": {
                    "variables": {
                        "result_count": {
                            "path": "meta.total",
                            "type": "integer"
                        },
                        "top_result_title": {
                            "path": "results[0].title",
                            "type": "string"
                        }
                    }
                }
            }
        ]
    }

API Integration Fields
^^^^^^^^^^^^^^^^^^^^^^

**Required:**

* ``id`` - Unique identifier for this API integration
* ``method`` - HTTP method (GET, POST, PUT, PATCH, DELETE)
* ``extract_response`` - Which variables to populate and how

**Optional:**

* ``url`` - Static URL (use this OR url_template in prepare_request)
* ``auth`` - Authentication configuration
* ``prepare_request`` - For dynamic URLs/bodies (contains url_template, body_template, required_variables)

**prepare_request block** (optional):

* ``url_template`` - URL with {variables.name} placeholders
* ``body_template`` - Request body with {variables.name} placeholders
* ``query_params`` - Query parameters (can use {variables.name})
* ``headers`` - HTTP headers
* ``required_variables`` - List of variable names needed to build request

**extract_response block** (required):

* ``variables`` - Dictionary mapping variable names to extraction configs

  Each extraction config has:

  * ``path`` - JSON path to extract (e.g., "current.temp" or "results[0].title")
  * ``type`` - Expected type (must match variable's declared type)

Security Model for APIs
^^^^^^^^^^^^^^^^^^^^^^^^

**NO direct API access in templates/expressions!**

Old (DANGEROUS):
    ``"text": "Temperature is {api.weather} degrees"``  ← Raw untrusted data!

New (SAFE):
    ``"text": "Temperature is {variables.actual_temperature} degrees"``  ← Type-validated variable!

Process:

1. **prepare_request** (if present):

   a. Check all ``required_variables`` are SAFE for API use
   b. Validate variable types (only safe types allowed in URLs/bodies)
   c. Build URL from template by substituting variables
   d. Build request body from template by substituting variables

2. Execute API call with prepared request

3. **extract_response**:

   a. For each variable in ``extract_response.variables``:

      - Extract value using ``path``
      - Validate against declared ``type``
      - Apply variable constraints if any
      - Store in variable

4. Variables are now available for use in expressions/templates

**Security Guarantees:**

* Only variables declared in ``extract_response`` are populated
* Each extracted value is type-validated
* Variables used in ``prepare_request`` must be SAFE_FOR_API
* Free-text user input CANNOT be used in URLs (injection prevention)
* Only enum-constrained strings or numeric types allowed in API requests

Question Execution Blocks
--------------------------

Each question has an ordered list of ``execution_blocks`` that run sequentially.

Block Types
^^^^^^^^^^^

1. **update_variables** - Update variables based on expressions

   .. code-block:: json

       {
           "type": "update_variables",
           "timing": "before_user_interaction|after_user_interaction",
           "updates": [
               {
                   "condition": "expression",
                   "variables": {
                       "var_name": "expression"
                   }
               }
           ]
       }

2. **api_call** - Call external API

   .. code-block:: json

       {
           "type": "api_call",
           "timing": "before_user_interaction|after_user_interaction",
           "api_id": "weather",
           "on_success": "continue|skip_to_next_question",
           "on_failure": "use_fallbacks|fail_quiz|skip_question"
       }

   This will populate ALL variables with ``source_api: "weather"``

3. **user_interaction** - Display question and collect answer (ONCE per question)

   .. code-block:: json

       {
           "type": "user_interaction",
           "data": {
               "type": "multiple_choice|text|integer|float|multiple_select",
               "text": "Question text with {variables.name}",
               "options": [...]
           },
           "store_answer_in": "optional_variable_name"
       }

Execution Order
^^^^^^^^^^^^^^^

Blocks execute in the order listed. Typical pattern:

1. ``update_variables`` (before) - Prepare computed values
2. ``api_call`` (before) - Fetch external data
3. ``user_interaction`` - Show question, collect answer
4. ``update_variables`` (after) - Update score based on answer

The special variable ``answer`` is available ONLY in ``after_user_interaction`` blocks.

Complete Example
----------------

Weather Prediction Quiz
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: json

    {
        "metadata": {
            "title": "Weather Prediction Quiz",
            "description": "Predict the temperature and see how accurate you are!",
            "author": "PyQuizHub",
            "version": "2.0"
        },
        "variables": {
            "user_prediction": {
                "type": "float",
                "mutable_by": ["user"],
                "tags": ["user_input", "public"],
                "description": "User's temperature prediction",
                "constraints": {
                    "min_value": -50,
                    "max_value": 50
                }
            },
            "actual_temperature": {
                "type": "float",
                "mutable_by": ["api"],
                "source_api": "weather",
                "response_path": "current.temperature_2m",
                "description": "Actual temperature from API",
                "constraints": {
                    "min_value": -100,
                    "max_value": 100
                }
            },
            "accuracy_score": {
                "type": "integer",
                "mutable_by": ["engine"],
                "tags": ["leaderboard"],
                "description": "Primary score for ranking (0-100)",
                "constraints": {
                    "min_value": 0,
                    "max_value": 100
                }
            }
        },
        "api_integrations": [
            {
                "id": "weather",
                "method": "GET",
                "url": "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m",
                "auth": {"type": "none"},
                "extract_response": {
                    "variables": {
                        "actual_temperature": {
                            "path": "current.temperature_2m",
                            "type": "float"
                        }
                    }
                }
            }
        ],
        "questions": [
            {
                "id": 1,
                "execution_blocks": [
                    {
                        "type": "user_interaction",
                        "data": {
                            "type": "float",
                            "text": "What's the current temperature in Berlin? (°C)",
                            "hint": "Think about the current season!"
                        }
                    },
                    {
                        "type": "update_variables",
                        "timing": "after_user_interaction",
                        "updates": [
                            {
                                "condition": "true",
                                "variables": {
                                    "user_prediction": "answer"
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "id": 2,
                "execution_blocks": [
                    {
                        "type": "api_call",
                        "timing": "before_user_interaction",
                        "api_id": "weather",
                        "on_success": "continue",
                        "on_failure": "use_fallbacks"
                    },
                    {
                        "type": "update_variables",
                        "timing": "before_user_interaction",
                        "updates": [
                            {
                                "condition": "abs(user_prediction - actual_temperature) <= 1",
                                "variables": {
                                    "accuracy_score": "100"
                                }
                            },
                            {
                                "condition": "abs(user_prediction - actual_temperature) <= 3",
                                "variables": {
                                    "accuracy_score": "80"
                                }
                            },
                            {
                                "condition": "abs(user_prediction - actual_temperature) <= 5",
                                "variables": {
                                    "accuracy_score": "60"
                                }
                            },
                            {
                                "condition": "true",
                                "variables": {
                                    "accuracy_score": "40"
                                }
                            }
                        ]
                    },
                    {
                        "type": "user_interaction",
                        "data": {
                            "type": "text",
                            "text": "Results:\\n\\nYour prediction: {variables.user_prediction}°C\\nActual: {variables.actual_temperature}°C\\nAccuracy score: {variables.accuracy_score}/100"
                        }
                    }
                ]
            }
        ],
        "transitions": {
            "1": [
                {"expression": "true", "next_question_id": 2}
            ],
            "2": [
                {"expression": "true", "next_question_id": null}
            ]
        }
    }

Validation Levels
-----------------

Basic Validation (Default)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Always performed:

* Valid JSON structure
* Required fields present (type, mutable_by for variables)
* Type validity (valid VariableType, MutableBy values)
* Tag validity (valid VariableTag values)
* Constraint validity
* Expression syntax
* Question flow validity
* ONE leaderboard variable per quiz
* Reserved names (no variable named "answer")
* API variable requirements (source_api requires response_path and mutable_by includes "api")

Advanced Validation (Permission-Aware)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Checks user/creator permissions:

* API call count limits (by creator tier: restricted=5, standard=20, advanced=50, admin=unlimited)
* Domain allowlists (restricted tier: allowlist only)
* Variable usage in APIs (standard tier: query params only; advanced tier: full control)
* User-level restrictions (some users can't access certain features)

Migration from Old Format
--------------------------

Old Format (DEPRECATED):

.. code-block:: json

    {
        "scores": {"score": 0},
        "questions": [{
            "score_updates": [{
                "condition": "answer == 'yes'",
                "update": {"score": "score + 1"}
            }]
        }]
    }

New Format:

.. code-block:: json

    {
        "variables": {
            "score": {
                "type": "integer",
                "mutable_by": ["engine"]
            }
        },
        "questions": [{
            "execution_blocks": [{
                "type": "update_variables",
                "timing": "after_user_interaction",
                "updates": [{
                    "condition": "answer == 'yes'",
                    "variables": {"score": "score + 1"}
                }]
            }]
        }]
    }

Key Changes:

1. ``scores`` → ``variables`` with type declarations
2. ``score_updates`` → ``execution_blocks`` with explicit timing
3. ``update.score`` → ``variables.score``
4. Added ``type`` and ``mutable_by`` (required)
5. API integration moved from ``api_integrations.response_path`` to ``variables[].response_path``

Best Practices
--------------

1. **Use leaderboard tag for primary score** - Only one variable should have this
2. **Tag user input as user_input** - Auto-tags as untrusted for safety checks
3. **Use constraints on user input** - Especially for numeric types and strings
4. **Use enum for string choices** - Makes them safe for API use
5. **Put response_path in variable definition** - Not in API integration
6. **Use execution_blocks timing** - before vs after user interaction
7. **Never access raw API data** - Always through type-validated variables
8. **Give variables descriptive names** - Makes quiz easier to understand

Question Types Reference
------------------------

multiple_choice
    Single selection from options

multiple_select
    Multiple selections allowed (stores as array)

text
    Free text input (auto-tagged as unsafe for API use)

integer
    Whole number input (auto-tagged as safe for API use)

float
    Decimal number input (auto-tagged as safe for API use)

boolean
    True/false or yes/no (auto-tagged as safe for API use)

Key Design Decisions Summary
-----------------------------

**1. No Object Type**
    Object type is NOT supported for security reasons. Use separate typed variables instead.

**2. Homogeneous Arrays Only**
    Arrays must declare ``array_item_type``. All items must be the same type.
    Example: ``["integer", "integer", "integer"]`` ✅
    NOT: ``["integer", "string", "float"]`` ❌

**3. HTTP Methods**
    All standard HTTP methods supported: GET, POST, PUT, PATCH, DELETE

**4. API Structure**
    * ``prepare_request`` - Optional block for dynamic URLs/bodies
    * ``extract_response`` - Required block declaring which variables to populate
    * Variables list in ``extract_response`` is exhaustive (only those variables are populated)

**5. Variable Interpolation**
    * In ``prepare_request``: Use ``{variables.name}`` for safe variable substitution
    * Only SAFE_FOR_API variables allowed (numeric types, enum strings)
    * Free-text user input CANNOT be used in API requests

**6. Response Extraction**
    * Each variable in ``extract_response.variables`` must declare:
      - ``path``: JSON path (supports array notation like ``results[0].title``)
      - ``type``: Must match the variable's declared type
    * Type validation happens before storing
    * Constraints applied after extraction

**7. Required vs Optional**
    Variable required fields: ``type``, ``mutable_by`` (+ ``array_item_type`` if type is array)
    Everything else is optional with reasonable defaults
