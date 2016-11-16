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
import webbrowser
import os

from batched_blender.ui import ui_shared
from batched_blender.submission import BatchSubmission
from batched_blender.assets import BatchAssets
from batched_blender.jobs import BatchJobs
from batched_blender.pools import BatchPools
from batched_blender.bfiles import BatchBfiles
from batched_blender.utils import BatchOps

import azure.storage.blob as az_storage
import azure.batch as az_batch
from azure.batch.batch_auth import SharedKeyCredentials


class BatchSettings(object):
    """
    Initializes and manages the Batch Apps addon session.
    Registers all classes and handles all sub-pages.
    Defines the display of the global HOME and ERROR pages.
    Also configures logging and User Preferences.
    """

    pages = ["HOME", "ERROR"]

    def __init__(self):

        self.ops = self._register_ops()
        self.ui = self._register_ui()
        self.props = self._register_props()

        self.log = self._configure_logging()
        self.cfg = self._configure_addon()
        self.page = "LOGIN"

        self.submission = None
        self.jobs = None
        self.assets = None
        self.pools = None
        self.bfiles = None

        self.start()

    def _configure_addon(self):
        """
        Configures the addon based on the current User Preferences
        and the supplied Batch Apps ini file configuration.
        """
        cfg = {}
        cfg['account'] =  self.props.account
        cfg['endpoint'] =  self.props.endpoint
        cfg['key'] =  self.props.key
        cfg['storage'] =  self.props.storage
        cfg['storage_key'] =  self.props.storage_key
        cfg['storage_container'] =  self.props.storage_container
        return cfg

    def _configure_logging(self):
        """
        Configures the logger for the addon based on the User Preferences.
        Sets up a stream handler to log to Blenders console and a file
        handler to log to the Batch log file.
        """
        logger = logging.getLogger('batched_blender')
        logger.setLevel(int(self.props.log_level))
        console_format = logging.Formatter(
            "Batch: [%(levelname)s] %(message)s")
        file_format = logging.Formatter(
            "%(asctime)-15s [%(levelname)s] %(module)s: %(message)s")

        console_logging = logging.StreamHandler()
        console_logging.setFormatter(console_format)
        logger.addHandler(console_logging)
        logfile = os.path.join(self.props.log_dir, "batched_blender.log")
        file_logging = logging.FileHandler(logfile)
        file_logging.setFormatter(file_format)
        logger.addHandler(file_logging)
        return logger

    def _register_ops(self):
        """
        Registers the shared operators with a batch_shared prefix.

        :Returns:
            - A list of the names (str) of the registered operators.
        """
        ops = []
        ops.append(BatchOps.register("shared.home",
                                         "Home",
                                         self._home))
        ops.append(BatchOps.register("shared.management_portal",
                                         "Management Portal",
                                         self._management_portal))
        return ops

    def _register_props(self):
        """
        Retrieves the shared addon properties - in this case the User
        Preferences.

        :Returns:
            - :class:`.BatchPreferences`
        """
        props = bpy.context.user_preferences.addons[__package__].preferences
        if not os.path.isdir(props.log_dir):
            try:
                os.mkdir(props.log_dir)
            except:
                raise EnvironmentError(
                    "Data directory not created at '{0}'.\n"
                    "Please ensure you have adequate permissions.".format(props.log_dir))
        return props

    def _register_ui(self):
        """
        Matches the HOME and ERROR pages with their corresponding
        ui functions.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_shared_ui(name):
            name = name.lower()
            return getattr(ui_shared, name)

        page_func = map(get_shared_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _home(self, op, context):
        """
        The execute method for the shared.home operator.
        Sets the session page to HOME.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        self.page = "HOME"
        return {'FINISHED'}

    def _management_portal(self, op, context):
        """
        The execute method for the shared.management_portal operator.
        Opens the Management Portal in a web browser.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        webbrowser.open("https://ms.portal.azure.com/", 2, True)
        return {'FINISHED'}

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
        return self.ui[self.page](ui, layout)

    def start(self):
        """
        Initialize all the addon subpages after authentication is
        complete.
        Sets page to HOME.
        """
        uploader = az_storage.BlockBlobService(
            self.cfg['storage'], 
            self.cfg['storage_key'],
            endpoint_suffix='core.windows.net')
        uploader.create_container(self.cfg['storage_container'], fail_on_exist=False)
        batch_creds = SharedKeyCredentials(self.cfg['account'], self.cfg['key'])
        batch = az_batch.BatchServiceClient(batch_creds, base_url=self.cfg['endpoint'])

        self.submission = BatchSubmission(batch, uploader)
        self.log.debug("Initialised submission module")

        self.assets = BatchAssets(batch, uploader)
        self.log.debug("Initialised assets module")

        self.jobs = BatchJobs(batch)
        self.log.debug("Initialised jobs module")

        self.pools = BatchPools(batch)
        self.log.debug("Initialised pool module")

        self.bfiles = BatchBfiles(batch, uploader)
        self.log.debug("Initialised bfile module")

        self.page = "HOME"

    def redraw(self):
        """
        Somewhat hacky way to force Blender to redraw the UI.
        """
        bpy.context.scene.objects.active = bpy.context.scene.objects.active

