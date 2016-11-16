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

import datetime
import os
import sys
import hashlib

import bpy
import isodate

from azure.batch import models
from azure.common import AzureHttpError

class BatchUtils(object):

    install_commands = [
            "sudo apt-get update",
            "sudo apt-get install software-properties-common",
            "sudo add-apt-repository -y ppa:thomas-schiex/blender",
            "sudo apt-get update",
            "sudo apt-get -q -y install blender",
            "sudo apt-get -y install python-pip",
            "pip install azure-storage"
            ]

    @staticmethod
    def current_time():
        now = datetime.datetime.now().isoformat()
        now = bpy.path.clean_name(now).replace('T', '-').replace('_', '-')
        return now

    @staticmethod
    def install_blender():
        start_task = models.StartTask(
                command_line="/bin/bash -c 'set -e; set -o pipefail; {}; wait'".format('; '.join(BatchUtils.install_commands)),
                run_elevated=True,
                wait_for_success=True)
        return start_task

    def get_pool_config(batch):
        """
        Gets a virtual machine configuration for the specified distro and version
        from the list of Azure Virtual Machines Marketplace images verified to be
        compatible with the Batch service.
        :param batch_service_client: A Batch service client.
        :type batch_service_client: `azure.batch.BatchServiceClient`
        :param str distro: The Linux distribution that should be installed on the
        compute nodes, e.g. 'Ubuntu' or 'CentOS'. Supports partial string matching.
        :param str version: The version of the operating system for the compute
        nodes, e.g. '15' or '14.04'. Supports partial string matching.
        :rtype: `azure.batch.models.VirtualMachineConfiguration`
        :return: A virtual machine configuration specifying the Virtual Machines
        Marketplace image and node agent SKU to install on the compute nodes in
        a pool.
        """
        distro = bpy.context.user_preferences.addons[__package__].preferences.vm_distro
        version = bpy.context.user_preferences.addons[__package__].preferences.vm_version
        node_agent_skus = batch.account.list_node_agent_skus()

        node_agent = next(agent for agent in node_agent_skus
                          for image_ref in agent.verified_image_references
                          if distro.lower() in image_ref.offer.lower() and
                          version.lower() in image_ref.sku.lower())

        img_ref = [image_ref for image_ref in node_agent.verified_image_references
                   if distro.lower() in image_ref.offer.lower() and
                   version.lower() in image_ref.sku.lower()][-1]

        vm_config = models.VirtualMachineConfiguration(
            image_reference=img_ref,
            node_agent_sku_id=node_agent.id)

        return vm_config

class BatchOps(object):
    """
    Static class for registering operators and executing them in a
    error-safe way.
    """

    @staticmethod
    def session(func, *args, **kwargs):
        """
        Execute an operator function.
        Can be invoke, execute, modal or a thread function.

        :Args:
            - func (function): The function to be executed along with
              any args and kwargs.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
            - If an exception is raised, returns {'CANCELLED'}.
        """
        session = bpy.context.scene.batch_session

        try:
            return func(*args, **kwargs)

        #except Exception: #TODO: Specify exceptopn
        #    session.log.error(
        #        "Warning: Session Expired - please log back in again.")

        #    session.page = "LOGIN"
        #    session.redraw()
        #    return {'CANCELLED'}

        except Exception as exp:
            session.page = "ERROR"
            session.log.error("Error occurred: {0}".format(exp))
            session.redraw()
            return {'CANCELLED'}

    @staticmethod
    def register(name, label, execute=None, modal=None, invoke=None, **kwargs):
        """
        Register a custom operator.

        :Args:
            - name (str): The id name of the operator (bl_idname).
            - label (str): The description of the operator (bl_label).

        :Kwargs:
            - execute (func): The execute function if applicable.
            - modal (func): The modal function if applicable.
            - invoke (func): The invoke function if applicable.
            - Any additional attributes or functions to be added to the class.

        :Returns:
            - The ID name of the registered operator with the
              prefix ``batch_``.

        """
        name = "batch_" + str(name)
        op_spec = {"bl_idname": name, "bl_label": label}

        if execute:
            def op_execute(self, context):
                return BatchOps.session(execute, self, context)

            op_spec["execute"] = op_execute

        if modal:
            def op_modal(self, context, event):
                return BatchOps.session(modal, self, context, event)

            op_spec["modal"] = op_modal

        if invoke:
            def op_invoke(self, context, event):
                return BatchOps.session(invoke, self, context, event)

            op_spec["invoke"] = op_invoke

        op_spec.update(kwargs)

        new_op = type("BatchOp",
                      (bpy.types.Operator, ),
                      op_spec)

        bpy.utils.register_class(new_op)
        return name

    @staticmethod
    def register_expanding(name, label, execute, modal=None,
                           invoke=None, **kwargs):
        """
        Register an operator that can be used as an expanding UI
        component (for example a job in the jobs page).

        :Args:
            - name (str): The id name of the operator (bl_idname).
            - label (str): The description of the operator (bl_label).
            - execute (func): The execute function.

        :Kwargs:
            - modal (func): The modal function if applicable.
            - invoke (func): The invoke function if applicable.
            - Any additional attributes or functions to be added to the class.

        :Returns:
            - The ID name of the registered operator with the
              prefix ``batch_``.

        """
        kwargs.update({'enabled':bpy.props.BoolProperty(default=False)})

        def op_execute(self, context):
            execute(self)
            self.enabled = not self.enabled
            return {'FINISHED'}

        return BatchOps.register(name, label, op_execute, modal,
                                     invoke, **kwargs)


class BatchAsset(object):

    def __init__(self, file_path, client):
        
        path = os.path.realpath(bpy.path.abspath(file_path))
        self.path = os.path.normpath(path)
        self.name = os.path.basename(self.path)
        
        self._client = client
        self._exists = os.path.exists(self.path)
        self.lastmodified = datetime.datetime.fromtimestamp(os.path.getmtime(self.path)) if self._exists else None
        self.checksum = self.get_checksum() if self._exists else None

    def get_checksum(self):
        """Generate md5 checksum for file.
        :Returns:
            - The md5 checksum of the file (bytes).
        """
        block_size = 128
        hasher = hashlib.md5()
        try:
            with open(self.path, 'rb') as user_file:
                while True:
                    file_block = user_file.read(block_size)
                    if not file_block:
                        break
                    hasher.update(file_block)
            return hasher.hexdigest()

        except (TypeError, EnvironmentError) as exp:
            bpy.context.scene.batch_session.log.info("Can't get checksum: {0}".format(exp))
            return None

    def get_last_modified(self):
        if self._exists:
            mod = os.path.getmtime(self.path)
            return datetime.datetime.fromtimestamp(mod)

    def is_uploaded(self):
        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
        bpy.context.scene.batch_session.log.info("Checking if asset is already uploaded...")
        uploaded_assets = [b.name for b in self._client.list_blobs(container, prefix=self.name)]
        bpy.context.scene.batch_session.log.info("Retrieved uploaded assets: {}".format(uploaded_assets))
        blob_name = self.name + '_' + self.checksum
        bpy.context.scene.batch_session.log.info("Uploaded {}: {}".format(blob_name, blob_name in uploaded_assets))
        return blob_name in uploaded_assets

    def upload(self):
        if self._exists and not self.is_uploaded():
            container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
            blob_name = self.name + '_' + self.checksum
            self._client.create_blob_from_path(container, blob_name, self.path)
        

