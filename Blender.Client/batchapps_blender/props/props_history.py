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

def format_date(job):
    """
    Format a job submitted date for the UI.

    :Args:
        - jon (:class:`batchapps.job.SubmittedJob`): Job whos date we want to
          format.

    :Returns:
        - The submitted date as a string. If formatting fails,
          an empty string.
    """
    try:
        datelist = job.time_submitted.split('T')
        datelist[1] = datelist[1].split('.')[0]
        return ' '.join(datelist)

    except:
        bpy.context.scene.batchapps_session.log.debug(
            "Couldn't format date {0}.".format(job.time_submitted))
        return ""


class HistoryDetails(bpy.types.PropertyGroup):
    """A display object representing a job."""

    id = bpy.props.StringProperty(
        description="Job ID",
        default="")

    name = bpy.props.StringProperty(
        description="Job Name",
        default="")

    type = bpy.props.StringProperty(
        description="Job Type",
        default="")

    status = bpy.props.StringProperty(
        description="Job Status",
        default="")

    timestamp = bpy.props.StringProperty(
        description="Time Submitted",
        default="")

    percent = bpy.props.IntProperty(
        description="Percent Complete",
        default=0)

    pool_id = bpy.props.StringProperty(
        description="Job Pool ID",
        default="Unknown")

    tasks = bpy.props.IntProperty(
        description="Number of Tasks",
        default=0)


class HistoryDisplayProps(bpy.types.PropertyGroup):
    """
    Display object representing a job list.
    This class is added to the Blender context.
    """

    selected = bpy.props.IntProperty(
        description="Selected Job",
        default=-1)

    jobs = bpy.props.CollectionProperty(
        type=HistoryDetails,
        description="Job History")

    per_call = bpy.props.IntProperty(
        description="Jobs Per Call",
        default=10,
        min=1,
        soft_min=1,
        max=50,
        soft_max=50)

    total_count = bpy.props.IntProperty(
        description="Total Job Count",
        default=0)

    index = bpy.props.IntProperty(
        description="Job display index",
        default=0)

    icons = {
        'inprogress': 'PREVIEW_RANGE',
        'complete': 'FILE_TICK',
        'cancelled': 'CANCEL',
        'error': 'ERROR',
        'notstarted': 'TIME'
        }

    def add_job(self, job):
        """
        Add a job to the job display list.

        """
        log = bpy.context.scene.batchapps_session.log
        log.debug("Adding job to ui list {0}".format(job.id))

        self.jobs.add()
        entry = self.jobs[-1]
        entry.id = job.id
        entry.name = job.name
        entry.type = job.type
        entry.status = job.status
        entry.tasks = job.number_tasks
        entry.percent = job.percentage if job.percentage else 0
        entry.timestamp = format_date(job)

        if job.pool_id:
            entry.pool_id = job.pool_id


class HistoryProps(object):
    """
    History properties.
    Once instantiated, this class is assigned to assets.BatchAppsAssets.props
    but is not added to the Blender context.
    """

    job_list = []
    display = None
    thread = None


def register_props():
    """
    Register the history property classes and assign to the blender
    context under "batchapps_history".

    :Returns:
        - A :class:`.HistoryProps` object

    """
    props_obj = HistoryProps()

    bpy.types.Scene.batchapps_history = \
        bpy.props.PointerProperty(type=HistoryDisplayProps)
    props_obj.display = bpy.context.scene.batchapps_history

    return props_obj
