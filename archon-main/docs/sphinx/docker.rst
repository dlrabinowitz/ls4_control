.. _archon-docker:

Docker
======

The product is automatically built into a Docker image, which is pushed to the SDSS GitHub Container Registry `ghcr.io/sdss/archon <https://github.com/orgs/sdss/packages/container/package/archon>`__. New commits to the ``main`` branch are tagged as ``latest`` in the image, while git tags are tagged with the same version number. The Dockerfile is linked `here <https://github.com/sdss/archon/blob/main/Dockerfile>`__. The default entrypoint to the container will run the actor.

To run the actor as a Docker container (for production, replace ``latest`` with the desired tag):

.. code-block:: console

  $ docker pull ghcr.io/sdss/archon:latest
  latest: Pulling from ghcr.io/sdss/archon
  5d3b2c2d21bb: Pull complete
  3fc2062ea667: Pull complete
  75adf526d75b: Pull complete
  008b9e4aa9fb: Pull complete
  6e2be73a0b44: Pull complete
  271dfd2e19e9: Pull complete
  7c98efabc49f: Pull complete
  da2e0799db78: Pull complete
  Digest: sha256:a797ebd6dde34098e8ae1e1a26a067a8211192bdc845e9f3fc576074447c2bf4
  Status: Downloaded newer image for ghcr.io/sdss/archon:latest

  $ docker run --name archon --rm --detach --network host ghcr.io/sdss/archon:latest
  32081bdb47b67de65e77d3f1e720da1fc642f650c4441108c4a7f26e131e8f10

The container needs access to the host network to connect to the Archon controller(s) (usually on port 4242) and to the RabbitMQ instance (usually on port 5672). There are different ways to accomplish that (see the documentation for `Bridge networking <https://docs.docker.com/network/bridge/>`__ and `this thread <https://forums.docker.com/t/accessing-host-machine-from-within-docker-container/14248>`__) but the easiest one is to use the `host network <https://docs.docker.com/network/host/>`__ by passing ``--network host`` as we did above. Note that this breaks the isolation of the container in ways that may be unsafe.
