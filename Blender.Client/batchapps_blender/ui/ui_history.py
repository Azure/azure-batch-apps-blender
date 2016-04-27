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


def status_icon(job):
    """
    Get the appropriate operator icon based on a jobs status.

    :Args:
        - job (:class:`.HistoryDetails`): The selected job to display.
    
    :Returns:
        - The required icon name (str).

    """
    status = job.status.lower()
    icons = bpy.context.scene.batch_history.icons
    return icons.get(status, "")

def details(ui, layout, job):
    """
    Display the detailed information on an indivual selected job.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - job (:class:`.HistoryDetails`): The selected job to display.

    """
    if job.status in ["InProgress", "Error", "Cancelled"]:
        status = """Status: {0} - {1}% complete""".format(
            job.status, job.percent)

    else:
        status = "Status: {0}".format(job.status)

    ui.label(status, layout)
    ui.label("Submitted: {0}".format(job.timestamp), layout)
    ui.label("ID: {0}".format(job.id), layout)
    ui.label("Type: {0}".format(job.type), layout)
    ui.label("Number of Tasks: {0}".format(job.tasks), layout)
    ui.label("Pool: {0}".format(job.pool_id), layout)

    if job.status.lower() in ["notstarted", "inprogress"]:
        ui.operator("history.cancel", "Cancel Job", layout)

def page_controls(ui, layout, num_jobs):
    """
    Display the job history list paging controls.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.
        - num_jobs (int): The total number of jobs in the users history.

    """
    history = bpy.context.scene.batch_history

    if history.total_count == 0:
        start = 0
        end = 0

    elif history.total_count != 0 and history.index == 0:
        start = 1
        end = num_jobs

    else:
        start = history.index + 1
        end = (start+num_jobs)-1

    job_display = "Displaying jobs {start}-{end} of {total}".format(
        start=start, end=end, total=history.total_count)

    ui.label(job_display, layout.row(align=True), "CENTER")

    split = layout.split(percentage=0.333)
    row = split.row(align=True)
    ui.operator("history.first", "", row, "REW", "LEFT", (history.index != 0))
    ui.operator("history.less", "", row, "PREV_KEYFRAME",
                "LEFT", (history.index != 0))

    row = split.row(align=True)
    ui.operator("history.refresh", "Refresh", row, "FILE_REFRESH", "CENTER")

    row = split.row(align=True)
    enabled = (history.index + num_jobs) != history.total_count
    ui.operator("history.more", "", row, "NEXT_KEYFRAME", "RIGHT", enabled)
    ui.operator("history.last", "", row, "FF", "RIGHT", enabled)


def history(ui, layout):
    """
    Display job history page.

    :Args:
        - ui (blender :class:`.Interface`): The instance of the Interface
            panel class.
        - layout (blender :class:`bpy.types.UILayout`): The layout object,
            derived from the Interface panel. Used for creating ui
            components.

    """
    jobs = bpy.context.scene.batch_history.jobs

    page_controls(ui, layout, len(jobs))
    outer_box = layout.box()

    if not jobs:
        ui.label("No jobs to display.", outer_box.row(), "CENTER")

    else:
        for index, job in enumerate(jobs):

            if index == bpy.context.scene.batch_history.selected:
                inner_box = outer_box.box()

                ui.operator("history."+job.id.replace("-", "_"), (" "+job.name),
                            inner_box, status_icon(job))
                details(ui, inner_box, job)

            else:
                ui.operator("history."+job.id.replace("-", "_"), (" "+job.name),
                            outer_box, status_icon(job))

    ui.label("", layout)
    ui.operator("shared.home", "Return Home", layout)

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
    page_controls(ui, layout, 0)
    outer_box = layout.box()
    ui.label("Loading...", outer_box.row(align=True), "CENTER")

    ui.label("", layout)
    ui.operator("shared.home", "Return Home", layout, active=False)