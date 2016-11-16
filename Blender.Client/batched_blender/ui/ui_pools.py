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


class PoolListUI(bpy.types.UIList):
    """Ui List element for display pools"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index, flt_flag):
        """Draw UI List"""

        pool = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(pool.name)

            #TODO: Only display check box when not transitioning
            col = layout.column()
            col.prop(pool,
                        "delete_checkbox",
                        text="",
                        index=index)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'

            if flt_flag:
                layout.enabled = False
            layout.label(text="", icon_value=icon)

        else:
            layout.label(text="",
                         translate=False,
                         icon_value=icon)


def uilist_controls(ui, layout):
    """
    Displays the buttons and labels for the UI List.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
    """
    batch_pools = bpy.context.scene.batch_pools

    num_pools = len(batch_pools.pools)
    num_display = "Displaying {0} pools".format(num_pools)

    ui.label(num_display, layout.row(align=True), align='CENTER')
    row = layout.row(align=True)

    div = row.split()
    ui.operator("pools.refresh", "Refresh", div, "FILE_REFRESH")

    div = row.split()
    active = any(a.delete_checkbox for a in batch_pools.pools)
    ui.operator('pools.delete', "Remove", div, "CANCEL", active=active) #TODO: Change icon

    div = row.split()
    ui.operator("pools.create", "Create", div, "ZOOMIN")


def display_uilist(ui, layout):
    """
    Displays the UI List that will show all current pools.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
    """

    batch_pools = bpy.context.scene.batch_pools
    outerBox = layout.box()
    row = outerBox.row()

    ui.label("Name", row)
    ui.label("Remove", row, "RIGHT")

    outerBox.template_list("PoolListUI",
                           "",
                           batch_pools,
                           "pools",
                           batch_pools,
                           "index")

    if len(batch_pools.pools) > 0:
        display_details(ui, outerBox)


def display_details(ui, outerBox):
    """
    Displays the details of the pool selected in the UI List.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - outerBox (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components. In this case the box the details are listed within.
    """
    batch_pools = bpy.context.scene.batch_pools
    col = outerBox.column(align=True)
    
    #TODO: Display node information
    if batch_pools.index < len(batch_pools.pools):
        selected = batch_pools.pools[batch_pools.index]
        ui.label("Pool: {0}".format(selected.name), col)
        ui.label("Status: {0}".format(selected.state), col)
        ui.label("Date Created: {0}".format(selected.timestamp), col)
        ui.label("Size: {0}".format(selected.nodes), col)
        ui.label("ID: {0}".format(selected.id), col)

def pools(ui, layout):
    """
    Display pool management page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    uilist_controls(ui, layout)
    display_uilist(ui, layout)
    
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

    box = layout.box()
    ui.label("New Pool", box)
    ui.prop(batch_pools, "pool_name", box, "Pool Name")
    ui.prop(batch_pools, "pool_size", box, "Pool Size")
    ui.operator("pools.start", "Start Pool", box)

    ui.label("", layout)
    ui.operator("pools.page", "Return to Pools", layout)
    ui.operator("shared.home", "Return Home", layout)