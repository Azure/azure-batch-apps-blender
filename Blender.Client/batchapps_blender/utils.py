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

from http.server import BaseHTTPRequestHandler
from urllib.parse import unquote

import sys
import socket

from batchapps.exceptions import SessionExpiredException

class BatchAppsOps(object):
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
            - If a :class:`batchapps.exceptions.SessionExpiredException` is
              raised, returns {'CANCELLED'}.
        """
        session = bpy.context.scene.batchapps_session

        try:
            return func(*args, **kwargs)

        except SessionExpiredException:
            session.log.error(
                "Warning: Session Expired - please log back in again.")

            session.page = "LOGIN"
            session.redraw()
            return {'CANCELLED'}

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
              prefix ``batchapps_``.

        """
        name = "batchapps_" + str(name)
        op_spec = {"bl_idname": name, "bl_label": label}

        if execute:
            def op_execute(self, context):
                return BatchAppsOps.session(execute, self, context)

            op_spec["execute"] = op_execute

        if modal:
            def op_modal(self, context, event):
                return BatchAppsOps.session(modal, self, context, event)

            op_spec["modal"] = op_modal

        if invoke:
            def op_invoke(self, context, event):
                return BatchAppsOps.session(invoke, self, context, event)

            op_spec["invoke"] = op_invoke

        op_spec.update(kwargs)

        new_op = type("BatchAppsOp",
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
              prefix ``batchapps_``.

        """
        kwargs.update({'enabled':bpy.props.BoolProperty(default=False)})

        def op_execute(self, context):
            execute(self)
            self.enabled = not self.enabled
            return {'FINISHED'}

        return BatchAppsOps.register(name, label, op_execute, modal,
                                     invoke, **kwargs)

class OAuthRequestHandler(BaseHTTPRequestHandler):
    """
    A custom HTTP server request handler to handler the AAD redirects
    for authentication.
    """

    def log_message(self, format, *args):
        """
        Override logging to silence messages from base class.
        """
        return

    def do_GET(s):
        """
        Handle a GET request from the AAD server. If a code is returned,
        assigns to the batchapps_auth.code property and returns status 200
        along with a simple HTML message.
        If an error is returned, assigns to properties for logging the
        returns status 401 and an HTML message.
        """
        session = bpy.context.scene.batchapps_session
        session.log.debug("Received AAD request {0}".format(s.path))

        if s.path.startswith('/?code'):
            bpy.context.scene.batchapps_auth.code = s.path

            s.send_response(200)
            s.send_header("Content-type", "text/html")
            s.end_headers()

            s.wfile.write(b"<html><head><title>Authentication Successful</title></head>")
            s.wfile.write(b"<body><p>Authentication successful.</p>")
            s.wfile.write(b"<p>You can now return to Blender where your log in</p>")
            s.wfile.write(b"<p>will be complete in just a moment.</p>")
            s.wfile.write(b"</body></html>")

        else:
            bpy.context.scene.batchapps_auth.code = s.path

            s.send_response(401)
            s.send_header("Content-type", "text/html")
            s.end_headers()

            s.wfile.write(b"<html><head><title>Authentication Failed</title></head>")
            s.wfile.write(b"<body><p>Authentication unsuccessful.</p>")
            s.wfile.write(b"<p>Check the Blender console for details.</p>")
            s.wfile.write(b"</body></html>")