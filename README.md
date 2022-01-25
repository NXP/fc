__Background:__

__FC__ (Framework Coordinator), is a coordinator service among different frameworks.

There are many different test systems in embedded system test community, see [this](https://elinux.org/Test_Systems). They are good at different scenarios, e.g.

* Test automation:

    LAVA, Fuego, autotest, avocado, TI VATF, U-Boot test tool, CI-RT R4D,
Baylibe Lab in a Box......

* Development automation:

    Labgrid......

But, nearly all systems require dedicated control of the board resources, which leads to resource waste when leverage different systems.

This project aims to afford a solution to move boards seamlessly between different systems. Different systems will continue work without aware existence of other systems.

__Principle:__

It works similar to other resource management system like [mesos](http://mesos.apache.org/), but it has low invasion to frameworks.

This means: unlike mesos which you should write your mesos scheduler for your framework & inject it into your framework code, `FC` won't change your framework code, it tries to adapt to your framework.

But still, your framework need next two features:

* Your framework needs to have a job queue which `FC` could monitor.
* Your framework needs to have ways to let `FC` control resource's availability, temporary connect/disconnect from your framework.

Then, `FC` will reasonably assign resource to different frameworks to avoid conflict.

__Supported frameworks:__

`FC` is designed as a plugin system to support different frameworks, it currently supports:

* __LAVA:__ use it for test automation
* __Labgrid:__ use it for development automation

But, it not limits to above two, you could write your own plugins to support other framework.

For more details, please go to [FC Homepage](https://fc.readthedocs.org/).