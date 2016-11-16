#-------------------------------------------------------------------------
#
# Batch Apps Blender Addon
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

import azure.batch as batch


class BatchPools(object):
    """
    Manager for the display and creation of Batch Apps instance pools.
    """

    pages = ["POOLS", "CREATE"]

    def __init__(self, manager):

        self.batch = manager

        self.ops = self._register_ops()
        self.props = self._register_props()
        self.ui = self._register_ui()

    def display(self, ui, layout):
        """
        Invokes the corresponding ui function depending on the session's
        current page.

        :Args:
            - ui (blender :class:`.Interface`): The instance of the Interface
              panel class.
            - layout (blender :class:`bpy.types.UILayout`): The layout object,
              derived from the Interface panel. Used for creating ui
              components.

        :Returns:
            - Runs the display function for the applicable page.
        """
        return self.ui[bpy.context.scene.batch_session.page](ui, layout)

    def _register_props(self):
        """
        Registers and retrieves the pools property objects.
        The dispaly properties are defined in a subclass which is assigned
        to the scene.batch_pools context.

        :Returns:
            - :class:`.PoolsProps`
        """
        props = props_pools.register_props()
        return props

    def _register_ops(self):
        """
        Registers each pool operator with a batch_pools prefix.

        :Returns:
            - A list of the names (str) of the registered pool operators.
        """
        ops = []
        ops.append(BatchOps.register("pools.page",
                                     "Running pools",
                                     self._pools))
        ops.append(BatchOps.register("pools.start",
                                     "Start new pool",
                                     self._start))
        ops.append(BatchOps.register("pools.delete",
                                     "Delete pool",
                                     self._delete))
        ops.append(BatchOps.register("pools.refresh",
                                     "Refresh pools",
                                     self._refresh))
        ops.append(BatchOps.register("pools.create",
                                     "Create pool",
                                     self._create))
        return ops

    def _register_ui(self):
        """
        Matches the pools and create pool pages with their corresponding
        ui functions.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_pools_ui(name):
            name = name.lower()
            return getattr(ui_pools, name)

        page_func = map(get_pools_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _pools(self, op, context):
        """
        The execute method for the pools.page operator.
        Downloads the data on the pools currently running in the service and
        registers each as an operator for display in the UI.

        Sets the page to POOLS.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batch_session
        session.page = "POOLS"
        self.props = context.scene.batch_pools
        self.props.reset()

        #TODO: Filter pools based on id prefix
        #TODO: Load pools in thread
        session.log.debug("Getting pool data.")
        pools = [p for p in self.batch.pool.list()]
        session.log.info("Retrieved {0} pool references.".format(len(pools)))

        for pool in pools:
            self.props.add_pool(pool)
  
        return {'FINISHED'}

    def _refresh(self, op, context):
        """
        The execute method for the pools.page operator.
        Downloads the data on the pools currently running in the service and
        registers each as an operator for display in the UI.

        Sets the page to POOLS.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        return bpy.ops.batch_pools.page()
        #session = context.scene.batch_session
        #self.props = context.scene.batch_pools
        #self.props.reset()

        #session.log.debug("Getting pool data.")
        #pools = [p for p in self.batch.pool.list()]
        #session.log.info("Retrieved {0} pool references.".format(len(pools)))

        #for pool in pools:
        #    self.props.add_pool(pool)
  
        #return {'FINISHED'}

    def _start(self, op, context):
        """
        The execute method for the pools.start operator.
        Starts a newly created pool, then calls the pools.page operator
        to refresh the pool list in the display and return to the POOLS page.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batch_session
        pool_id = "Blender_Pool_{}".format(BatchUtils.current_time())
        session.log.info("creating pool {}".format(pool_id))
        
        pool_config = BatchUtils.get_pool_config(self.batch)
        pool = batch.models.PoolAddParameter(
            pool_id,
            bpy.context.user_preferences.addons[__package__].preferences.vm_type,
            display_name=self.props.pool_name,
            virtual_machine_configuration=pool_config,
            target_dedicated=self.props.pool_size,
            start_task=BatchUtils.install_blender(),
        )
        self.batch.pool.add(pool)

        session.log.info(
            "Started new pool with ID: {0}".format(pool_id))

        return bpy.ops.batch_pools.page()

    def _delete(self, op, context):
        """
        The execute method for the pools.delete operator.
        Delete the currently selected pool, then calls the pools.page
        operator to refresh the pool list in the display.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batch_session
        delete = self.pending_delete()

        session.log.info("{0} pools to be deleted".format(len(delete)))

        for index in delete:
            pool = self.props.collection[index]
            display = self.props.pools[index]

            try:
                session.log.debug("Deleting pool {0}".format(pool.id))
                self.batch.pool.delete(pool.id)
            except Exception as exp:
                session.log.warning("Failed to delete {0}".format(pool.id))
                session.log.warning(str(exp))

        return bpy.ops.batch_pools.page()

    def _create(self, op, context):
        """
        The execute method for the pools.create operator.
        Display the UI components to create a new pool by setting the page
        to CREATE.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batch_session
        session.page = "CREATE"
        return {'FINISHED'}

    def pending_delete(self):
        """
        Get a list of the pools that have been selected for delete. 

        :Returns:
            - A list of the indexes (int) of the items in the display
              pool list that have been selected for delete.
        """

        delete_me = []

        for index, pool in enumerate(self.props.pools):
            if pool.delete_checkbox:
                delete_me.append(index)

        return delete_me