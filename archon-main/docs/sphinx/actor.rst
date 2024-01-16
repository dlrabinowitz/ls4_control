.. _archon-actor:

Actor
=====

The actor functionality is implemented as a base `CLU <https://clu.readthedocs.io/en/latest/>`__ actor in `.ArchonBaseActor`. An AMQP version of the actor is available as `.ArchonActor`. It's possible to subclass `.ArchonBaseActor` with other specific actor implementations, for example ::

  from archon.actor import ArchonBaseActor
  from clu.legacy import LegacyActor

  class LegacyArchonActor(ArchonBaseActor, LegacyActor):
      pass

The actor must be instantiated with a list of `.ArchonController` instances in addition to the usual actor parameters. ::

  actor = ArchonActor('archon', [controller], host='localhost', port=5672, version='1.2.3')
  await actor.start()

The controllers are unpacked into a ``controllers`` dictionary keyed by the name of the controller.

Normally the actor is instantiated using the classmethod `~.ArchonBaseActor.from_config` with the path to a configuration file. See the :ref:`Configuration file <archon-actor-configuration>` section for more details. ::

  actor = ArchonActor.from_config(config_file)
  await actor.start()

Running the actor
-----------------

The actor can be run as usual by calling ::

  await actor.run_forever()

A simple CLI interface is provided to run the actor.

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

When the actor starts it will use the fully qualified domain name to determine the profile and actor to load, along with the appropriate configuration. This can be overridden by passing the ``--profile`` flag.

Commands
--------

A set of default actor commands are attached to the actor as ``archon.actor.commands.parser``. The full list of commands can be obtained by running the ``help`` command from the CLU command line ::

  archon help
  01:01:57.454 archon >
  01:01:57.468 archon : {
      "help": [
          "Usage: archon [OPTIONS] COMMAND [ARGS]...",
          "",
          "Options:",
          "  --help  Show this message and exit.",
          "",
          "Commands:",
          "  config      Manages the configuration of the device.",
          "  expose      Exposes the cameras.",
          "  flush       Flushes controllers.",
          "  frame       Interacts with the controller buffer frame.",
          "  get_schema  Returns the schema of the actor as a JSON schema.",
          "  help        Shows the help.",
          "  init        Initialises a controller.",
          "  keyword     Prints human-readable information about a keyword.",
          "  lvm         Commands specific to LVM.",
          "  ping        Pings the actor.",
          "  reconnect   Restarts the socket connection to the controller(s).",
          "  reset       Resets the controllers and discards ongoing exposures.",
          "  status      Reports the status of the controller.",
          "  system      Reports the status of the controller backplane.",
          "  talk        Sends a command to the controller.",
          "  version     Reports the version."
      ]
  }

The command list is also available :ref:`here <actor-commands>`. Information on the usage of each command can be retrieved by passing ``--help`` to a specific command, for example ``expose --help``.

To add a new command you must define it as a CLU ``click`` command. ::

  from archon.actor.commands import parser

  @parser.command()
  async def new_command(command, controllers):
      pass

See the :ref:`CLU documentation <clu:click-parser>` for more details. Note that every parser command receives the `actor command <clu.command.Command>` as the first argument and the dictionary of controllers associated with the actor as the second one.

parallel_controllers
^^^^^^^^^^^^^^^^^^^^

It is sometimes useful to write a command in a way that is executed in parallel and concurrently for all the available Archon controllers. The `.parallel_controllers` decorator simplifies this by allowing to replace the command callback function with a coroutine that will be executed for each controller. ::

  from archon.actor.tools import error_controller, parallel_controllers
  from archon.actor.commands import parser

  @parser.command()
  @parallel_controllers()
  async def status(command, controller):
      """Reports the status of the controller."""

      try:
          status = await controller.get_device_status()
      except ArchonError as ee:
          return error_controller(command, controller, str(ee))

      command.info(
          status={
              "controller": controller.name,
              "status": controller.status.value,
              "status_names": [flag.name for flag in controller.status.get_flags()],
              **status,
          }
      )

      return True

Here the coroutine ``status`` receives the command and a singe controller executes certain code, outputting the status of the controller. We can use the helper `.error_controller` to correctly format the output of an error. `.parallel_controllers` will handle executing this code for each controller attached to the actor. Note that in this case we should not finish or fail the command, just return `True` or `False` respectively. `.parallel_controllers` will finish the command successfully if each one of the controller callbacks returns `True`, or fail it if any of them returns `False`. If a callback returns `False`, all other callbacks are immediately cancelled.

`.parallel_controllers` will check that each controller is connected and ready to receive commands so it's not necessary to do that in the callback. This can be disabled by decorating with ``@parallel_controllers(check=False)``.

Exposing
--------

Exposing the CCDs is accomplish via the ``expose`` actor command. Normally one will issue the ``expose start`` command, which will start the exposure but will not automatically read the detectors. That step happens when ``expose finish`` is called. This division allows the user to execute additional actions between the beginning and end of the integration, for example to command an external shutter. For convenience one can integrate and read at once by calling ``expose start --finish``. See ``expose start --help`` for more options.

The resulting files are saved to the location and file specified in the configuration file. Each CCD in a controller is saved as an independent file. A basic header is always attached to each FITS file, which can be expanded by defining additional keywords in the ``header`` section of the :ref:`configuration <archon-actor-configuration>`.

When finishing the exposure, one can send a JSON-formatted mapping of keyword-values that will be added to the default header. The value for each keyword can be a single value or a list in which the first element is the value and the second the comment for the keyword. ::

  archon expose finish --header '{"KEYWORD1": 1, "KEYWORD2": "Some value"}'
  archon expose finish --header '{"KEYWORD1": [1, "A comment"]}'

Overriding the exposure delegate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Internally the actor uses the `.ExposureDelegate` to handle exposures. Subclasses of `.ArchonBaseActor` will inherit this delegate. The delegate is designed to be modular so that it can be itself subclassed and its behaviour overridden.

One typical case in which we may want to override the delegate is to implement control for an external shutter. The delegate will call `.ExposureDelegate.shutter` at the beginning of the integration and readout, but the default ``shutter`` method simply returns `True`. To change that behaviour we can do ::

  from archon.actor.delegate import ExposureDelegate

  class ShutterDelegate(ExposureDelegate):

      async def shutter(self, open):

          if open is True:
              await shutter_device.open()
          else:
              await shutter_device.close()

And then we set the new delegate as ::

  class MyActor(ArchonActor):
      DELEGATE_CLASS = ShutterDelegate

Two other methods that are useful to override are `~.ExposureDelegate.readout_cotasks` and `~.ExposureDelegate.post_process`. The first is run concurrently with readout and it can be used to run time consuming tasks at that time, for example to read environmental sensor data that will be used for the header. ``readout_cotasks`` does not return anything, so any data must be stored in the instance itself. ::

  class MyDelegate(ExposureDelegate):

      def __init__(self, actor):
          super().__init__(actor)
          self.extra_data = {}

      def reset(self):
          self.extra_data = {}
          return super().reset()

      async def readout_cotasks(self):
          temperature = sensor.read_temperature()
          self.extra_data['temperature'] = temperature

`~.ExposureDelegate.post_process` runs after the buffer has been fetched and receives, for each `controller <.ArchonController>` associated with the actor, the controller instance and the list of FITS HDUs (one for each CCD associated with the controller). The HDUs contain the data read from the buffer for that CCD and the default header. The method must return the controller and HDUs after modifying them. Continuing our example before ::

  class MyDelegate(ExposureDelegate):

      ...

      async def post_process(controller, hdus):
          for hdu in hdus:
              hdu.header['TEMP'] = self.extra_data['temperature']

.. _archon-actor-configuration:

Configuration
-------------

To work properly, the actor requires some knowledge of the controller. This configuration is usually passed to ``from_config()`` when initialising the actor. If the actor is started from the command line, the appropriate configuration file will be selected and loaded.

The following is a sample configuration file with all the possible parameters.

.. literalinclude:: sample-config.yaml
   :language: yaml
