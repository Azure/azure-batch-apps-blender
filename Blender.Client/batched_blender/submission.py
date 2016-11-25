#-------------------------------------------------------------------------
#
# Azure Batch Blender Addon
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

import datetime
import logging
import random
import os
import string
import threading
import time

import bpy

from batched_blender.ui import ui_submission
from batched_blender.props import props_submission
from batched_blender.utils import BatchOps, BatchAsset, BatchUtils

from azure.batch import models
from azure.storage import blob


class BatchSubmission(object):
    """Manages the creation and submission of a new job."""

    pages = ['SUBMIT', 'PROCESSING', 'SUBMITTED']
    render_cmd = "render.py"
    merge_cmd = "merge.py"

    def __init__(self, batch, uploader):
        self.batch = batch
        self.uploader = uploader
        self.job_file = None
        self.thread = None
        self.ui = self._register_ui()
        props_submission.register_props()
        self._register_ops()

    def _register_ops(self):
        """Registers each job submission operator with a batch_submission
        prefix. Page operators:
            - "page": Open the job configuration and submission view.
            - "start": Submit the new job submission thread.
            - "processing": Processes and submits the job to the service.
        """
        BatchOps.register("submission.page", "Configure a new job", self._submission)
        BatchOps.register("submission.start", "Start job submission", self._start)
        BatchOps.register("submission.processing", "Internal: Create new job",
                          modal=self._processing_modal, invoke=self._processing_invoke, _timer=None)
    
    def _register_ui(self):
        """Maps the job configure, submitting and submission completed
        pages with their corresponding ui functions.

        :rtype: dict of str, func pairs
        """
        def get_ui(name):
            name = name.lower()
            return getattr(ui_submission, name)

        page_func = map(get_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _submission(self, op, context, *args):
        """The execute method for the submission.page operator.
        Displays the job configuration and submission view.
        Sets the page to 'SUBMIT'.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        bpy.context.scene.batch_session.page = "SUBMIT"
        self.valid_scene(context)
        return {'FINISHED'}

    def _start(self, op, context, *args):
        """The execute method for the submission.start operator.
        Sets the functions to be performed by the job submission thread
        and updates the session page to 'PROCESSING' while the thread
        executes.

        :param op: An instance of the current operator class.
        :type op: :class:`bpy.types.Operator`
        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        :returns: Blender operator response; {'FINISHED'} if
         successful else {'CANCELLED'}
        :rtype: set
        """
        submit_thread = lambda: BatchOps.session(self.submit_job)
        self.thread = threading.Thread(name="SubmitThread", target=submit_thread)
        bpy.ops.batch_submission.processing('INVOKE_DEFAULT')
        if context.scene.batch_session.page == "SUBMIT":
            context.scene.batch_session.page = "PROCESSING"
        return {'FINISHED'}

    def _processing_modal(self, op, context, event):
        """The modal method for the submission.processing operator to handle
        running the submission of a job in a separate thread to prevent
        the blocking of the Blender UI.

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
            context.scene.batch_session.log.debug("SubmitThread complete.")
            if not self.thread.is_alive():
                context.window_manager.event_timer_remove(op._timer)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def _processing_invoke(self, op, context, event):
        """The invoke method for the submission.processing operator.
        Starts the job submission thread.

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
        context.scene.batch_session.log.debug("SubmitThread initiated.")
        context.window_manager.modal_handler_add(op)
        op._timer = context.window_manager.event_timer_add(1, context.window)
        return {'RUNNING_MODAL'}

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

    def valid_scene(self, context):
        """Display warnings if the selected frame range of format are invalid.

        :param context: The current Blender scene context.
        :type context: :class:`bpy.types.Context`
        """
        if not context.scene.batch_submission.valid_range:
            context.scene.batch_session.log.warning(
                "Selected frame range falls outside global range.")
        if not context.scene.batch_submission.valid_format:
            context.scene.batch_session.log.warning(
                "Invalid output format - using PNG instead.")

    def get_pool(self):
        """Retrieve the pool reference to be used for the job, or create
        an auto pool if necessary.

        :returns: The pool reference.
        :rtype: :class:`azure.batch.models.PoolInformation`
        """
        session = bpy.context.scene.batch_session
        props = bpy.context.scene.batch_submission
        lux = bpy.context.scene.render.engine == 'LUXRENDER_RENDER'
        pool = None

        if props.pool_type == {"reuse"} and props.pool_id:
            pool = models.PoolInformation(pool_id=props.pool_id)
            session.log.info("Using existing pool with ID: {0}".format(props.pool_id))
            return pool

        elif props.pool_type == {"create"}:
            pool_id = "blender_pool_{}".format(BatchUtils.current_time())
            session.log.info("Creating new pool {}".format(pool_id))
            bpy.ops.batch_pools.create(id=pool_id)
            pool = models.PoolInformation(pool_id=pool_id)
            session.log.info("Created pool with ID: {0}".format(pool_id))
            props.pool_type = {"reuse"}
            props.pool_id = pool_id
            return pool

        elif props.pool_type == {"auto"}:
            name = "Blender Auto Pool {}".format(BatchUtils.current_time())
            session.log.info("Creating auto-pool {}".format(pool_name))
            auto_pool = BatchUtils.get_auto_pool(self.batch, name, lux)
            pool = models.PoolInformation(auto_pool_specification=auto_pool)
            return pool

        else:
            raise ValueError("Invalid pool settings.")

    def upload_assets(self, assets):
        """Upload all assets required by the job. The assets will then
        be converted to ResourceFile references for job submission.

        :param assets: The assets to be uploaded.
        :type assets: List of `.BatchAsset` objects.
        :returns: All the assets references to include with the job.
        :rtype: A list of :class:`azure.batch.model.ResourceFile` objects.
        :raises: ValueError if one or more assets fails to upload.
        """
        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
        session = bpy.context.scene.batch_session
        session.log.info("Uploading any required files.")
        uploaded = []
        failed = {}
        for asset in assets:
            session.log.info("    uploading {}".format(asset.name))
            try:
                asset.upload()
                expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                blob_name = asset.name + '_' + asset.checksum
                sas_token = self.uploader.generate_blob_shared_access_signature(
                    container, blob_name, permission=blob.BlobPermissions.READ, expiry=expiry)
                sas_url = self.uploader.make_blob_url(container, blob_name, sas_token=sas_token)
                uploaded.append(models.ResourceFile(file_path=asset.name, blob_source=sas_url))
            except Exception as exp:
                failed[asset.name] = exp
        if failed:
            [session.log.error("{0}: {1}".format(k, v)) for k, v in failed.items()]
            raise ValueError("Some required assets failed to upload.")
        return uploaded

    def configure_assets(self):
        """Gather the assets required for the job and allocate the .blend file
        that will be rendered.

        :returns: All the assets references to include with the job.
        :rtype: A list of :class:`azure.batch.model.ResourceFile` objects.
        """
        session = bpy.context.scene.batch_session
        assets = bpy.context.scene.batch_assets
        if assets.path == '':
            session.log.info("No assets referenced yet. Checking now.")
            bpy.ops.batch_assets.refresh()
            if session.page == 'ERROR':
                raise Exception("Failed to set up assets for job")

        uploading = [a for a in assets.collection if a._exists]
        render_script = os.path.join(os.path.dirname(__file__), "scripts", self.render_cmd)
        uploading.append(BatchAsset(render_script, self.uploader))

        if bpy.context.scene.batch_assets.temp:
            session.log.debug("Using temp blend file {0}".format(assets.path))
            bpy.ops.wm.save_as_mainfile(filepath=assets.path, check_existing=False, copy=True)
            self.job_file = BatchAsset(assets.path, self.uploader)
            uploading.append(self.job_file)
        else:
            try:
                session.log.debug("Using saved blend file {0}".format(assets.path))
                self.job_file = bpy.context.scene.batch_assets.get_jobfile()
            except ValueError:
                self.job_file = BatchAsset(assets.path, self.uploader)
                uploading.append(self.job_file)
        return self.upload_assets(uploading)

    def merge_task(self, tasks, prefs):
        merge_script = os.path.join(os.path.dirname(__file__), "scripts", self.merge_cmd)
        all_tasks = [t.id for t in tasks]
        blender_cmd = "blender -b -P \"{}\"".format(self.merge_cmd)
        linux_cmd = "/bin/bash -c 'set -e; set -o pipefail; {}; wait'".format(blender_cmd)
        return models.TaskAddParameter("merge", linux_cmd,
            display_name="Merge Task",
            depends_on={'task_ids': all_tasks},
            resource_files = self.upload_assets([BatchAsset(render_script, self.uploader)]),
            environment_settings=[
                models.EnvironmentSetting("STORAGE_ACCOUNT", prefs.storage),
                models.EnvironmentSetting("STORAGE_KEY", prefs.storage_key)])

    def submit_job(self):
        """The job submission process including the uploading
        of any required assets and the configuration of an
        auto-pool if necessary. Sets the page to 'COMPLETE' if successful.
        """
        props = bpy.context.scene.batch_submission
        session = bpy.context.scene.batch_session
        pools = bpy.context.scene.batch_pools
        assets = bpy.context.scene.batch_assets
        prefs = bpy.context.user_preferences.addons['batched_blender'].preferences
        lux = bpy.context.scene.render.engine == 'LUXRENDER_RENDER'
        session.log.info("Starting new job submission.")
        self.valid_scene(bpy.context)

        job_id = 'blender-render-{}'.format(BatchUtils.current_time())
        if lux:
            job_id = 'luxblend-render-{}'.format(BatchUtils.current_time())
        job_name = props.title if props.title else job_id
        job = models.JobAddParameter(
            job_id, 
            self.get_pool(),
            display_name=job_name,
            on_all_tasks_complete='terminateJob',
            uses_task_dependencies=True)

        if props.video_merge:
            job.metadata = [{'name':'video_merge', 'value':'true'}]
        job_assets = self.configure_assets()

        session.log.info("Setting up job output storage container: {}".format(job_id))
        self.uploader.create_container(job.id, fail_on_exist=False)

        #TODO: Support frame step
        job_tasks = []
        if lux:
            session.log.debug("Running LuxRender job")
            for task in range(props.start_f, props.end_f+1):
                env_var = "%AZ_BATCH_APP_PACKAGE_{}%".format(pools.lux_app_image.upper())
                if pools.lux_app_version != 'default':
                    env_var += "#{}".format(pools.lux_app_version.upper())
                blender_cmd = "cmd /c {}\\Blender\\blender.exe -b {} -P render.py < NUL".format(env_var, self.job_file.name)
                job_tasks.append(models.TaskAddParameter(
                    str(task).rjust(len(str(props.end_f)), '0'),
                    blender_cmd,
                    resource_files=job_assets,
                    display_name="Frame {}".format(task),
                    environment_settings=[
                        models.EnvironmentSetting("HALT_SAMPLES", str(props.lux_samples)),
                        models.EnvironmentSetting("STORAGE_ACCOUNT", prefs.storage),
                        models.EnvironmentSetting("STORAGE_KEY", prefs.storage_key)]))

        else:
            for task in range(props.start_f, props.end_f+1):
                blender_cmd = "blender -b \"{}\" -P \"{}\"".format(self.job_file.name, self.render_cmd)
                linux_cmd = "/bin/bash -c 'set -e; set -o pipefail; {}; wait'".format(blender_cmd)
                job_tasks.append(models.TaskAddParameter(
                    str(task).rjust(len(str(props.end_f)), '0'),
                    linux_cmd,
                    resource_files=job_assets,
                    display_name="Frame {}".format(task),
                    environment_settings=[
                        models.EnvironmentSetting("STORAGE_ACCOUNT", prefs.storage),
                        models.EnvironmentSetting("STORAGE_KEY", prefs.storage_key)]))
            if props.video_merge:
                job_tasks.append(self.merge_task(job_tasks, prefs))
        try:
            session.log.debug("Adding job: {}".format(job_id))
            self.batch.job.add(job)
            failed_tasks = []
            for i in range(0, len(job_tasks), 100):
                task_status = self.batch.task.add_collection(job_id, job_tasks[i:i+100])
                for task in task_status.value:
                    if task.status != models.TaskAddStatus.success:
                        failed_tasks.append(task)
            if failed_tasks:
                [session.log.error("{0}: {1}".format(t.task_id, t.error)) for t in failed_tasks]
                raise ValueError("Some tasks failed to submit.")
        except Exception:
            try:
                self.batch.job.delete(job_id)
                self.uploader.delete_container(job.id, fail_not_exist=False)
                session.log.info("Cleaned up failed job submission.")
            except Exceptopn as exp:
                session.log.info("Couldn't clean up job: {}".format(exp))
            raise

        session.log.info(
            "New job {!r} submitted with ID: {}".format(props.title, job_id))
        session.page = "SUBMITTED"
        assets.set_uploaded()
        session.redraw()
