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

import bpy
import os

import threading

from batched_blender.utils import BatchOps
from batched_blender.ui import ui_pools
from batched_blender.props import props_pools


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
        ops.append(BatchOps.register_expanding("pools.create",
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
        self.props.display = bpy.context.scene.batch_pools

        self.props.display.pools.clear()
        self.props.display.selected = -1

        context.scene.batch_session.log.debug("Getting pool data.")

        self.props.pools = [p for p in self.batch.pool.list()]
        context.scene.batch_session.log.info(
            "Retrieved {0} pool references.".format(len(self.props.pools)))

        for pool in self.props.pools:
            self.props.display.add_pool(pool)
        
        for index, pool in enumerate(self.props.display.pools):
            self.register_pool(pool, index)

        context.scene.batch_session.page = "POOLS"
        return {'FINISHED'}

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
        #new_pool = self.batch.create(
        #    target_size=self.props.display.pool_size)

        #context.scene.batch_session.log.info(
        #    "Started new pool with ID: {0}".format(new_pool.id))

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
        pool = self.get_selected_pool()
        context.scene.batch_session.log.debug(
            "Selected pool {0}".format(pool.id))

        pool.delete()
        context.scene.batch_session.log.info(
            "Deleted pool with ID: {0}".format(pool.id))

        return bpy.ops.batch_pools.page()

    def _create(self, op):
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
        session = bpy.context.scene.batch_session
        session.page = "POOLS" if op.enabled else "CREATE"
        return {'FINISHED'}

    def get_selected_pool(self):
        """
        Retrieves the pool object for the pool currently selected in
        the dispaly.

        :Returns:
            - A :class:`batch.pools.Pool` object.
        """
        return self.props.pools[self.props.display.selected]

    def register_pool(self, pool, index):
        """
        Register a pool as an operator class for dispaly in the UI.

        :Args:
            - pool (:class:`batch.jobs.SubmittedJob`): The pool to
              register.
            - index (int): The index of the job in list currently displayed.

        :Returns:
            - The newly registered operator name (str).
        """
        name = "pools.{0}".format(pool.id.replace("-", "_"))
        label = "Pool: {0}".format(pool.id)
        index_prop = bpy.props.IntProperty(default=index)

        def execute(self):
            session = bpy.context.scene.batch_pools
            bpy.context.scene.batch_session.log.debug(
                "Pool details opened: {0}, selected: {1}, index {2}".format(
                    self.enabled,
                    session.selected,
                    self.ui_index))

            if self.enabled and session.selected == self.ui_index:
                session.selected = -1

            else:
                session.selected = self.ui_index

        bpy.context.scene.batch_session.log.debug(
            "Registering {0}".format(name))

        return BatchOps.register_expanding(name, label, execute,
                                               ui_index=index_prop)