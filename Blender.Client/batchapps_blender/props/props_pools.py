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

@bpy.app.handlers.persistent
def on_load(*args):
    """
    Event handler to refresh pools when a new blender scene is opened.

    Run on blend file load when page is POOLS or CREATE.
    """
    if bpy.context.scene.batch_session.page in ["POOLS", "CREATE"]:
        bpy.ops.batch_pools.page()

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

class PoolDetails(bpy.types.PropertyGroup):
    """
    A display object representing a pool.
    his class is added to the Blender context.
    """

    id = bpy.props.StringProperty(
        description="Pool ID",
        default="")

    auto = bpy.props.BoolProperty(
        description="Auto Pool or manually provisioned",
        default=True)

    created = bpy.props.StringProperty(
        description="When pool was created",
        default="")

    target = bpy.props.IntProperty(
        description="Pool target size",
        default=0)

    current = bpy.props.IntProperty(
        description="Pool current size",
        default=0)

    state = bpy.props.StringProperty(
        description="Pool State",
        default="")

    queue = bpy.props.IntProperty(
        description="Pool Queue",
        default=0)

class PoolDisplayProps(bpy.types.PropertyGroup):
    """Display object representing a pool list"""

    selected = bpy.props.IntProperty(
        description="Selected pool",
        default=-1)

    pool_size = bpy.props.IntProperty(
        description="Number of instances in new pool",
        default=3,
        min=1,
        max=20)

    pools = bpy.props.CollectionProperty(
        type=PoolDetails,
        description="Pools currently running")

    def add_pool(self, pool):
        """
        Add a pool reference to the pool display list.

        """
        log = bpy.context.scene.batch_session.log
        log.debug("Adding pool to ui list {0}".format(pool.id))

        self.pools.add()
        entry = self.pools[-1]
        entry.auto = pool.id.startswith('Blender_auto_pool_')
        entry.id = pool.display_name if entry.auto else pool.id
        entry.created = format_date(pool)
        entry.target = pool.target_dedicated
        entry.current = pool.current_dedicated
        entry.state = pool.allocation_state.value
        entry.queue = 0 #len(pool.jobs)

class PoolsProps(object):
    """
    Pools Properties.
    Once instantiated, this class is assigned to pools.BatchPools.props
    but is not added to the Blender context.
    """
        
    pools = []
    display = None
    thread = None

def register_props():
    """
    Register the pool property classes and assign to the blender
    context under "batch_pools".
    Also registers pool event handlers.

    :Returns:
        - A :class:`.PoolsProps` object

    """
    props_obj = PoolsProps()
    bpy.types.Scene.batch_pools = \
        bpy.props.PointerProperty(type=PoolDisplayProps)

    props_obj.display = bpy.context.scene.batch_pools
    bpy.app.handlers.load_post.append(on_load)

    return props_obj