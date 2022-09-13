Overview
========

Principle
---------

When multiple frameworks try to access the same DUT, there are definitely conflicts there.
To overcome that, we should assure only <=1 framework could get the access of DUT at the same time.

Basic
^^^^^

  .. image:: images/principle.svg

As mentioned in above diagram, ``FC`` will use different frameworks' interface to disconnect all frameworks' access to DUT by default.
Then, ``FC`` will monitor the job queue of different frameworks, if find some framework's job pending on any resource,
``FC`` will connect the resource again to that framework. With that way, no conflict will be occured.

Advanced
^^^^^^^^

There are two advanced features here:

* **default framework**

  ``FC`` allow admin to configure a default framework. For that default framework, ``FC`` will not disconnect its link to DUT defaultly.
  The DUT will be disconnected from default framework only if other framework try to access that resource, this will be automatically handled by ``FC`` coordinator.

  This is useful when some framework is treated as primary framework, then this feature could improve the schedule efficiency of primary framework.
  By default, all frameworks will be treated equally.

  .. note::
    only one framework could be configured as default framework, otherwise there will be conflict.

* **resource seize**

  ``FC`` support framework priority, that means if a resource pending on a high priority framework due to an occupation of a low priority framework.
  The ``FC`` will force cancel the occupation of low priority framework to let high priority framework to seize the resource.

  This is useful when some framework takes critical task while other framework takes non-important task.
  By default, ``FC`` will use fair scheduler.

Architecture
------------

  .. image:: images/architecture.svg

See above diagram, ``FC`` has three main components inside, ``fc-server``, ``fc-client`` and ``fc-guarder``:

1. fc-server
^^^^^^^^^^^^

  ``fc-server`` is the main program to coordinate different frameworks.

  * *api server:*

    There is an API server located on port 8600, it afford ``REST`` api for ``fc-client`` & ``fc-guarder``.

  * *coordinator:*

    The main component to schedule different frameworks.

  * *plugins:*

    * lava:

      It will control resource by switch resource status between "GOOD" & "MAINTENANCE".

    * labgrid:

      It will control resource by inject system level labgrid reservation.

1. fc-client
^^^^^^^^^^^^

  ``fc-client`` is the client program to query resource information from ``fc-server``, meanwhile, it could help to reserve boards.

3. fc-guarder
^^^^^^^^^^^^^

  ``fc-guarder`` is the guard program to monitor ``fc-server``, if ``fc-server`` down for any reasons, the ``fc-guarder`` will online all lava devices to make resources still could be used by LAVA.

FlowChart
---------

Next is the primary flowchart of fc:

  .. image:: images/flowchart.svg
