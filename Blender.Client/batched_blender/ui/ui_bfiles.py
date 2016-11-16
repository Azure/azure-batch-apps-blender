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

class BlobListUI(bpy.types.UIList):
    """Ui List element for display blobs"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index, flt_flag):
        """Draw UI List"""

        blob = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(blob.name)
            col = layout.column()
            col.prop(blob,
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
    batch_blobs = bpy.context.scene.batch_bfiles

    num_blobs = len(batch_blobs.bfiles)
    num_display = "Displaying {0} blobs".format(num_blobs)

    ui.label(num_display, layout.row(align=True), align='CENTER')
    row = layout.row(align=True)

    div = row.split()
    ui.operator("bfiles.refresh", "Refresh", div, "FILE_REFRESH")

    div = row.split()
    active = any(a.delete_checkbox for a in batch_blobs.bfiles)
    ui.operator('bfiles.delete', "Remove", div, "CANCEL", active=active)

def display_uilist(ui, layout):
    """
    Displays the UI List that will show all current blobs.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
    """

    batch_blobs = bpy.context.scene.batch_bfiles
    outerBox = layout.box()
    row = outerBox.row()

    ui.label("Name", row)
    ui.label("Remove", row, "RIGHT")

    outerBox.template_list("BlobListUI",
                           "",
                           batch_blobs,
                           "bfiles",
                           batch_blobs,
                           "index")

    if len(batch_blobs.bfiles) > 0:
        display_details(ui, outerBox)

def display_details(ui, outerBox):
    """
    Displays the details of the blob selected in the UI List.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - outerBox (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components. In this case the box the details are listed within.
    """
    batch_blobs = bpy.context.scene.batch_bfiles
    col = outerBox.column(align=True)

    #TODO: Display both upload date and file last modified
    if batch_blobs.index < len(batch_blobs.bfiles):
        selected = batch_blobs.bfiles[batch_blobs.index]
        ui.label("Name: {}".format(selected.name), col)
        ui.label("Size: {}".format(selected.size), col)
        ui.label("Uploaded: {}".format(selected.uploaded), col)
        ui.label("Checksum: {}".format(selected.checksum), col)
    
def bfiles(ui, layout):
    """
    Display blob management page.

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
