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

from batchapps_blender.ui import ui_shared

from batchapps_blender.auth import BatchAppsAuth
from batchapps_blender.submission import BatchAppsSubmission
from batchapps_blender.assets import BatchAppsAssets
from batchapps_blender.history import BatchAppsHistory
from batchapps_blender.pools import BatchAppsPools
from batchapps_blender.utils import BatchAppsOps

from batchapps import (
    JobManager,
    FileManager,
    PoolManager,
    Configuration)

from batchapps.exceptions import InvalidConfigException


def override_config(cfg, **kwargs):
    """
    Override a particular AAD setting in the config file, if it has been
    set in the Blender User Preferences.

    :Args:
        - cfg (:class:`batchapps.Configuration`): The configuration to be
            updated.
        
    :Kwargs:
        - The auth setting in the config to be changed, with it's updated
            value.

    :Returns:
        - The updated config (:class:`batchapps.Configuration`).
    """
    try:
        cfg.aad_config(**kwargs)

    except InvalidConfigException:
        pass

    finally:
        return cfg

class BatchAppsSettings(object):
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

        self.auth = BatchAppsAuth()
        self.submission = None
        self.history = None
        self.assets = None
        self.pools = None

        if self.auth.auto_authentication(self.cfg, self.log):
            self.start(self.auth.props.credentials)

    def _configure_addon(self):
        """
        Configures the addon based on the current User Preferences
        and the supplied Batch Apps ini file configuration.

        :Returns:
            - A :class:`.batchapps.Configuration` object.
        """
        cfg = None
        try:
            data_dir = os.path.split(self.props.data_dir)

            cfg = Configuration(jobtype='Blender', 
                                data_path=data_dir[0],
                                log_level=int(self.props.log_level),
                                name=self.props.ini_file,
                                datadir=data_dir[1])
            
        except (InvalidConfigException, IndexError) as exp:
            self.log.warning("Warning failed to load config file, "
                             "creating new default config.")
            self.log.warning(str(exp))
            
        finally:

            if not cfg:
                cfg = Configuration(jobtype='Blender', log_level='warning')

            if self.props.endpoint:
                cfg = override_config(cfg, endpoint=self.props.endpoint)
            if self.props.account:
                cfg = override_config(cfg, account=self.props.account)
            if self.props.key:
                cfg = override_config(cfg, key=self.props.key)
            if self.props.client_id:
                cfg = override_config(cfg, client_id=self.props.client_id)
            if self.props.tenant:
                cfg = override_config(cfg, tenant=self.props.tenant)
            if self.props.redirect:
                cfg = override_config(cfg, redirect=self.props.redirect)

            cfg.save_config()
            return cfg

    def _configure_logging(self):
        """
        Configures the logger for the addon based on the User Preferences.
        Sets up a stream handler to log to Blenders console and a file
        handler to log to the Batch Apps log file.

        :Returns:
            - A :class:`batchapps.log.PickleLog` object.
        """
        logger = logging.getLogger('BatchAppsBlender')

        console_format = logging.Formatter(
            "BatchApps: [%(levelname)s] %(message)s")

        file_format = logging.Formatter(
            "%(asctime)-15s [%(levelname)s] %(module)s: %(message)s")

        console_logging = logging.StreamHandler()
        console_logging.setFormatter(console_format)
        logger.addHandler(console_logging)

        logfile = os.path.join(self.props.data_dir, "batch_apps.log")

        file_logging = logging.FileHandler(logfile)
        file_logging.setFormatter(file_format)
        logger.addHandler(file_logging)

        logger.setLevel(int(self.props.log_level))
        return logger

    def _register_ops(self):
        """
        Registers the shared operators with a batchapps_shared prefix.

        :Returns:
            - A list of the names (str) of the registered operators.
        """
        ops = []
        ops.append(BatchAppsOps.register("shared.home",
                                         "Home",
                                         self._home))
        ops.append(BatchAppsOps.register("shared.management_portal",
                                         "Management Portal",
                                         self._management_portal))
        return ops

    def _register_props(self):
        """
        Retrieves the shared addon properties - in this case the User
        Preferences.

        :Returns:
            - :class:`.BatchAppsPreferences`
        """
        return bpy.context.user_preferences.addons[__package__].preferences

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
        webbrowser.open("https://manage.batchapps.windows.net", 2, True)
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

    def start(self, creds):
        """
        Initialize all the addon subpages after authentication is
        complete.
        Sets page to HOME.

        :Args:
            - creds (:class:`batchapps.Credentials`): Authorised credentials
              with which API calls will be made.
        """
        job_mgr = JobManager(creds, cfg=self.cfg)
        asset_mgr = FileManager(creds, cfg=self.cfg)
        pool_mgr = PoolManager(creds, cfg=self.cfg)

        self.submission = BatchAppsSubmission(job_mgr, asset_mgr, pool_mgr)
        self.log.debug("Initialised submission module")

        self.assets = BatchAppsAssets(asset_mgr)
        self.log.debug("Initialised assets module")

        self.history = BatchAppsHistory(job_mgr)
        self.log.debug("Initialised history module")

        self.pools = BatchAppsPools(pool_mgr)
        self.log.debug("Initialised pool module")

        self.page = "HOME"

    def redraw(self):
        """
        Somewhat hacky way to force Blender to redraw the UI.
        """
        bpy.context.scene.objects.active = bpy.context.scene.objects.active

