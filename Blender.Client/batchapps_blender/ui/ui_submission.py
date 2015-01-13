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


def static(ui, layout, active):
    """
    Display static job details reflecting global render settings.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - active (bool): Whether UI components are enabled.

    """
    width = int(bpy.context.scene.render.resolution_x*\
        (bpy.context.scene.render.resolution_percentage/100))
    height = int(bpy.context.scene.render.resolution_y*\
        (bpy.context.scene.render.resolution_percentage/100))
    output = bpy.context.scene.batchapps_submission.image_format
    
    ui.label("Width: {0}".format(width), layout.row(), active=active)
    ui.label("Height: {0}".format(height), layout.row(), active=active)
    ui.label("Output: {0}".format(output), layout.row(), active=active)


def variable(ui, layout, active):
    """
    Display frame selection controls.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - active (bool): Whether UI components are enabled.

    """
    ui.prop(bpy.context.scene.batchapps_submission, "start_f", layout.row(),
            label="Start Frame ", active=active)
    ui.prop(bpy.context.scene.batchapps_submission, "end_f", layout.row(),
            label="End Frame ", active=active)


def pool_select(ui, layout, active):
    """
    Display pool selection controls.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - active (bool): Whether UI components are enabled.

    """
    ui.label("", layout)
    ui.prop(bpy.context.scene.batchapps_submission, "pool", layout.row(),
            label=None, expand=True, active=active)

    if bpy.context.scene.batchapps_submission.pool == {"reuse"}:
        ui.label("Use an existing persistant pool by ID", layout.row(), active=active)
        ui.prop(bpy.context.scene.batchapps_submission, "pool_id",
                layout.row(), active=active)

    elif bpy.context.scene.batchapps_submission.pool == {"create"}:
        ui.label("Create a new persistant pool", layout.row(), active=active)
        ui.prop(bpy.context.scene.batchapps_pools, "pool_size",
                layout.row(), "Number of instances:", active=active)

    else:
        ui.label("Auto provision a pool for this job", layout.row(),
                 active=active)
        ui.prop(bpy.context.scene.batchapps_submission, "pool_size",
                layout.row(), "Number of instances:", active=active)

def pre_submission(ui, layout):
    """
    Display any warnings before job submission.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    if not bpy.context.scene.batchapps_submission.valid_format:
        ui.label("Warning: Output format {0}".format(
            bpy.context.scene.render.image_settings.file_format), layout)

        ui.label("not supported. Using PNG instead", layout)
        row = layout.row(align=True)
        row.alert=True
        ui.operator("submission.start", "Submit Job", row)
        
    elif not bpy.context.scene.batchapps_submission.valid_range:
        ui.label("Warning: Selected frame range falls", layout)
        ui.label("outside global render range", layout)
        row = layout.row(align=True)
        row.alert=True
        ui.operator("submission.start", "Submit Job", row)

    else:
        ui.label("", layout)
        ui.label("", layout)
        ui.operator("submission.start", "Submit Job", layout)
    
    ui.operator("shared.home", "Return Home", layout)


def post_submission(ui, layout):
    """
    Display the job processing message.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    ui.label("Submission now processing.", layout.row(align=True), "CENTER")
    ui.label("See console for progress.", layout.row(align=True), "CENTER")
    ui.label("Please don't close blender.", layout.row(align=True), "CENTER")


def submit(ui, layout):
    """
    Display new job submission page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    ui.prop(bpy.context.scene.batchapps_submission, "title", layout,
            label="Job name ", active=True)

    static(ui, layout, True)
    variable(ui, layout, True)
    pool_select(ui, layout, True)
    pre_submission(ui, layout)

def processing(ui, layout):
    """
    Display job submission processing page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    ui.prop(bpy.context.scene.batchapps_submission, "title", layout.row(),
            label="Job name ", active=False)

    static(ui, layout, False)
    variable(ui, layout, False)
    pool_select(ui, layout, False)
    post_submission(ui, layout)

    ui.label("", layout)


def submitted(ui, layout):
    """
    Display job submitted page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    sublayout = layout.box()
    ui.label("Submission Successfull!", sublayout.row(align=True), "CENTER")
    ui.label("", sublayout, "CENTER")
    ui.operator("shared.home", "Return Home", layout)