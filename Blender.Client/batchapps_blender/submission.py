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

import logging
import random
import os
import string
import threading
import time

from batched_blender.ui import ui_submission
from batched_blender.props import props_submission
from batched_blender.utils import BatchOps, BatchAsset


class BatchSubmission(object):
    """
    Manages the creation and submission of a new job.
    """

    pages = ['SUBMIT', 'PROCESSING', 'SUBMITTED']

    def __init__(self, batch, uploader):

        self.batch = batch
        self.uploader = uploader

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
        Registers and retrieves the submission property objects.page
        The dispaly properties are defined in a subclass which is assigned
        to the scene.batch_submission context.

        :Returns:
            - :class:`.SubmissionProps`
        """
        props = props_submission.register_props()
        return props
        
    def _register_ops(self):
        """
        Registers each job submission operator with a batch_submission
        prefix.

        :Returns:
            - A list of the names (str) of the registered job submission
              operators.
        """
        ops = []
        ops.append(BatchOps.register("submission.page",
                                         "Create new job",
                                         self._submission))
        ops.append(BatchOps.register("submission.start",
                                         "Submit job",
                                         self._start))
        ops.append(BatchOps.register("submission.processing",
                                         "Submitting new job",
                                         modal=self._processing_modal,
                                         invoke=self._processing_invoke,
                                         _timer=None))
        return ops

    def _register_ui(self):
        """
        Matches the submit, processing and completed pages with their
        corresponding ui functions.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_ui(name):
            name = name.lower()
            return getattr(ui_submission, name)

        page_func = map(get_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _processing_modal(self, op, context, event):
        """
        The modal method for the submission.processing operator to handle
        running the submission of a job in a separate thread to prevent
        the blocking of the Blender UI.

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
            context.scene.batch_session.log.debug("SubmitThread complete.")
            if not self.props.thread.is_alive():
                context.window_manager.event_timer_remove(op._timer)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _processing_invoke(self, op, context, event):
        """
        The invoke method for the submission.processing operator.
        Starts the job submission thread.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.
            - event (:class:`bpy.types.Event`): The blender invocation event.

        :Returns:
            - Blender-specific value {'RUNNING_MODAL'} to indicate the operator
              will continue to process after the completion of this function.
        """
        self.props.thread.start()
        context.scene.batch_session.log.debug("SubmitThread initiated.")

        context.window_manager.modal_handler_add(op)
        op._timer = context.window_manager.event_timer_add(1, context.window)
        return {'RUNNING_MODAL'}

    def _start(self, op, context, *args):
        """
        The execute method for the submission.start operator.
        Sets the functions to be performed by the job submission thread
        and updates the session page to "PROCESSING" while the thread
        executes.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        submit_thread = lambda: BatchOps.session(self.submit_job)
        self.props.thread = threading.Thread(name="SubmitThread",
                                             target=submit_thread)

        bpy.ops.batch_submission.processing('INVOKE_DEFAULT')

        if context.scene.batch_session.page == "SUBMIT":
            context.scene.batch_session.page = "PROCESSING"
        
        return {'FINISHED'}

    def _submission(self, op, context, *args):
        """
        The execute method for the submission.page operator.
        Sets the page to SUBMIT.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        bpy.context.scene.batch_session.page = "SUBMIT"
        self.valid_scene(context)

        return {'FINISHED'}

    def valid_scene(self, context):
        """
        Display warnings if the selected frame range of format are invalid.

        :Args:
            - context (:class:`bpy.types.Context`): The current blender
              context.

        """
        if not context.scene.batch_submission.valid_range:
            context.scene.batch_session.log.warning(
                "Selected frame range falls outside global range.")

        if not context.scene.batch_submission.valid_format:
            context.scene.batch_session.log.warning(
                "Invalid output format - using PNG instead.")

    def gather_parameters(self):
        """
        Gathers the operating parameters for the job.

        :Returns:
            - A dictionary of parameters (stR).
        """
        session = bpy.context.scene.batch_session
        params = {}

        params["output"] = bpy.path.clean_name(self.props.display.title)
        params["start"] = str(self.props.display.start_f)
        params["end"] = str(self.props.display.end_f)
        params["format"] = self.props.display.supported_formats[
            self.props.display.image_format]

        return params

    def get_pool(self):
        """
        Retrieve the pool id to be used for the job, or create an auto
        pool if necessary.

        :Returns:
            - The pool id (string).
        """
        session = bpy.context.scene.batch_session
        pools = bpy.context.scene.batch_pools
        pool = None

        if self.props.display.pool == {"reuse"} and self.props.display.pool_id:
            pool = self.props.display.pool_id
            session.log.info("Using existing pool with ID: {0}".format(pool))
            return pool

        elif self.props.display.pool == {"create"}:
            session.log.info("Creating new pool.")

            pool = self.batch_pool.create(target_size=pools.pool_size)
            session.log.info("Created pool with ID: {0}".format(pool.id))

            self.props.display.pool = {"reuse"}
            self.props.display.pool_id = pool.id
            return pool

        elif self.props.display.pool == {"new"}:
            return pool

        else:
            raise ValueError("Invalid pool settings.")

    def get_title(self):
        """
        Retrieve the job title if specified, or set to "Untitled_Job".
        """
        if self.props.display.title == "":
            self.props.display.title = "Untitled_Job"

        else:
            self.props.display.title = bpy.path.clean_name(
                self.props.display.title)

        return self.props.display.title

    def upload_assets(self, new_job):
        """
        Upload all assets required by the job.

        :Args:
            - new_job (:class:`JobSubmission`): The job for which all assets
              will be uploaded.
        
        :Raises:
            - ValueError if one or more assets fails to upload.
        """
        session = bpy.context.scene.batch_session
        session.log.info("Uploading any required files.")

        failed = new_job.required_files.upload()
        if failed:
            [session.log.error("{0}: {1}".format(f[0], f[1])) for f in failed]
            raise ValueError("Some required assets failed to upload.")

    def configure_assets(self, new_job):
        """
        Gather the assets required for the job and allocate the job file from
        which the rendering will be run.
        """
        session = bpy.context.scene.batch_session
        assets = bpy.context.scene.batch_assets

        if assets.path == '':
            session.log.info("No assets referenced yet. Checking now.")
            bpy.ops.batch_assets.refresh()

            #if session.page == 'LOGIN':
            #    raise Exception("AAD token has expired") #TODO: SessionExpiredException

            if session.page == 'ERROR':
                raise Exception("Failed to set up assets for job")

        file_set = self.batch_files.create_file_set(assets.collection)
        new_job.add_file_collection(file_set)

        if bpy.context.scene.batch_assets.temp:
            session.log.debug("Using temp blend file {0}".format(assets.path))
            bpy.ops.wm.save_as_mainfile(filepath=assets.path,
                                        check_existing=False,
                                        copy=True)
            jobfile = BatchAsset(assets.path, self.uploader)

            new_job.add_file(jobfile)
            new_job.set_job_file(-1)
            
        else:
            session.log.debug("Using saved blend file {0}".format(assets.path))
            try:
                jobfile = bpy.context.scene.batch_assets.get_jobfile()
            except ValueError:
                jobfile = BatchAsset(assets.path, self.uploader)

            new_job.set_job_file(jobfile)

        self.upload_assets(new_job)

    def submit_job(self):
        """
        The job submission process including the uploading of any required
        assets and the instantiation of an auto-pool if necessary.

        Sets the page to COMPLETE if successful.
        """
        self.props.display = bpy.context.scene.batch_submission
        session = bpy.context.scene.batch_session
        assets = bpy.context.scene.batch_assets
        session.log.info("Starting new job submission.")
        self.valid_scene(bpy.context)

        new_job = self.batch_job.create_job(self.get_title())
        self.configure_assets(new_job)

        new_job.pool = self.get_pool()
        new_job.instances = self.props.display.pool_size
        new_job.params = self.gather_parameters()
        new_job.params['jobfile'] = new_job.source

        session.log.info("Preparation complete, submitting job.")
        session.log.debug("Submission details: {0}".format(
            new_job._create_job_message()))

        submission = new_job.submit()
        session.log.info(
            "New job submitted with ID: {0}".format(submission['id']))

        session.page = "SUBMITTED"
        assets.set_uploaded()
        session.redraw()
