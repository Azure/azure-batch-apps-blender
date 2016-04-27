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

def details(ui, layout, pool):
    """
    Display details on an individual selected pool.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - pool (:class:`.PoolDetails`): The selected pool to display.

    """
    types = {True:'Auto Provisioned',
             False: 'Persistent Pool'}
    if not pool.auto:
        split = layout.split(percentage=0.1)
        ui.label("ID: ", split.row(align=True))
        proprow = split.row(align=True)
        proprow.active=False
        ui.prop(pool, 'id', proprow)

    else: ui.label("ID: {0}".format(pool.id), layout)

    ui.label("Type: {0}".format(types[pool.auto]), layout)
    ui.label("State: {0}".format(pool.state), layout)
    ui.label("Currently running: {0} jobs".format(pool.queue), layout)
    ui.label("", layout)

    ui.label("Created: {0}".format(pool.created), layout)
    split = layout.split(percentage=0.5)
    ui.label("Target Size: {0}".format(pool.target), split.row(align=True))
    ui.label("Current Size: {0}".format(pool.current), split.row(align=True))
                

    row = layout.row(align=True)
    if pool.queue > 0:
        row.alert=True
    ui.operator("pools.delete", "Delete Pool", row)

def display_pools(ui, layout):
    """
    Display pool list.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    batch_pools = bpy.context.scene.batch_pools
    icons_right = {True: 'DISCLOSURE_TRI_RIGHT_VEC', False: 'TRIA_RIGHT'}
    icons_down = {True: 'DISCLOSURE_TRI_DOWN_VEC', False: 'TRIA_DOWN'}

    if not batch_pools.pools:
        ui.label("No pools found", layout)
        
    else:
        for index, pool in enumerate(batch_pools.pools):

            if index == batch_pools.selected:

                inner_box = layout.box()
                ui.operator("pools."+pool.id.replace("-", "_"), "Hide details",
                            inner_box, icons_down[pool.auto])

                details(ui, inner_box, pool)

            else:
                ui.operator("pools."+pool.id.replace("-", "_"), (' '+pool.id),
                            layout, icons_right[pool.auto])

def pools(ui, layout):
    """
    Display pools page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    batch_pools = bpy.context.scene.batch_pools
    ui.operator("pools.create", "Create New Pool", layout)
    ui.label("", layout)

    display_pools(ui, layout)

    ui.label("", layout)
    ui.operator("pools.page", "Refresh Pools", layout)
    ui.operator("shared.home", "Return Home", layout)

def create(ui, layout):
    """
    Display create new pool panel in pools page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    batch_pools = bpy.context.scene.batch_pools
    ui.operator("pools.create", "Create New Pool", layout.row())

    box = layout.box()
    ui.label("New Pool", box)
    ui.prop(batch_pools, "pool_size", box, "Pool Size")
    ui.operator("pools.start", "Start Pool", box)

    ui.label("", layout)

    display_pools(ui, layout)

    ui.label("", layout)
    ui.operator("pools.page", "Refresh Pools", layout)
    ui.operator("shared.home", "Return Home", layout)

