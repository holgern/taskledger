Multi-repo workflows
====================

``runtildone`` supports projects where the code you need to read and the code
you need to modify live in different repositories.

Why this exists
---------------

Common cases:

* upstream source in one repo, local customization in another
* read-only vendor repo plus writable application repo
* framework repo plus extension/addons repo

Setup
-----

Register each repo once:

.. code-block:: bash

   taskledger init
   taskledger repo add core --path ../odoo --kind odoo --role read
   taskledger repo add addons --path ../custom-addons --kind custom --role write
   taskledger repo set-default addons

Read/write split run
--------------------

Read files from one repo and execute in another:

.. code-block:: bash

   runtildone --harness codex project run \
      --repo addons \
      --file core:addons/sale/models/sale_order.py \
      --profile multi-repo-implementation \
      --prompt "implement the fix in the writable repo"

If the work item already has ``--target-repo`` metadata or a default execution repo is
configured, that target is selected automatically and shown in previews. Use
``--run-in-repo`` to override it explicitly.

Saved context version
---------------------

You can bundle the cross-repo sources once and reuse them:

.. code-block:: bash

   taskledger context save sale-debug \
     --file core:addons/sale/models/sale_order.py \
     --file addons/custom_sale/models/sale_order.py
   taskengine context run sale-debug \
      --run-in-repo addons \
      --profile multi-repo-implementation \
      --prompt "apply the implementation"

Doctoring and review
--------------------

Use these commands to keep the setup healthy:

.. code-block:: bash

   taskledger repo doctor
   taskledger status
   taskledger runs list --json

Mental model
------------

* ``--file repo:path`` selects source material from a registered repo.
* ``--repo`` associates the run with a project repo for metadata and history.
   * ``--run-in-repo`` changes the actual execution directory.
   * ``taskledger repo set-default`` picks the fallback writable repo when the run does
     not already imply one.
   * read-only repos may provide context, but they are rejected as execution targets.
* project runs still write artifacts under ``.taskledger/runs/``.
