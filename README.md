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

__Install:__

* Server:

    ```
    docker-compose up -d
    ```

* Client:

    * Using pip:
    ```
    $ apt-get update
    $ apt-get install -y microcom
    $ pip3 install fc-client
    $ pip3 uninstall -y pyserial
    $ pip3 install https://github.com/labgrid-project/pyserial/archive/v3.4.0.1.zip#egg=pyserial
    ```
    You should export next 2 variables before run client command:
    ```
    export FC_SERVER=$FC_SERVER
    export LG_CROSSBAR=$LG_CROSSBAR
    ```
    * Using docker:
    ```
    docker run -idt -e FC_SERVER=$FC_SERVER -e LG_CROSSBAR=$LG_CROSSBAR --name=fc-client atline/fc-client
    ```

__Quickstart:__

* Configure for FC server:

    - __config/cfg.yaml:__ you could define related parameters including managed resources in this configure

    - __config/lavacli.yaml:__ this is the identity file used by lavacli, which further be used by fc to control lava

* Command for user:

    If you already enable labgrid plugin in `cfg.yaml`, you could use next command to use remote debug feature for development automation:

    ```
    $ fc-client s                                 # get all resource status managed by fc
    $ fc-client -r $resource_name s               # get specified resource status managed by fc
    $ fc-client -r $resource_name l               # lock the resource
    $ fc-client -r $resource_name u               # unlock the resource
    $ labgrid-client -p $resource_name console    # get serial access
    $ labgrid-client -p $resource_name power on   # power on resource
    $ labgrid-client -p $resource_name power off  # power off resource
    ```

