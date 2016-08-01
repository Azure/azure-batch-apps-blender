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

import datetime
import logging
import random
import os
import string
import threading
import time
import uuid

from batched_blender.ui import ui_submission
from batched_blender.props import props_submission
from batched_blender.utils import BatchOps, BatchAsset

import azure.batch as batch
import azure.storage.blob as blob


class BatchSubmission(object):
    """
    Manages the creation and submission of a new job.
    """

    pages = ['SUBMIT', 'PROCESSING', 'SUBMITTED']

    def __init__(self, batch, uploader):

        self.batch = batch
        self.uploader = uploader
        self.job_file = None

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
        params = {}
        params["output"] = bpy.path.clean_name(self.props.display.title)
        params["start"] = self.props.display.start_f
        params["end"] = self.props.display.end_f
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
            pool = batch.models.PoolInformation(pool_id=self.props.display.pool_id)
            session.log.info("Using existing pool with ID: {0}".format(self.props.display.pool_id))
            return pool

        elif self.props.display.pool == {"create"}:
            session.log.info("Creating new pool.")
            pool_name = "Blender_Pool_{}".format(uuid.uuid4())
            commands = [
                "sudo apt-get update",
                "sudo apt-get install software-properties-common",
                "sudo add-apt-repository -y ppa:thomas-schiex/blender",
                "sudo apt-get update",
                "sudo apt-get -q -y install blender",
            ]
            pool_config = batch.models.VirtualMachineConfiguration(
                image_reference=batch.models.ImageReference(
                    'Canonical',
                    'UbuntuServer',
                    '14.04.4-LTS',
                    'latest'
                ),
                node_agent_sku_id='batch.node.ubuntu 14.04'
            )
            pool = batch.models.PoolAddParameter(
                pool_name,
                'BASIC_A1',
                display_name = "Blender_Pool_{}".format(datetime.datetime.now().isoformat()),
                virtual_machine_configuration=pool_config,
                target_dedicated=self.props.display.pool_size,
                start_task=batch.models.StartTask(
                    command_line="/bin/bash -c 'set -e; set -o pipefail; {}; wait'".format('; '.join(commands)),
                    run_elevated=True,
                    wait_for_success=True)
            )
            self.batch.pool.add(pool)
            pool = batch.models.PoolInformation(pool_id=pool_name)
            session.log.info("Created pool with ID: {0}".format(pool_name))

            self.props.display.pool = {"reuse"}
            self.props.display.pool_id = pool_name
            return pool

        elif self.props.display.pool == {"new"}:
            pool_name = "Blender_Auto_Pool_{}".format(datetime.datetime.now().isoformat())
            commands = [
                "sudo apt-get update",
                "sudo apt-get install software-properties-common",
                "sudo add-apt-repository -y ppa:thomas-schiex/blender",
                "sudo apt-get update",
                "sudo apt-get -q -y install blender",
            ]
            pool_config = batch.models.VirtualMachineConfiguration(
                image_reference=batch.models.ImageReference(
                    'Canonical',
                    'UbuntuServer',
                    '14.04.4-LTS',
                    'latest'
                ),
                node_agent_sku_id='batch.node.ubuntu 14.04'
            )
            pool_spec = batch.models.PoolSpecification(
                display_name=pool_name,
                vm_size='BASIC_A1',
                virtual_machine_configuration=pool_config,
                target_dedicated=self.props.display.pool_size,
                start_task=batch.models.StartTask(
                    command_line="/bin/bash -c 'set -e; set -o pipefail; {}; wait'".format('; '.join(commands)),
                    run_elevated=True,
                    wait_for_success=True)
            )
            auto_pool = batch.models.AutoPoolSpecification(
                auto_pool_id_prefix="Blender_auto_",
                pool_lifetime_option=batch.models.PoolLifetimeOption.job,
                keep_alive=False,
                pool=pool_spec
            )
            pool = batch.models.PoolInformation(auto_pool_specification=auto_pool)
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

    def upload_assets(self, assets):
        """
        Upload all assets required by the job.

        :Args:
            - new_job (:class:`JobSubmission`): The job for which all assets
              will be uploaded.
        
        :Raises:
            - ValueError if one or more assets fails to upload.
        """
        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
        session = bpy.context.scene.batch_session
        session.log.info("Uploading any required files.")
        uploaded = []
        failed = {}
        for a in assets:
            session.log.info("    uploading {}".format(a.name))
            try:
                a.upload()
                expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                blob_name = a.name + '_' + a.checksum
                sas_token = self.uploader.generate_blob_shared_access_signature(
                    container, blob_name, permission=blob.BlobPermissions.READ, expiry=expiry)
                sas_url = self.uploader.make_blob_url(container, blob_name, sas_token=sas_token)
                uploaded.append(batch.models.ResourceFile(file_path=a.name, blob_source=sas_url))
            except Exception as exp:
                failed[a.name] = exp
        if failed:
            [session.log.error("{0}: {1}".format(k, v)) for k, v in failed.items()]
            raise ValueError("Some required assets failed to upload.")
        return uploaded

    def configure_assets(self):
        """
        Gather the assets required for the job and allocate the job file from
        which the rendering will be run.
        """
        session = bpy.context.scene.batch_session
        assets = bpy.context.scene.batch_assets

        if assets.path == '':
            session.log.info("No assets referenced yet. Checking now.")
            bpy.ops.batch_assets.refresh()

            if session.page == 'ERROR':
                raise Exception("Failed to set up assets for job")

        uploading = [a for a in assets.collection if a._exists]
        if bpy.context.scene.batch_assets.temp:
            session.log.debug("Using temp blend file {0}".format(assets.path))
            bpy.ops.wm.save_as_mainfile(filepath=assets.path,
                                        check_existing=False,
                                        copy=True)

            self.job_file = BatchAsset(assets.path, self.uploader)
            uploading.append(self.job_file)
            
        else:
            session.log.debug("Using saved blend file {0}".format(assets.path))
            try:
                self.job_file = bpy.context.scene.batch_assets.get_jobfile()
            except ValueError:
                self.job_file = BatchAsset(assets.path, self.uploader)

        return self.upload_assets(uploading)

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

        job_name = self.get_title()
        job_id = 'blender_render_' + bpy.path.clean_name(datetime.datetime.now().isoformat())
        job = batch.models.JobAddParameter(job_id, self.get_pool(), display_name=job_name)
        job_assets = self.configure_assets()
        job_params = self.gather_parameters()
        job_tasks = []
        for i in range(job_params['start'], job_params['end']+1):
            task_id = "blender_{}_{}".format(job_params['output'], i)
            blender_cmd = "blender -b \"{0}\" -o \"{1}_####\" -F {2} -f {3} -t 0".format(
                self.job_file.name, job_params['output'], job_params['format'], i)
            linux_cmd = "/bin/bash -c 'set -e; set -o pipefail; {}; wait'".format(blender_cmd)
            job_tasks.append(batch.models.TaskAddParameter(
                task_id, linux_cmd, resource_files=job_assets)
            )

        try:
            self.batch.job.add(job)
            failed_tasks = []
            for i in range(0, len(job_tasks), 100):
                task_status = self.batch.task.add_collection(job_id, job_tasks[i:i+100])
                for task in task_status.value:
                    if task.status != batch.models.TaskAddStatus.success:
                        failed_tasks.append(task)

            if failed_tasks:
                [session.log.error("{0}: {1}".format(t.task_id, t.error)) for t in failed_tasks]
                
                raise ValueError("Some tasks failed to submit.")
        except Exception:
            try:
                self.batch.job.delete(job_id)
                session.log.info("Cleaned up failed job submission.")
            except Exceptopn as exp:
                session.log.info("Couldn't clean up job: {}".format(exp))
            raise



        session.log.info(
            "New job {!r} submitted with ID: {}".format(job_name, job_id))

        session.page = "SUBMITTED"
        assets.set_uploaded()
        session.redraw()
