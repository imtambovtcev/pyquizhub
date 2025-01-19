Quiz Format Guide
=================

JSON Structure
--------------

Quizzes are defined using JSON files with the following structure:

.. code-block:: json

    {
        "metadata": {
            "title": "Quiz Title",
            "description": "Quiz description",
            "author": "Author Name",
            "version": "1.0"
        },
        "scores": {
            "score_name": 0
        },
        "questions": [
            {
                "id": 1,
                "data": {
                    "type": "multiple_choice",
                    "text": "Question text",
                    "options": [
                        {
                            "value": "yes",
                            "label": "Yes"
                        },
                        {
                            "value": "no", 
                            "label": "No"
                        }
                    ]
                },
                "score_updates": [
                    {
                        "condition": "answer == 'yes'",
                        "update": {
                            "score_name": "score_name + 1"
                        }
                    }
                ]
            }
        ],
        "transitions": {
            "1": [
                {
                    "expression": "true",
                    "next_question_id": null
                }
            ]
        }
    }

Field Descriptions
------------------

metadata
    Quiz metadata including title, description, author and version

scores
    Defines score variables and their initial values

questions
    Array of question objects containing:
    
    * id - Unique question identifier
    * data - Question content and type
    * score_updates - Score update rules based on answers

transitions
    Rules for question flow control using conditions

Question Types
--------------

multiple_choice
    Standard multiple choice with single correct answer

multiple_select
    Multiple correct answers allowed

text
    Free text answer matching

integer
    Numeric answer (whole numbers)

float
    Numeric answer (decimal numbers)

Example Quiz Files
------------------

Simple Multiple Choice
^^^^^^^^^^^^^^^^^^^^^^
.. literalinclude:: ../tests/test_quiz_jsons/test_quiz_multiple_choice.json
   :language: json
   :caption: Multiple Choice Quiz

Text Input
^^^^^^^^^^
.. literalinclude:: ../tests/test_quiz_jsons/test_quiz_text.json
   :language: json
   :caption: Text Input Quiz

Numeric Input
^^^^^^^^^^^^^
.. literalinclude:: ../tests/test_quiz_jsons/test_quiz_integer.json
   :language: json
   :caption: Numeric Input Quiz
