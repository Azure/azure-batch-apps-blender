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

class AssetListUI(bpy.types.UIList):
    """Ui List element for display assets"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index, flt_flag):
        """Draw UI List"""

        asset = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(asset.name)

            if not asset.upload_check:
                col = layout.column()
                col.prop(asset,
                         "upload_checkbox",
                         text="",
                         index=index)

            else:
                col = layout.column()
                col.label("", icon="FILE_TICK")

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
    batchapps_assets = bpy.context.scene.batchapps_assets

    num_assets = len(batchapps_assets.assets)
    num_display = "Displaying {0} assets".format(num_assets)

    ui.label(num_display, layout.row(align=True), align='CENTER')
    row = layout.row(align=True)

    div = row.split()
    ui.operator("assets.refresh", "Reset", div, "FILE_REFRESH")

    div = row.split()
    active = any(a.upload_checkbox for a in batchapps_assets.assets)
    ui.operator('assets.upload', "Upload", div, "MOVE_UP_VEC", active=active)

    div = row.split()
    ui.operator("assets.add", "", div, "ZOOMIN")

    div = row.split()
    active = (num_assets > 0)
    ui.operator('assets.remove', "", div, "ZOOMOUT", active=active)


def display_uilist(ui, layout):
    """
    Displays the UI List that will show all collected assets.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
    """

    batchapps_assets = bpy.context.scene.batchapps_assets
    outerBox = layout.box()
    row = outerBox.row()

    ui.label("Filename", row)
    ui.label("Uploaded", row, "RIGHT")

    outerBox.template_list("AssetListUI",
                           "",
                           batchapps_assets,
                           "assets",
                           batchapps_assets,
                           "index")

    if len(batchapps_assets.assets) > 0:
        display_details(ui, outerBox)


def display_details(ui, outerBox):
    """
    Displays the details of the asset selected in the UI List.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - outerBox (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components. In this case the box the details are listed within.
    """
    batchapps_assets = bpy.context.scene.batchapps_assets
    col = outerBox.column(align=True)
    
    if batchapps_assets.index < len(batchapps_assets.assets):

        selected = batchapps_assets.assets[batchapps_assets.index]
        uploaded = "Uploaded" if selected.upload_check else "Not Uploaded"

        ui.label("Asset: {0}".format(selected.name), col)
        ui.label("Status: {0}".format(uploaded), col)
        ui.label("Date Modified: {0}".format(selected.timestamp), col)
        ui.label("Full Path: {0}".format(selected.fullpath), col)

def assets(ui, layout):
    """
    Display asset management page.

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
    