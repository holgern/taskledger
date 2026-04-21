Usage
=====

Installation
------------

Install the package in editable mode during development:

.. code-block:: bash

   python -m pip install -e .
   python -m pip install -e ".[dev]"

Initialize project state
------------------------

Create the `.taskledger/` state directory in the current workspace:

.. code-block:: bash

   taskledger init

Work items
----------

Create, list, inspect, and move work items through their lifecycle:

.. code-block:: bash

   taskledger item create parser-fix --text "Repair parser handling."
   taskledger item list
   taskledger item show item-0001
   taskledger item approve item-0001
   taskledger item close item-0001

Memories
--------

Memories hold durable textual state such as analysis notes, plans, or validation output.

.. code-block:: bash

   taskledger memory create "Failing tests" --text "pytest output"
   taskledger memory list
   taskledger memory show failing-tests
   taskledger memory append failing-tests --text "More evidence"

Repositories and search
-----------------------

Register repositories so taskledger can search them and inspect dependencies.

.. code-block:: bash

   taskledger repo add core --path /path/to/repo --role both
   taskledger repo list
   taskledger search "parse error"
   taskledger grep "def create_"
   taskledger symbols "ProjectWorkItem"
   taskledger deps core package.module

Project-level commands
----------------------

Use the top-level commands to inspect overall state:

.. code-block:: bash

   taskledger status
   taskledger board
   taskledger next
   taskledger doctor
   taskledger report

Testing
-------

Run the pytest suite from the repository root:

.. code-block:: bash

   pytest -q

Documentation build
-------------------

Build the Sphinx docs locally:

.. code-block:: bash

   python -m pip install sphinx sphinx-rtd-theme
   sphinx-build -b html docs docs/_build/html

