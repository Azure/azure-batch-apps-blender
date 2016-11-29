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


class JobListUI(bpy.types.UIList):
    """Ui List element for display jobs"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index, flt_flag):
        """Draw UI List"""

        job = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(job.name)
            if job.status in bpy.context.scene.batch_jobs.stable_states:
                col = layout.column()
                col.prop(job,
                         "delete_checkbox",
                         text="",
                         index=index)
            else:
                col = layout.column()
                col.label("", icon="FILE_REFRESH")

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
    batch_jobs = bpy.context.scene.batch_jobs

    num_jobs = len(batch_jobs.jobs)
    num_display = "Displaying {0} jobs".format(num_jobs)

    ui.label(num_display, layout.row(align=True), align='CENTER')
    row = layout.row(align=True)

    div = row.split()
    ui.operator("jobs.refresh", "Refresh", div, "FILE_REFRESH")

    div = row.split()
    active = any(a.delete_checkbox for a in batch_jobs.jobs)
    ui.operator('jobs.delete', "Remove", div, "CANCEL", active=active) #TODO: Change icon

    div = row.split()
    active = bool(batch_jobs.more)
    ui.operator('jobs.load_more', "Load More", div, "MOVE_UP_VEC", active=active) #TODO: Change icon

def display_uilist(ui, layout):
    """
    Displays the UI List that will show all jobs.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
    """

    batch_jobs = bpy.context.scene.batch_jobs
    outerBox = layout.box()
    row = outerBox.row()

    ui.label("Name", row)
    ui.label("Remove", row, "RIGHT")

    outerBox.template_list("JobListUI",
                           "",
                           batch_jobs,
                           "jobs",
                           batch_jobs,
                           "index")

    if len(batch_jobs.jobs) > 0:
        display_details(ui, outerBox)

def display_details(ui, outerBox):
    """
    Displays the details of the job selected in the UI List.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - outerBox (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components. In this case the box the details are listed within.
    """
    batch_jobs = bpy.context.scene.batch_jobs
    col = outerBox.column(align=True)
    
    #TODO: Display task information
    if batch_jobs.index < len(batch_jobs.jobs):
        selected = batch_jobs.jobs[batch_jobs.index]
        ui.label("Job: {0}".format(selected.name), col)
        ui.label("Status: {0}".format(selected.status), col)
        ui.label("Percent: {0}".format(selected.percent), col)
        ui.label("Submitted: {0}".format(selected.timestamp), col)
        split = col.split(percentage=0.1)
        ui.label("ID:", split.row(align=True))
        proprow = split.row(align=True)
        proprow.active=False
        ui.prop(selected, 'id', proprow)
        if selected.pool != 'auto pool':
            split = col.split(percentage=0.1)
            ui.label("Pool:", split.row(align=True))
            proprow = split.row(align=True)
            proprow.active=False
            ui.prop(selected, 'pool', proprow)
        else:
            ui.label("Pool: {0}".format(selected.pool), col)
        ui.prop(batch_jobs, 'output_dir', col)
        ui.operator("jobs.download", "Download Outputs", col)

def loading(ui, layout):
    """
    Display job history loading page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    outer_box = layout.box()
    ui.label("Loading...", outer_box.row(align=True), "CENTER")

    ui.label("", layout)
    ui.operator("shared.home", "Return Home", layout, active=False)

def jobs(ui, layout):
    """
    Display job management page.

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