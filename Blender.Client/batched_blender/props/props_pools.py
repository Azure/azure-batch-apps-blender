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


def format_date(pool):
    """
    Format a pool created date for the UI.

    :Args:
        - pool (:class:`batch.pool.Pool`): Pool whos date we want to
          format.

    :Returns:
        - The created date as a string. If formatting fails,
          an empty string.
    """
    try:
        datelist = pool.creation_time.isoformat().split('T')
        datelist[1] = datelist[1].split('.')[0]
        return ' '.join(datelist)

    except:
        bpy.context.scene.batch_session.log.debug(
            "Couldn't format date {0}.".format(pool.creation_time.isoformat()))
        return ""

class PoolDisplayProps(bpy.types.PropertyGroup):
    """
    A display object representing a pool.
    Displayed by :class:`.ui_pools.PoolListUI`.
    """

    name = bpy.props.StringProperty(
        description="Pool name")

    auto = bpy.props.BoolProperty(
        description="Whether pool is an auto-pool")

    nodes = bpy.props.IntProperty(
        description="Number of nodes in pool")
    
    delete_checkbox = bpy.props.BoolProperty(
        description = "Check to delete pool",
        default = False)

    timestamp = bpy.props.StringProperty(
        description="Pool created timestamp",
        default="")

    state = bpy.props.StringProperty(
        description="Pool State",
        default="")

    id = bpy.props.StringProperty(
        description="Pool ID")

class PoolProps(bpy.types.PropertyGroup):
    """
    Pool Properties,
    Once instantiated, this class is set to both the Blender context, and
    assigned to pools.BatchPools.props.
    """
    stable_states = ["steady"]
    collection = []

    pools = bpy.props.CollectionProperty(
        type=PoolDisplayProps,
        description="Pool display list")

    index = bpy.props.IntProperty(
        description="Selected pool index")

    pool_size = bpy.props.IntProperty(
        description="Number of instances in new pool",
        default=3,
        min=1,
        max=20)

    pool_name = bpy.props.StringProperty(
        description="Name of the new pool",
        default="")

    def add_pool(self, pool):
        """
        Add a pool to both the display and object lists.

        """
        log = bpy.context.scene.batch_session.log
        log.debug("Adding pool to ui list {0}".format(pool.id))

        self.collection.append(pool)
        self.pools.add()
        entry = self.pools[-1]
        if hasattr(pool, 'display_name') and pool.display_name:
            entry.name = pool.display_name
        else:
            entry.name = pool.id
        entry.auto = pool.id.startswith('blender_auto_')
        entry.timestamp = format_date(pool)
        entry.nodes = pool.current_dedicated
        entry.state = pool.allocation_state.value
        entry.id = pool.id

        log.debug("Total pools now {0}.".format(len(self.pools)))

    def remove_selected(self):
        """
        Remove selected pool from both display and object lists.

        """
        bpy.context.scene.batch_session.log.debug(
            "Removing index {0}.".format(self.index))

        self.collection.pop(self.index)
        self.pools.remove(self.index)
        self.index = max(self.index - 1, 0)

    def reset(self):
        """
        Clear both pool display and object lists.

        """
        self.collection.clear()
        self.pools.clear()
        self.index = 0

        bpy.context.scene.batch_session.log.debug("Reset pool lists.")


def register_props():
    """
    Register the pool property classes and assign to the blender
    context under "batch_pools".

    :Returns:
        - A :class:`.PoolProps` object
    """

    bpy.types.Scene.batch_pools = \
        bpy.props.PointerProperty(type=PoolProps)

    return bpy.context.scene.batch_pools
