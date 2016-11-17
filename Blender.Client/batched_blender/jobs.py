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
import os

import threading

from batched_blender.utils import BatchOps
from batched_blender.ui import ui_jobs
from batched_blender.props import props_jobs

import azure.batch as batch


class BatchJobs(object):
    """
    Manger for the retrival and display of the users job history.
    """

    pages = ["JOBS", "LOADING"]

    def __init__(self, manager):

        self.batch = manager
        self.ops = self._register_ops()
        self.props = self._register_props()
        self.ui = self._register_ui()

    def display(self, ui, layout):
        """
        Invokes the corresponding ui function depending on the session's
        current page.

        :Args:
            - ui (blender :class:`.Interface`): The instance of the Interface
              panel class.
            - layout (blender :class:`bpy.types.UILayout`): The layout object,
              derived from the Interface panel. Used for creating ui
              components.

        :Returns:
            - Runs the display function for the applicable page.
        """
        return self.ui[bpy.context.scene.batch_session.page](ui, layout)

    def _register_props(self):
        """
        Registers and retrieves the jobs property objects.
        The dispaly properties are defined in a subclass which is assigned
        to the scene.batch_jobs context.

        :Returns:
            - :class:`.JobProps`
        """
        props = props_jobs.register_props()
        return props

    def _register_ops(self):
        """
        Registers each job history operator with a batch_jobs prefix.

        :Returns:
            - A list of the names (str) of the registered job history
              operators.
        """
        ops = []
        ops.append(BatchOps.register("jobs.page",
                                     "Jobs",
                                     self._jobs))
        ops.append(BatchOps.register("jobs.load_more",
                                     "Load more jobs",
                                     self._more))
        ops.append(BatchOps.register("jobs.refresh",
                                     "Refresh",
                                     self._refresh))
        ops.append(BatchOps.register("jobs.delete",
                                     "Delete job",
                                     self._delete))
        #ops.append(BatchOps.register("jobs.outputs",
        #                             "Delete job",
        #                             self._outputs))
        #ops.append(BatchOps.register("jobs.download",
        #                             "Delete job",
        #                             self._download))
        ops.append(BatchOps.register("jobs.loading",
                                     "Loading jobs",
                                     modal=self._loading_modal,
                                     invoke=self._loading_invoke,
                                     _timer=None))
        return ops

    def _register_ui(self):
        """
        Matches the jobs and loading pages with their corresponding
        ui functions.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_jobs_ui(name):
            name = name.lower()
            return getattr(ui_jobs, name)

        page_func = map(get_jobs_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _loading_modal(self, op, context, event):
        """
        The modal method for the jobs.loading operator to handle running
        the downloading of the job history data in a separate thread to
        prevent the blocking of the Blender UI.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.
            - event (:class:`bpy.types.Event`): The blender invocation event.

        :Returns:
            - If the thread has completed, the Blender-specific value
              {'FINISHED'} to indicate the operator has completed its action.
            - Otherwise the Blender-specific value {'RUNNING_MODAL'} to
              indicate the operator wil continue to process after the
              completion of this function.
        """
        if event.type == 'TIMER':
            context.scene.batch_session.log.debug("JobsThread complete.")
            if not self.props.thread.is_alive():
                context.window_manager.event_timer_remove(op._timer)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _loading_invoke(self, op, context, event):
        """
        The invoke method for the jobs.loading operator.
        Starts the job data retrieval thread.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.
            - event (:class:`bpy.types.Event`): The blender invocation event.

        :Returns:
            - Blender-specific value {'RUNNING_MODAL'} to indicate the operator
              wil continue to process after the completion of this function.
        """
        self.props.thread.start()
        context.scene.batch_session.log.debug("JobsThread initiated.")

        context.window_manager.modal_handler_add(op)
        op._timer = context.window_manager.event_timer_add(1, context.window)
        return {'RUNNING_MODAL'}

    def _jobs(self, op, context, *args):
        """
        The execute method for the jobs.page operator.
        Sets the functions to be performed by the job data retrieval thread
        and updates the session page to "LOADING" while the thread executes.

        Also resets the job display paging controls.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batch_session
        self.props = context.scene.batch_jobs
        self.props.reset()
        self.props.more = ""
        if session.page == "HOME":
            session.page = "LOADING"
            
        jobs_thread = lambda: BatchOps.session(self.get_job_list)
        self.props.thread = threading.Thread(name="JobsThread",
                                             target=jobs_thread)

        bpy.ops.batch_jobs.loading('INVOKE_DEFAULT')
        return {'FINISHED'}

    def _more(self, op, context, *args):
        """
        The execute method for the jobs.more operator.
        Resets the job display paging controls to display the subsequent jobs
        in the list and re-loads the accompanying job data.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        self.get_job_list()
        return {'FINISHED'}

    def _refresh(self, op, context, *args):
        """
        The execute method for the jobs.refresh operator.
        Re-loads the current job data.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        return bpy.ops.batch_jobs.page()

    def _delete(self, op, context, *args):
        """
        The execute method for the jobs.delete operator.
        Delete the currently selected job, then calls the jobs.page
        operator to refresh the job list in the display.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batch_session
        delete = self.pending_delete()

        session.log.info("{0} jobs to be deleted".format(len(delete)))

        for index in delete:
            job = self.props.collection[index]
            display = self.props.jobs[index]

            try:
                session.log.debug("Deleting job {0}".format(job.id))
                self.batch.job.delete(job.id)
            except Exception as exp:
                session.log.warning("Failed to delete {0}".format(job.id))
                session.log.warning(str(exp))

        return bpy.ops.batch_jobs.page()

    def get_job_list(self):
        """
        Downlaods a set of job data based on index and default per call parameter,
        assigns it to the property job_list and redraws the JOBS page to
        display the new data.

        Each job is also registered as an operator class.
        #TODO: Unregister previous job classes?
        """
        session = bpy.context.scene.batch_session
        session.log.debug("Getting job data")

        options = batch.models.JobListOptions(
            max_results=self.props.per_call,
            filter="startswith(id,'blender_render')")
        job_iter = self.batch.job.list(options)
        if self.props.more:
            jobs = job_iter.get(self.props.more)
        else:
            jobs = job_iter.next()
        session.log.info("Retrieved {0} job listings.".format(len(jobs)))

        for job in jobs:
            self.props.add_job(job, self.batch)

        self.props.more = job_iter.next_link if job_iter.next_link else ""
        session.page = "JOBS"
        session.redraw()

    def pending_delete(self):
        """
        Get a list of the jobs that have been selected for delete. 

        :Returns:
            - A list of the indexes (int) of the items in the display
              job list that have been selected for delete.
        """

        delete_me = []

        for index, job in enumerate(self.props.jobs):
            if job.delete_checkbox:
                delete_me.append(index)

        return delete_me
