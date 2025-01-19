Storage Backends
==============

.. module:: pyquizhub.core.storage

Base Storage Interface
--------------------

.. autoclass:: pyquizhub.core.storage.storage_manager.StorageManager
   :members:
   :special-members: __init__

File System Storage
-----------------

.. autoclass:: pyquizhub.core.storage.file_storage.FileStorageManager
   :members:
   :show-inheritance:

SQL Storage
----------

.. autoclass:: pyquizhub.core.storage.sql_storage.SQLStorageManager
   :members:
   :show-inheritance:

Implementation Examples
---------------------

File System Example
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pyquizhub.core.storage.file import FileStorage
   
   storage = FileStorage("/path/to/storage")
   storage.save_quiz(quiz_data)

SQL Example
^^^^^^^^^^

.. code-block:: python

   from pyquizhub.core.storage.sql import SQLStorage
   
   storage = SQLStorage("sqlite:///path/to/sqlite.db")
   storage.save_quiz(quiz_data)
