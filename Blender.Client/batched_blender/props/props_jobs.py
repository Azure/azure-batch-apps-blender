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

import batched_blender.helpers as helpers

def format_date(job):
    """
    Format a job submitted date for the UI.

    :Args:
        - jon (:class:`batch.job.SubmittedJob`): Job whos date we want to
          format.

    :Returns:
        - The submitted date as a string. If formatting fails,
          an empty string.
    """
    try:
        datelist = job.creation_time.isoformat().split('T')
        datelist[1] = datelist[1].split('.')[0]
        return ' '.join(datelist)

    except:
        bpy.context.scene.batch_session.log.debug(
            "Couldn't format date {0}.".format(job.time_submitted))
        return ""


class JobDisplayProps(bpy.types.PropertyGroup):
    """
    A display object representing a job.
    Displayed by :class:`.ui_jobs.JobListUI`.
    """

    name = bpy.props.StringProperty(
        description="Job name")

    id = bpy.props.StringProperty(
        description="Job ID")

    pool = bpy.props.StringProperty(
        description="Pool on which the job ran")

    percent = bpy.props.IntProperty(
        description="Job complete percentage")
    
    delete_checkbox = bpy.props.BoolProperty(
        description = "Check to delete job",
        default = False)

    timestamp = bpy.props.StringProperty(
        description="Job created timestamp",
        default="")

    status = bpy.props.StringProperty(
        description="Job State",
        default="")

class JobProps(bpy.types.PropertyGroup):
    """
    Job Properties,
    Once instantiated, this class is set to both the Blender context, and
    assigned to jobs.BatchJobs.props.
    """
    collection = []
    thread = None

    jobs = bpy.props.CollectionProperty(
        type=JobDisplayProps,
        description="Job display list")

    index = bpy.props.IntProperty(
        description="Selected job index")

    more = bpy.props.StringProperty(
        description="Reference to load more jobs",
        default="")

    per_call = bpy.props.IntProperty(
        description="Jobs per call",
        default=5,
        min=1,
        soft_min=1,
        max=50,
        soft_max=50)

    def add_job(self, job, batch):
        """
        Add a job to both the display and object lists.

        """
        log = bpy.context.scene.batch_session.log
        log.debug("Adding job to ui list {0}".format(job.id))

        self.collection.append(job)
        self.jobs.add()
        entry = self.jobs[-1]
        if hasattr(job, 'display_name') and job.display_name:
            entry.name = job.display_name
        else:
            entry.name = job.id
        entry.timestamp = format_date(job)
        if hasattr(job.pool_info, 'pool_id') and job.pool_info.pool_id:
            entry.pool = job.pool_info.pool_id
        else:
            entry.pool = "auto pool"
        entry.status = job.state.value
        entry.id = job.id
        entry.percent = helpers.get_job_percent(batch, job.id)

        log.debug("Total jobs now {0}.".format(len(self.jobs)))

    def remove_selected(self):
        """
        Remove selected job from both display and object lists.

        """
        bpy.context.scene.batch_session.log.debug(
            "Removing index {0}.".format(self.index))

        self.collection.pop(self.index)
        self.jobs.remove(self.index)
        self.index = max(self.index - 1, 0)

    def reset(self):
        """
        Clear both job display and object lists.

        """
        self.collection.clear()
        self.jobs.clear()
        self.index = 0

        bpy.context.scene.batch_session.log.debug("Reset job lists.")


def register_props():
    """
    Register the jobs property classes and assign to the blender
    context under "batch_jobs".

    :Returns:
        - A :class:`.JobProps` object

    """
    bpy.types.Scene.batch_jobs = \
        bpy.props.PointerProperty(type=JobProps)

    return bpy.types.Scene.batch_jobs
