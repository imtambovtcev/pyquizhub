Architecture Overview
===================

Core Components
-------------

Engine
^^^^^^

The core engine handles:

* Quiz validation and processing
* Score calculation
* Session management
* Access control

Storage Backends
^^^^^^^^^^^^^^^

Available storage options:

* File System Storage
* SQL Database Storage
* Custom storage implementations

Access Adapters
^^^^^^^^^^^^^

Interface implementations:

* REST API
* CLI Interface
* Web Interface

Component Interaction
-------------------

.. code-block:: text

    [Access Adapters] -> [Engine] -> [Storage Backend]
                         |
                         v
                    [Access Control]

Access Levels
------------

Admin Access
^^^^^^^^^^
* System configuration
* User management
* Storage management
* Full quiz access

Creator Access
^^^^^^^^^^^^
* Create new quizzes
* Edit own quizzes
* View quiz results
* Generate access tokens

User Access
^^^^^^^^^
* Take quizzes with valid token
* View own results
* Track progress
