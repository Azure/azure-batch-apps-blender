#-------------------------------------------------------------------------
#
# Azure Batch Blender Addon
#
# Copyright (c) Microsoft Corporation.  All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the ""Software""), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#--------------------------------------------------------------------------

import datetime
import threading
import os

import bpy

from batched_blender.utils import BatchOps, BatchUtils
from batched_blender.ui import ui_pools
from batched_blender.props import props_pools

from azure.batch import models


class BatchPools(object):
    """Manager for the display and creation of Batch pools."""

    pages = ["POOLS", "CREATE"]

    def __init__(self, manager):
        self.batch = manager
        self.ui = self._register_ui()
        props_pools.register_props()
        self._register_ops()

    def _register_ops(self):
        """Registers each pool operator with a batch_pools prefix.
        Page operators:
            - "page": Open the pool monitoring view and load pool information.
            - "start": Open the new pool configuration and creation view.
            - "run": Calls "create" and returns to the monitoring view.
            - "create": Creates the newly configured pool.
            - "delete": Deletes the selected pools.
            - "refresh": Refresh the pool information in the monitoring view.
            - "resize": Resize the node count of the selected pool.
        """
        BatchOps.register("pools.page", "View running pools", self._pools)
        BatchOps.register("pools.start", "Configure a new pool", self._start)
        BatchOps.register("pools.run", "Create the pool", self._run)
        BatchOps.register("pools.create", "Internal: Create the pool", self._create)
        BatchOps.register("pools.delete", "Delete pool", self._delete)
        BatchOps.register("pools.refresh", "Refresh pools", self._refresh)
        BatchOps.register("pools.resize", "Resize pool", self._resize)

    def _register_ui(self):
        """Maps the pools and create pool pages with their corresponding
        ui functions.

        :rtype: dict of str, func pairs
        """
        def get_pools_ui(name):
            name = name.lower()
            return getattr(ui_pools, name)

        page_func = map(get_pools_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _pools(self, op, context):
        """The execute method for the pools.page operator.
        Retrives the data on the pools currently running in the service and
        displays in a pool monitoring view. Sets the page context to 'POOLS'.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        session = context.scene.batch_session
        props = context.scene.batch_pools
        lux = bpy.context.scene.render.engine == 'LUXRENDER_RENDER'
        props.reset()

        #TODO: Load pools in thread
        session.log.debug("Getting pool data.")
        options = models.PoolListOptions(
            filter="startswith(id,'lux')" if lux else "startswith(id,'blender')")
        pools = [p for p in self.batch.pool.list(options)]
        session.log.info("Retrieved {0} pool references.".format(len(pools)))
        for pool in pools:
            props.add_pool(pool)
        session.page = "POOLS"
        return {'FINISHED'}

    def _start(self, op, context):
        """The execute method for the pools.start operator.
        Opens the pool configure and create view. Sets the page context
        to 'CREATE'.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        context.scene.batch_session.page = "CREATE"
        return {'FINISHED'}

    def _run(self, op, context):
        """The execute method for the pools.run operator.
        Invokes the pool create operation followed by the pool page
        operation.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        bpy.ops.batch_pools.create()
        return bpy.ops.batch_pools.page()

    def _create(self, op, context, **kwargs):
        """The execute method for the pools.create operator.
        Starts a newly created pool without altering the current view.
        Only called internally.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        session = context.scene.batch_session
        props = context.scene.batch_pools
        lux = bpy.context.scene.render.engine == 'LUXRENDER_RENDER'
        pool_id = kwargs.get('id', "blender_pool_{}".format(BatchUtils.current_time()))
        if lux:
            pool_id = "luxblend_pool_{}".format(BatchUtils.current_time())
        session.log.info("Creating pool {}".format(pool_id))
        name = props.pool_name if props.pool_name else pool_id
        pool = models.PoolAddParameter(
            pool_id, **BatchUtils.get_pool_config(self.batch, name, lux))
        self.batch.pool.add(pool)
        session.log.info(
            "Started new pool with ID: {0}".format(pool_id))
        return {'FINISHED'}

    def _delete(self, op, context):
        """The execute method for the pools.delete operator.
        Delete the currently selected pools, then calls the pools.page
        operator to refresh the pool list in the display.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        session = context.scene.batch_session
        props = context.scene.batch_pools
        delete = self.pending_delete()
        session.log.info("{0} pools to be deleted".format(len(delete)))
        for index in delete:
            pool = props.collection[index]
            try:
                session.log.debug("Deleting pool {0}".format(pool.id))
                self.batch.pool.delete(pool.id)
            except Exception as exp:
                session.log.warning("Failed to delete {0}".format(pool.id))
                session.log.warning(str(exp))
        return bpy.ops.batch_pools.page()

    def _refresh(self, op, context):
        """The execute method for the pools.refresh operator.
        Calls the page operator to reset the pool monitoring view.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        return bpy.ops.batch_pools.page()

    def _resize(self, op, context):
        """The execute method for the pools.resize operator.
        Resize the number of nodes in the selected pool. Refreshes
        the monitoring view on completion.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        session = context.scene.batch_session
        batch_pools = context.scene.batch_pools
        selected = batch_pools.pools[batch_pools.index]
        pool_obj = batch_pools.collection[batch_pools.index]

        session.log.info("Resizing pool: {0} from {1} to {2} nodes".format(
            pool_obj.id,
            pool_obj.target_dedicated,
            selected.nodes))
        options = {'target_dedicated': selected.nodes,
                   'node_deallocation_option': 'requeue'}
        try:
            self.batch.pool.resize(pool_obj.id, options)
        except Exception as exp:
            session.log.warning("Failed to resize {0}".format(pool_obj.id))
            session.log.warning(str(exp))
        return bpy.ops.batch_pools.page()

    def display(self, ui, layout):
        """Invokes the corresponding ui function depending on the session's
        current page.

        :param ui: The instance of the Interface panel class.
        :type ui: :class:`.Interface`
        :param layout: The layout object, used for creating and placing ui components.
        :type layout: :class:`bpy.types.UILayout`
        :returns: The result of the UI operator - usually {'FINISHED'}
        :rtype: set
        """
        return self.ui[bpy.context.scene.batch_session.page](ui, layout)

    def pending_delete(self):
        """Get a list of the pools that have been selected for delete. 

        :returns: Indexes of the selected pools.
        :rtype: List of int
        """
        pools = bpy.context.scene.batch_pools.pools
        return [i for i, pool in enumerate(pools) if pool.delete_checkbox]
