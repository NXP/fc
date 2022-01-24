Quickstart
==========

.. _installation:

Installation
------------

FC could be installed by ``pip``.

* fc-server

.. code-block:: console

  $ sudo pip3 install fc-server

* fc-client

.. code-block:: console

  $ sudo pip3 install fc-client

* fc-guarder

.. code-block:: console

  $ sudo pip3 install fc-guarder

Additional, you can also use FC using docker, details see :ref:`Run with docker package`.

Run
---

Run with native package
+++++++++++++++++++++++

* fc-server

.. code-block:: console

  $ fc-server

* fc-client

.. code-block:: console

  $ fc-client

* fc-guarder

.. code-block:: console

  $ fc-guarder

.. _Run with docker package:

Run with docker package
+++++++++++++++++++++++

* fc-server

.. code-block:: console

  $ git clone https://github.com/frameworkcoordinator/fc.git
  $ cd fc/docker/fc_server
  $ docker-compose up -d

* fc-client

.. code-block:: console

  $ docker run --rm -it atline/fc-client /bin/bash
  root@08ab13f5f363:~# fc-client

* fc-guarder

.. code-block:: console

  $ git clone https://github.com/frameworkcoordinator/fc.git
  $ cd fc/docker/fc_guarder
  $ docker-compose up -d
