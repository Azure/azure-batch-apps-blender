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

import bpy
import isodate

from azure.common import AzureHttpError

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

        #try:
        return func(*args, **kwargs)

        #except Exception: #TODO: Specify exceptopn
        #    session.log.error(
        #        "Warning: Session Expired - please log back in again.")

        #    session.page = "LOGIN"
        #    session.redraw()
        #    return {'CANCELLED'}

        #except Exception as exp:
        #    session.page = "ERROR"
        #    session.log.error("Error occurred: {0}".format(exp))
        #    session.redraw()
        #    return {'CANCELLED'}

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
        component (for example a job in the history page).

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
        timestamp = self.get_last_modified()
        if timestamp:
            self.storage_ref = {
                'key': 'last-modified',
                'value': timestamp.isoformat()
                }
        else:
            self.storage_ref = None

    def _parse(self, timestamp):
        timestamp, _, micro= timestamp.partition(".")
        timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
        micro = int(micro.rstrip("Z"), 10)
        return timestamp + datetime.timedelta(microseconds=micro)

    def is_uploaded(self):
        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
        try:
            bpy.context.scene.batch_session.log.info("gathering properties")
            props = self._client.get_blob_properties(container, self.name)
            bpy.context.scene.batch_session.log.info("retrieved")
            print(props.metadata)
        except AzureHttpError:
            return False
        last_uploaded = props.metadata.get('value')
        print(last_uploaded)
        if not last_uploaded:
            print("done")
            return False
        print(type(last_uploaded))
        #print(isodate.parse_datetime(last_uploaded))
        if self._parse(last_uploaded) < self.get_last_modified():
            print("not up to date")
            return False
        print("uploaded")
        return True

    def get_last_modified(self):
        if self._exists:
            mod = os.path.getmtime(self.path)
            return datetime.datetime.fromtimestamp(mod)

    def upload(self):
        if self._exists and not self.is_uploaded():
            container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
            self._client.create_blob_from_path(container, self.name, self.path, metadata=self.storage_ref)
        

