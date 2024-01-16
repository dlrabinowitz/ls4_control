
.. _archon-controller:

Controller
==========

``archon`` provides a `wrapper <.ArchonController>` for the `STA Archon <http://www.sta-inc.net/archon/>`__ controller and exposes the controller features as an `~clu.actor.AMQPActor`. Note that ``archon`` uses `asyncio` throughout the codebase to enable asynchronicity.

`.ArchonController` provides a mid-level interface to the Archon controller and implements the protocol for communicating with the controller. ::

  >>> from archon.controller import ArchonController
  >>> archon = ArchonController('my_controller', '10.7.45.25')
  >>> archon
  <archon.controller.controller.ArchonController at 0x7f5de43d3ee0>

After instantiating `.ArchonController`, it must be started to establish the connection to the controller TCP server. When the controller is started, the parameters are reset, the internal status set to idle, and autoflushing is enabled. ::

  >>> await archon.start()

.. warning::
  ``ArchonController`` will only work with an Archon configuration script that matches the behaviour and parameters it expects. Since there are many ways to implement those features, it will **not** work with any script.

Sending commands
----------------

`~.ArchonController.send_command` allows to send a raw command to the controller, while managing command IDs, message formatting, and reply parsing. The replies from the controller are stored in `.ArchonCommand.replies` as a list of `.ArchonCommandReply`. ::

  >>> cmd = archon.send_command('SYSTEM')
  >>> cmd
  <ArchonCommand (>01SYSTEM, status=ArchonCommandStatus.RUNNING)>
  >>> await cmd
  >>> cmd
  <ArchonCommand (>00SYSTEM, status=ArchonCommandStatus.DONE)>
  >>> cmd.replies
  [<ArchonCommandReply (b'<01BACKPLANE_TYPE=1 BACKPLANE_REV=5 BACKPLANE_VERSION=1.0.1104 BACKPLANE_ID=00003FFF1A9902F6 POWER_ID=0000014A46C4 MOD_PRESENT=FFF MOD1_TYPE=12 MOD1_REV=2 MOD1_VERSION=1.0.1104 MOD1_ID=013C82C81218EAC1 MOD2_TYPE=11 MOD2_REV=0 MOD2_VERSION=1.0.1104 MOD2_ID=013ADF5CE983EED1 MOD3_TYPE=16 MOD3_REV=0 MOD3_VERSION=1.0.1104 MOD3_ID=013F0B0C2B9A098A MOD4_TYPE=9 MOD4_REV=0 MOD4_VERSION=1.0.1104 MOD4_ID=013BDC58A3770501 MOD5_TYPE=2 MOD5_REV=10 MOD5_VERSION=1.0.1104 MOD5_ID=013CA1A7F8456290 MOD6_TYPE=2 MOD6_REV=10 MOD6_VERSION=1.0.1104 MOD6_ID=0135E6C7132CAB69 MOD7_TYPE=2 MOD7_REV=10 MOD7_VERSION=1.0.1104 MOD7_ID=013D20299487C81A MOD8_TYPE=16 MOD8_REV=0 MOD8_VERSION=1.0.1104 MOD8_ID=013C005A12A71540 MOD9_TYPE=8 MOD9_REV=0 MOD9_VERSION=1.0.1104 MOD9_ID=013FC3304C7B3552 MOD10_TYPE=16 MOD10_REV=0 MOD10_VERSION=1.0.1104 MOD10_ID=013613E28D6F9CFA MOD11_TYPE=16 MOD11_REV=0 MOD11_VERSION=1.0.1104 MOD11_ID=013AC627F3458711 MOD12_TYPE=11 MOD12_REV=0 MOD12_VERSION=1.0.1104 MOD12_ID=013F95EDEF775096 \n')>]

`~.ArchonController.send_command` returns an `.ArchonCommand` instance, which is a subclass of `~asyncio.Future`. The command is sent to the controller as soon as ``send_command()`` is called; awaiting the resulting ``ArchonCommand`` will asynchronously block until the command is done (successfully or not). ``ArchonController`` keeps an internal list of all the running commands and associates replies with the corresponding command. Normally an Archon command expects a single reply, at which point the command is marked done. The only exception is the ``FETCH`` command which returns a number of binary replies. ``ArchonController`` handles this case in an efficient way when `~.ArchonController.fetch` is called.

If a command receives a failed reply, the status of the command will be set to `.ArchonCommandStatus.FAILED` ::

  >>> cmd = await archon.send_command('SYSTEM')
  >>> cmd.status
  ArchonCommandStatus.FAILED

All command statuses are instances of `.ArchonCommandStatus`.

Normally a command will wait indefinitely for a reply. It's possible to set a timeout after which the command is failed with status `.ArchonCommandStatus.TIMEDOUT` by passing ``timeout=`` to `~ArchonController.send_command`.

Controller status and configuration
-----------------------------------

`.ArchonController` also provides some mid-level routines to automate complex processes such as `loading <.ArchonController.read_config>` or `saving a configuration file <.ArchonController.write_config>`, retrieving the `controller status <.ArchonController.get_device_status>`, or reading the system status <.ArchonController.get_system>. All these methods are relatively straightforward to use and we refer the user to the API documentation.

`.ArchonController` maintains an internal `status <.ArchonController.status>` for the controller (e.g., whether it's idle, exposing, or reading). This status is not retrieved from the device itself since the Archon firmware doesn't provide a way to query the timing script or parameters.

The status is a bitmask of `.ControllerStatus` bits ::

  >>> archon.status
  <ControllerStatus.READOUT_PENDING|EXPOSING: 12>

Note that certain bits are incompatible and should never appear together (e.g., ``EXPOSING`` and ``IDLE``). The internal status can be updated using `.ArchonController.update_status`, which handles turning off incompatible bits, although it's not recommended to do so.

It's possible to "subscribe" to the controller status via the `~.ArchonController.yield_status` asynchronous generator. This generator will asynchronous yield the status of the device only when the bitmask changes. ::

  async for status in controller.yield_status():
      print(status)

Exposing and reading the CCDs
-----------------------------

To expose the CCDs attached to the controller use the `~.ArchonController.expose` method which accepts an exposure time ::

  await archon.expose(15., readout=True)

The coroutine will turn off autoflushing, start the device integration routine, wait the desired exposure time, and turn off integration. When the integration starts the status bits `~.ControllerStatus.EXPOSING` and `~.ControllerStatus.READOUT_PENDING` are turned on. When the integration is complete the `~.ControllerStatus.EXPOSING` bit changes to `~.ControllerStatus.IDLE`. Note that `.ArchonController.expose` returns immediately after the integration starts and returns a task that can be awaited until the readout finishes. ::

  >>> expose_task = await archon.expose(15., readout=True)
  # The exposure has started but expose() returns immediately.

  >>> await expose_task  # This will block until the exposure and readout ends.

If ``readout=True``, the readout routine will start immediately, at which point the status changes to `~.ControllerStatus.READING`. If ``readout=False`` one must manually call `~.ArchonController.readout` to start the chip readout.

Once readout is complete the buffer can be retrieved by calling `~.ArchonController.fetch`. ``fetch`` will identify the last completed buffer, retrieve its contents, and return a Numpy array with the appropriate number of lines and pixels. ::

  >>> image = await archon.fetch()
  >>> image
  array([[12932, 11918, 12688, ..., 12998, 13486, 14235],
         [11619, 10529, 10613, ..., 10323, 12366, 11106],
         [11807, 10555, 10588, ..., 12059, 11573, 12342],
         ...,
         [ 9736, 10368, 10581, ..., 12534,  3538,  3768],
         [10467, 10653, 10537, ..., 10779,  3717,  3569],
         [11940, 10226, 10294, ..., 10596,  5329,  4796]], dtype=uint16)

Configuration
-------------

`.ArchonController` is relatively agnostic to configuration parameters but some timeout values are defined in ``etc/archon.yml`` and accessible as ::

  >>> from archon import config
  {'archon': {'default_parameters': {}},
   'timeouts': {'controller_connect': 5,
                'expose_timeout': 2,
                'fetching_expected': 5,
                'fetching_max': 10,
                'flushing': 1.2,
                'readout_expected': 40,
                'readout_max': 60,
                'write_config_delay': 0.0001,
                'write_config_timeout': 2}}

Generally these values are reasonable and don't need to be modified.
