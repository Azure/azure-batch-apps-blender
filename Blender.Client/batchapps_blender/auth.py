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

import webbrowser
import logging
import threading

from http.server import HTTPServer
from urllib.parse import unquote

from batchapps_blender.utils import (
    BatchAppsOps,
    OAuthRequestHandler)

from batchapps_blender.ui import ui_auth
from batchapps_blender.props import props_auth

from batchapps import AzureOAuth
from batchapps.exceptions import (
    AuthenticationException,
    InvalidConfigException)


TIMEOUT = 60 # 1 minute

class BatchAppsAuth(object):
    """
    Managers authentication of the session for the BatchApps Blender Addon.
    Will attempt to sign in automatically based on data available in the
    Batch Apps configuration. If unsuccessful, will prompt use to sign in
    via a web browser.
    """

    pages = ["LOGIN", "REDIRECT"]

    def __init__(self):

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
        return self.ui[bpy.context.scene.batchapps_session.page](ui, layout)


    def _register_props(self):
        """
        Registers and retrieves the auth property objects.
        These properties are assigned to the scene.batchapps_auth context.

        :Returns:
            - :class:`.AuthProps`
        """
        props = props_auth.register_props()
        return props
        

    def _register_ops(self):
        """
        Registers each auth operator with a batchapps_auth prefix.

        :Returns:
            - A list of the names (str) of the registered auth operators.
        """
        ops = []
        ops.append(BatchAppsOps.register("auth.login",
                                         "Login",
                                         self._login))
        ops.append(BatchAppsOps.register("auth.logout",
                                         "Logout",
                                         self._logout))
        ops.append(BatchAppsOps.register("auth.redirect",
                                         "Redirecting authentication",
                                         modal=self._redirect_modal,
                                         invoke=self._redirect_invoke,
                                         _timer=None))
        return ops


    def _register_ui(self):
        """
        Matches the login and redirection pages with their corresponding
        ui functions.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_auth_ui(name):
            name = name.lower()
            return getattr(ui_auth, name)

        page_func = map(get_auth_ui, self.pages)
        return dict(zip(self.pages, page_func))
        
    def _redirect_modal(self, op, context, event):
        """
        The modal method for the auth.redirect operator to handle running
        the authentication redirection server in a separate thread to
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
            context.scene.batchapps_session.log.debug("AuthThread complete.")
            if not self.props.thread.is_alive():
                context.window_manager.event_timer_remove(op._timer)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _redirect_invoke(self, op, context, event):
        """
        The invoke method for the auth.redirect operator.
        Starts the authentication redirect thread.

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
        context.scene.batchapps_session.log.debug("AuthThread initiated.")

        context.window_manager.modal_handler_add(op)
        op._timer = context.window_manager.event_timer_add(1, context.window)
        return {'RUNNING_MODAL'}

    def _login(self, op, context, *args):
        """
        The execute method for the auth.login operator.
        Sets the functions to per performed by the authentication thread and
        updates the session page to "REDIRECT" while the thread executes.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        auth_thread = lambda: BatchAppsOps.session(self.web_authentication)
        self.props.thread = threading.Thread(name="AuthThread",
                                             target=auth_thread)

        bpy.ops.batchapps_auth.redirect('INVOKE_DEFAULT')

        if context.scene.batchapps_session.page == "LOGIN":
            context.scene.batchapps_session.page = "REDIRECT"

        return {'FINISHED'}

    def _logout(self, op, context, *args):
        """
        The execute method for the auth.logout operator.
        Clears any cached credentials and resets the session page back to the
        Login screen.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        if self.props.credentials:
            self.props.credentials.clear_auth()

        self.props.credentials = None
        bpy.context.scene.batchapps_session.page = "LOGIN"
        bpy.context.scene.batchapps_session.log.info(
            "Logged out. Cached sessions cleared.")

        return {'FINISHED'}

    def auto_authentication(self, cfg, log):
        """
        Attempts to authenticate automatically by first searching the Batch Apps
        configuration for an unattended session, then a cached session.
        
        :Args:
            - cfg (:class:`batchapps.Configuration`): An instance of the Batch
              Apps Configuration class, read from the file set in the addon
              User Preferences.
            - log (:class:`batchapps.log.PickleLog`): A logger object as set in
              BatchAppsSettings.

        :Returns:
            - ``True`` if the addon was successfully authenticated,
              else ``False``
        """
        try:
            log.info("Checking for unattended session...")
            self.props.credentials = AzureOAuth.get_unattended_session(config=cfg)
            log.info("Found!")
            return True

        except (AuthenticationException, InvalidConfigException) as exp:
            log.info("Could not get unattended session: {0}".format(exp))

        try:
            log.info("Checking for cached session...")
            self.props.credentials = AzureOAuth.get_session(config=cfg)
            log.info("Found!")
            return True

        except (AuthenticationException, InvalidConfigException) as exp:
            log.info("Could not get cached session: {0}".format(exp))
            return False
            
    def wait_for_request(self):
        """
        Once the user has been prompted to authenticate in a web browser
        session, start a basic HTTPServer to intercept the AAD redirect call
        to collect the server response to the auth request.

        The localhost redirect URL will depend on how the client is set up in
        the AAD portal.

        The server has a timeout of 1 minute.
        """
        session = bpy.context.scene.batchapps_session
        self.props.code=None

        config = bpy.context.scene.batchapps_session.cfg

        redirect = config.aad_config()['redirect_uri'].split(':')
        server_address = (redirect[0], int(redirect[1]))

        web_server = HTTPServer(server_address, OAuthRequestHandler)
        session.log.debug("Created web server listening at: {0}, {1}.".format(
            redirect[0], int(redirect[1])))

        web_server.timeout = TIMEOUT
        web_server.handle_request()
        web_server.server_close()
        session.log.debug("Closed server.")

    def open_websession(self):
        """
        Open a web browser session to prompt the user to authenticate via their
        AAD credentials.
        This method of authentication is the 'last resort' after
        auto-authentication and unattended authentication have failed.

        :Raises:
            - :class:`RuntimeError` if authentication fails, which will fail
              the loading of the addon as all auth routes have failed. This
              could be due to either an 
              :class:`batchapps.exceptions.AuthenticationException` of a
              :class:`batchapps.exceptions.InvalidConfigException`.
        """
        session = bpy.context.scene.batchapps_session

        try:
            url, state = AzureOAuth.get_authorization_url(config=session.cfg)
            webbrowser.open(url)

            session.log.info("Opened web browser for authentication "
                             "and waiting for response.")

            self.wait_for_request()

        except (AuthenticationException, InvalidConfigException) as exp:
            session.log.error("Unable to open Web UI auth session: "
                              "{0}".format(exp))

            raise RuntimeError("Failed to authorize addon")

    def decode_error(self, val):
        """
        Format the auth redirect URL to extract the auth code.

        :Args:
            - val (str): The redirect URL.

        :Returns:
            - The auth code (str).
        """
        error_idx = self.props.code.find(val)
        if error_idx < 0:
            return None

        strt_idx = error_idx + len(val)
        end_idx = self.props.code.find('&', strt_idx)
        error_val = self.props.code[strt_idx:end_idx]

        return unquote(error_val)

    def web_authentication(self):
        """
        Prompts user to authenticate via a web browser session, after
        auto-authentication and unattended authentication have failed.

        If web authentication is successful, the session (i.e. refresh token)
        will be cached to enable auto-authentication next time the addon is
        used. Session page will be set to the HOME page.

        If unsuccessful, the addon will failed to load and the ERROR page will
        be display. Error details will be logged to the console.

        """
        session = bpy.context.scene.batchapps_session

        if self.auto_authentication(session.cfg, session.log):
            session.start(self.props.credentials)
            session.page = "HOME"
            session.redraw()
            return

        self.open_websession()

        if not self.props.code:
            session.log.warning("Log in timed out - please try again.")
            session.page = "LOGIN"

        elif '/?error=' in self.props.code:
            error = self.decode_error('/?error=')
            details = self.decode_error(
                '&error_description=').replace('+', ' ')

            session.log.error("Authentication failed: {0}".format(error))
            session.log.error(details)
            session.page = "ERROR"

        else:
            session.log.info(
                "Received valid authentication response from web browser.")
            session.log.info("Now retrieving new authentication token...")

            self.props.credentials = AzureOAuth.get_authorization_token(
                self.props.code, config=session.cfg)

            session.start(self.props.credentials)
            session.log.info("Successful! Login complete.")
        
        session.redraw()