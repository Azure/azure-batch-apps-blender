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

def details(ui, layout, bfile):
    """
    Display details on an individual selected bfile.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - bfile (:class:`.BfileDetails`): The selected bfile to display.

    """
    ui.label("name: {0}".format(bfile.name), layout)
    #Programatically given in Byte, but shown in Kibibyte under azure.portal
    ui.label("size: "+str(round(bfile.size*0.976562/1000,2)), layout)
    ui.label("last_modified: "+bfile.timestamp, layout)
    row = layout.row(align=True)
    ui.operator("bfiles.delete", "Delete Blob", row)

def display_bfiles(ui, layout):
    """
    Display bfile list.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    batch_bfiles = bpy.context.scene.batch_bfiles
    icons_right = {True: 'DISCLOSURE_TRI_RIGHT_VEC', False: 'TRIA_RIGHT'}
    icons_down = {True: 'DISCLOSURE_TRI_DOWN_VEC', False: 'TRIA_DOWN'}
    if not batch_bfiles.bfiles:
        ui.label("No bfiles found", layout)
    else:
        for index, bfile in enumerate(batch_bfiles.bfiles):
            if index == batch_bfiles.selected:
                inner_box = layout.box()
                ui.operator(bfile.name, "Hide details",
                            inner_box, icons_down[True])
                details(ui, inner_box, bfile)
            else:
                ui.operator(bfile.name, (' '+bfile.name),
                            layout, icons_right[True])

def bfiles(ui, layout):
    """
    Display bfiles page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    batch_bfiles = bpy.context.scene.batch_bfiles
    display_bfiles(ui, layout)
    ui.label("", layout)
    ui.operator("bfiles.page", "Refresh Blobs", layout)
    ui.operator("shared.home", "Return Home", layout)

