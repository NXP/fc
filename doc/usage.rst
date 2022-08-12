Usage
=====

For ``lava``, usage should be transparent to ``FC``. For ``labgrid``, the only item changed is `board reserve` with ``fc-client``.

The detail usage as next:

.. code-block:: bash

  $ fc-client s                                    # get all resource status managed by fc
  $ fc-client -r $resource_name s                  # get specified resource's status and additional information
  $ fc-client -f $farm_type s                      # get resource's status only within this farm
  $ fc-client -d $device_type s                    # get resource's status and information only belongs to specified device type
  $ fc-client -f $farm_type -d $device_type s      # get resource's status and information only belongs to specified device type and within this farm
  $ fc-client -r $resource_name l                  # lock the resource
  $ fc-client -r $resource_name u                  # unlock the resource
  $ fc-client b                                    # list current bookings
  $ labgrid-client -p $resource_name console       # get serial access
  $ labgrid-client -p $resource_name power cycle   # power restart resource
  $ labgrid-client -p $resource_name power on      # power on resource
  $ labgrid-client -p $resource_name power off     # power off resource

.. note::

   The additional information only be displayed when user specify resource or specify device type.
