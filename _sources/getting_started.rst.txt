Getting Started
=============

Installation
-----------

1. Install using pip:

   .. code-block:: bash

      pip install pyquizhub

2. Or install from source:

   .. code-block:: bash

      git clone https://github.com/yourusername/pyquizhub.git
      cd pyquizhub
      poetry install

Basic Usage
----------

1. Start the engine API with Uvicorn:

   .. code-block:: bash

      poetry run uvicorn pyquizhub.main:app --reload

2. Create a quiz JSON file:

   .. code-block:: json

      {
          "quiz_id": "python_basics",
          "title": "Python Basics Quiz",
          "questions": [
              {
                  "id": "q1",
                  "type": "multiple_choice",
                  "text": "What is Python?",
                  "options": [
                      {"value": "0", "label": "A snake"},
                      {"value": "1", "label": "A programming language"},
                      {"value": "2", "label": "A text editor"}
                  ],
                  "correct_answer": "1"
              }
          ]
      }

3. Add the quiz using CLI:

   .. code-block:: bash

      python pyquizhub/adapters/cli/admin_cli.py add --file quiz.json

4. Generate an access token:

   .. code-block:: bash

      python pyquizhub/adapters/cli/admin_cli.py token --quiz-id <quiz_id>

5. Take the quiz:

   .. code-block:: bash

      python pyquizhub/adapters/cli/user_cli.py --token <your_token>

Web Interface
-----------

1. Start the web server:

   .. code-block:: bash

      python pyquizhub/adapters/web/

2. Open http://localhost:8080 in your browser

3. Enter your access token to start the quiz
