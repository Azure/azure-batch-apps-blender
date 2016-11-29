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

from batched_blender.utils import BatchOps, JobWatcher
from batched_blender.ui import ui_jobs
from batched_blender.props import props_jobs

import azure.batch as batch


class BatchJobs(object):
    """Manger for the retrival and display of the users job history."""

    pages = ["JOBS", "LOADING"]

    def __init__(self, manager, storage):
        self.batch = manager
        self.storage = storage
        self.ui = self._register_ui()
        props_jobs.register_props()
        self._register_ops()
        self.thread = None

    def _register_ops(self):
        """Registers each job history operator with a batch_jobs prefix.
        Job operations:
            - "page": Open the job monitoring view and initiate load job information.
            - "load_more": Load information on the next 5 jobs.
            - "refresh": Refresh the job information in the monitoring view.
            - "delete": Delete the selected jobs and their data.
            - "download": Download all the outputs of the selected job.
            - "loading": Modal loading of job information
        """
        BatchOps.register("jobs.page", "Jobs", self._jobs)
        BatchOps.register("jobs.load_more", "Load more jobs", self._more)
        BatchOps.register("jobs.refresh", "Refresh", self._refresh)
        BatchOps.register("jobs.delete", "Delete job", self._delete)
        BatchOps.register("jobs.download", "Delete job", self._download)
        BatchOps.register("jobs.loading", "Loading jobs",
                          modal=self._loading_modal, invoke=self._loading_invoke, _timer=None)

    def _register_ui(self):
        """Maps the jobs and loading pages with their corresponding
        ui functions.

        :rtype: dict of str, func pairs
        """
        def get_jobs_ui(name):
            name = name.lower()
            return getattr(ui_jobs, name)

        page_func = map(get_jobs_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _jobs(self, op, context, *args):
        """The execute method for the jobs.page operator.
        Sets the functions to be performed by the job data retrieval thread
        and invokes the thread. The view displays "LOADING" while
        the thread executes. Also resets the jobs displayed.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        session = context.scene.batch_session
        props = context.scene.batch_jobs
        props.reset()
        props.more = ""
        #if session.page == "HOME":  #TODO: Should I be doing this?
        session.page = "LOADING"
            
        jobs_thread = lambda: BatchOps.session(self.get_job_list)
        self.thread = threading.Thread(name="JobsThread", target=jobs_thread)
        bpy.ops.batch_jobs.loading('INVOKE_DEFAULT')
        return {'FINISHED'}

    def _loading_modal(self, op, context, event):
        """The modal method for the jobs.loading operator to handle running
        the downloading of the job history data in a separate thread to
        prevent the blocking of the Blender UI.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :param event: The blender invocation event.
        :type event: :class:`bpy.types.Event`
        :returns: Blender operator response; {'FINISHED'} if
         the thread has completed else {'RUNNING_MODAL'} to
         indicate the thread continues to run.
        :rtype: set
        """
        if event.type == 'TIMER':
            context.scene.batch_session.log.debug("JobsThread complete.")
            if not self.thread.is_alive():
                context.window_manager.event_timer_remove(op._timer)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def _loading_invoke(self, op, context, event):
        """The invoke method for the jobs.loading operator.
        Starts the job data retrieval thread.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :param event: The blender invocation event.
        :type event: :class:`bpy.types.Event`
        :returns: Blender operator response; {'RUNNING_MODAL'}
         to indicate the thread continues to run.
        :rtype: set
        """
        self.thread.start()
        context.scene.batch_session.log.debug("JobsThread initiated.")
        context.window_manager.modal_handler_add(op)
        op._timer = context.window_manager.event_timer_add(1, context.window)
        return {'RUNNING_MODAL'}

    def _more(self, op, context, *args):
        """The execute method for the jobs.more operator.
        Loads and additional 5 jobs to the display.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        self.get_job_list()
        return {'FINISHED'}

    def _refresh(self, op, context, *args):
        """The execute method for the jobs.refresh operator.
        Re-load the job history data. Resets the loaded job list to the
        first 5 entries.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        return bpy.ops.batch_jobs.page()

    def _delete(self, op, context, *args):
        """The execute method for the jobs.delete operator.
        Delete the currently selected jobs, then calls the jobs.page
        operator to refresh the job list in the display.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        props = bpy.context.scene.batch_jobs
        session = context.scene.batch_session
        delete = self.pending_delete()
        session.log.info("{0} jobs to be deleted".format(len(delete)))
        for index in delete:
            job = props.collection[index]
            display = props.jobs[index]
            try:
                session.log.debug("Deleting job {0}".format(job.id))
                self.batch.job.delete(job.id)
                session.log.debug("Deleting job outputs {0}".format(job.id))
                self.storage.delete_container(job.id, fail_not_exist=False)
            except Exception as exp:
                session.log.warning("Failed to delete {0}".format(job.id))
                session.log.warning(str(exp))
        return bpy.ops.batch_jobs.page()

    def _download(self, op, context):
        """The execute method for the jobs.download operator.
        Download all the outputs of the currently selected job to
        the allocated directory. This is launched in a separate
        process that runs independently of Blender.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        props = context.scene.batch_jobs
        session = context.scene.batch_session
        if props.output_dir and os.path.isdir(props.output_dir):
            session.log.info("Launching job watcher")
            JobWatcher(props.jobs[props.index].id, props.output_dir)
        else:
            session.log.warning("Invalid output directory.")
        return {'FINISHED'}

    def display(self, ui, layout):
        """Invokes the corresponding ui function depending on the session's
        current page.

        :param ui: The instance of the Interface panel class.
        :type ui: :class:`.Interface`
        :param layout: The layout object, used for creating and placing ui components.
        :type layout: :class:`bpy.types.UILayout`
        :returns: The result of the UI operator - usually {'FINISHED'}
        :rtype: set
        """
        return self.ui[bpy.context.scene.batch_session.page](ui, layout)

    def get_job_list(self):
        """Downloads data on 5 jobs. If invoked by the page operator this will be
        the first 5 jobs as provided by the service. Subsequent calls there-after
        (e.g. the more operator) will use the iterator URL to load additional
        job information. The view will also be refreshed.
        """
        props = bpy.context.scene.batch_jobs
        session = bpy.context.scene.batch_session
        session.log.debug("Getting job data")

        options = batch.models.JobListOptions(
            max_results=props.per_call,
            filter="startswith(id,'blender-render') or startswith(id,'luxblend-render')")
        job_iter = self.batch.job.list(options)
        if props.more:
            jobs = job_iter.get(props.more)
        else:
            jobs = job_iter.next()

        session.log.info("Retrieved {0} job listings.".format(len(jobs)))
        for job in jobs:
            props.add_job(job, self.batch)
        props.more = job_iter.next_link if job_iter.next_link else ""
        session.page = "JOBS"
        session.redraw()

    def pending_delete(self):
        """Get a list of the jobs that have been selected for delete. 

        :returns: Indexes of the selected jobs.
        :rtype: List of int
        """
        jobs = bpy.context.scene.batch_jobs.jobs
        return [i for i, job in enumerate(jobs) if job.delete_checkbox]
