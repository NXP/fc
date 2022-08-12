Configuration
=============

Three ``FC`` components require different configurations.

fc-server
---------

**1. fc/fc_server/config/cfg.yaml**

.. code-block:: yaml

  registered_frameworks:
    - lava
    - labgrid

  frameworks_config:
    lava:
      identities: $lava_identity
      priority: 1
      default: true
    labgrid:
      lg_crossbar: ws://$labgrid_crossbar_ip:20408/ws
      priority: 2
      seize: false

  priority_scheduler: true

  api_server:
    port: 8600

  managed_resources:
    $farm_type:
      $device_type:
        - $resource1
        - $resource2

You should replace the parameters with ``$`` symbol:

* ``$lava_identity``: it's a lava concept used by ``lavacli``, refers to `lavacli <https://validation.linaro.org/static/docs/v2/lavacli.html?highlight=lavacli#using-lavacli>`_
* ``$labgrid_crossbar_ip``: it's a labgrid concept used by ``labgrid``, specify `labgrid exporter ip <https://labgrid.readthedocs.io/en/latest/getting_started.html#coordinator>`_ here.
* ``$farm_type``: this will be shown in `fc-client` to distinguish different farm type, you could use any string
* ``$device_type``: this category devices for easy readness, you could use any string
* ``$resource``: list all your resources here

Some optional configure:

* ``priority_scheduler``: priority scheduler only starts to work when it set as `true`
* ``priority``: should specify different priorities for priority scheduler, the lower number will have high priority
* ``seize``: if enable priority scheduler, all frameworks will try to seize the resource from lower priority framework, we could disable that by set `seize` as `false`
* ``default``: the framework will be treated as default framework if specified as `true`

.. note::

  The api server defaults will return ``Resource``, ``Farm``, ``Owner``, ``Comment`` totally four columns to ``fc-client``, but you possible to call external tool to return one more ``Info`` column to client.

  This could be configured as next to add one ``external_info_tool`` to the option ``api_server``:

  .. code-block:: yaml

    api_server:
      external_info_tool: python3 /path/to/fetch_info.py $fc_farm_type $fc_resource

  The ``$fc_farm_type``, ``$fc_resource`` will automatically replaced by real value of resource in FC, your own ``fetch_info.py`` could optional to use them.

**2. fc/fc_server/config/lavacli.yaml**

You should see it in ``$HOME/.config/lavacli.yaml`` if you once add identities for lavacli, see `this <https://validation.linaro.org/static/docs/v2/lavacli.html?highlight=lavacli#using-lavacli>`_

fc-client
---------

You need to define next environment variables before run ``fc-client``.

.. code-block:: bash

  export LG_CROSSBAR=ws://$labgrid_crossbar_ip:20408/ws
  export FC_SERVER=http://$fc_sever_ip:8600

fc-guarder
----------

You should use the same configuration with ``fc-server``.
