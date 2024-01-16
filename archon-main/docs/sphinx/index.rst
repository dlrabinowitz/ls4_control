
archon's documentation
======================

This is the documentation for the SDSS Python product archon. The current version is |archon_version|. You can install the package by doing

.. code-block:: console

  $ pip install sdss-archon

Development and issue tracking happens at the `GitHub repository <https://github.com/sdss/archon>`__.

Running the actor
-----------------

A simple CLI interface is provided to run the :ref:`actor <archon-actor>`.

.. code-block:: console

  $ archon --help
  Usage: archon [OPTIONS] COMMAND [ARGS]...

  Archon controller

  Options:
    -p, --profile [boss|lvm]  The profile to use. If not provided, infered
                              from the domain name.
    -c, --config FILE         Path to the user configuration file.
    -v, --verbose             Debug mode. Use additional v for more details.
                              [x>=0]
    --help                    Show this message and exit.

  Commands:
    actor*  Runs the actor.

To start the actor in detached (daemon) mode run ``archon actor start``. This is roughly equivalent to the following script ::

  archon_actor = ArchonActor.from_config(config_file)
  await archon_actor.start()
  await archon_actor.run_forever()

Use the flag ``--debug`` with ``archon actor start`` to prevent the process from detaching, which is useful for development and debugging.

A list of available actor commands is described :ref:`here <actor-commands>` and can also be output using the actor command ``help``. The JSONSchema of the actor replies can be consulted :ref:`here <actor-schema>`.

``archon`` is also continuously built as a Docker image. See the :ref:`corresponding section <archon-docker>` for details.

Index
-----

.. toctree::
  :caption: Contents
  :maxdepth: 3

  controller
  actor
  docker

.. toctree::
  :caption: Reference
  :maxdepth: 3

  api
  actor-commands
  actor-schema

.. toctree::
  :caption: Development
  :maxdepth: 2

  Changelog <changelog>
  GitHub Repository <https://github.com/sdss/archon>
  Issues  <https://github.com/sdss/archon/issues>
