#-------------------------------------------------------------------------
# The Blender Batch Apps Sample
#
# Copyright (c) Microsoft Corporation. All rights reserved. 
#
# The MIT License (MIT)
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
import tempfile
import os
import re
import string
import random

from batchapps_blender.ui import ui_assets
from batchapps_blender.props import props_assets
from batchapps_blender.utils import BatchAppsOps


class BatchAppsAssets(object):
    """
    Manager for all external file handling and displaying of assets.
    """

    pages = ["ASSETS"]

    def __init__(self, manager):

        self.batchapps = manager
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
        Registers and retrieves the asset property objects.
        These properties are assigned to the scene.batchapps_assets context.

        It also resets the current job filepath, to prevent this being
        persisted between different Blender scenes.

        :Returns:
            - :class:`.AssetProps`
        """

        props = props_assets.register_props()
        props.path = ""
        return props

    def _register_ops(self):
        """
        Registers each asset operator with a batchapps_assets prefix.

        :Returns:
            - A list of the names (str) of the registered asset operators.
        """
        ops = []
        ops.append(BatchAppsOps.register("assets.page",
                                         "Scene assets",
                                         self._assets))
        ops.append(BatchAppsOps.register("assets.refresh",
                                         "Refresh assets",
                                         self._refresh))
        ops.append(BatchAppsOps.register("assets.upload",
                                         "Upload selected assets",
                                         self._upload))
        ops.append(BatchAppsOps.register("assets.remove",
                                         "Remove asset",
                                         invoke=self._remove))
        ops.append(BatchAppsOps.register("assets.add", "Add asset",
                                         self._add_execute,
                                         invoke=self._add_invoke,
                                         filepath=bpy.props.StringProperty(
                                             subtype="FILE_PATH")))
        return ops

    def _register_ui(self):
        """
        Matches the assets page with its corresponding ui function.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_asset_ui(name):
            name = name.lower()
            return getattr(ui_assets, name)

        page_func = map(get_asset_ui, self.pages)

        return dict(zip(self.pages, page_func))

    def _assets(self, op, context):
        """
        The execute method for the assets.page operator.
        Sets the page and initiates asset collection.
        Also checks whether assets have already been initialized for the
        current scene file.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batchapps_session
        session.page = "ASSETS"
        self.props = context.scene.batchapps_assets

        new_path = self.get_jobpath()

        if new_path != self.props.path:
            session.log.debug("New scene, gathering assets.")

            self.props.path = new_path

            if not self.props.temp:
                session.log.debug("Not temp file - saving.")
                bpy.ops.wm.save_mainfile()
            
            self.generate_collection()

        return {'FINISHED'}

    def _refresh(self, op, context):
        """
        The execute method for the assets.refresh operator.
        Re-initiates asset collection from scratch, regardless of whether it
        has been done before for this scene. This means any additional assets
        added, or any existing assets removed will be restored to their initial
        state.
        This also updates the current job file path if it has changed.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batchapps_session
        self.props = context.scene.batchapps_assets
        new_path = self.get_jobpath()

        if new_path != self.props.path:
            session.log.debug("New scene, resetting path.")
            self.props.path = new_path
        
        self.generate_collection()

        return {'FINISHED'}

    def _upload(self, op, context):
        """
        The execute method for the assets.upload operator.
        Identifies assets that have been selected for uploaded.
        Iterates through uploaded each sequentially, and updates
        the UI uploaded checkbox accordingly.

        If one asset fails to upload, the operator will continue to
        attempt to upload the remaining. 
        Any other error that occurs will be raised to be handled by
        :func:`.BatchAppsOps.session`.
       
        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batchapps_session
        upload = self.pending_upload()

        session.log.info("{0} assets to be uploaded".format(len(upload)))

        for index in upload:
            asset = self.props.collection[index]
            display = self.props.assets[index]

            try:
                session.log.debug("Uploading {0}".format(asset.name))
                asset.upload(force=True)
                display.upload_check = True
                session.log.debug("Upload complete")
                
            except Exception as exp:
                print('Failed to upload: {0}'.format(exp))
                display.upload_check = False

        return {'FINISHED'}

    def _add_execute(self, op, context):
        """
        The execute method for the assets.add operator.
        Adds an asset selected via a file browser.
        The file will only be added if it exists and has not already been
        added. If the file is already present, it will be skipped and the
        operator will finished without error.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        session = context.scene.batchapps_session
        session.log.debug("Selected file {0}".format(op.filepath))

        user_file = self.batchapps.file_from_path(op.filepath)
        if user_file and user_file not in self.props.collection:
            self.props.add_asset(user_file)

        else:
            session.log.warning("File {0} either duplicate or does not "
                                "exist.".format(user_file.name))

        return {'FINISHED'}

    def _add_invoke(self, op, context, event):
        """
        The invoke method for the assets.add operator.
        Invokes the file selector window from the WindowManager.

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
        context.window_manager.fileselect_add(op)
        return {'RUNNING_MODAL'}


    def _remove(self, op, context, event):
        '''
        The invoke method for the assets.remove operator.
        Removes currently selected assets from both the display assets
        and the UserFile collection.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.
            - event (:class:`bpy.types.Event`): The blender invocation event.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        '''
        if not self.props.assets:
            return {'FINISHED'}

        self.props.remove_selected()
        return {'FINISHED'}

    def collect_assets(self):
        """
        Generates a list of the external files referenced by the current
        blend file. After collection, the paths are made absolute and
        normalized.
        This currently includes files from:
            - bpy.data.sounds
            - bpy.data.fonts
            - bpy.data.textures.image
            - bpy.data.images
            - bpy.data.libraries
        
        :Returns:
            - A list of file paths as strings.
        """
        asset_list = []

        bpy.context.scene.batchapps_session.log.info(
            "Collecting external assets.")

        for s in bpy.data.sounds:
            new_path = os.path.realpath(bpy.path.abspath(s.filepath))
            asset_list.append(new_path)

        for f in bpy.data.fonts:
            if f.filepath != "<builtin>":
                new_path = os.path.realpath(bpy.path.abspath(f.filepath))
                asset_list.append(new_path)

        for t in bpy.data.textures:
            if hasattr(t, 'image'):
                if t.image:
                    new_path = bpy.path.abspath(t.image.filepath)
                    new_path = os.path.normpath(os.path.realpath(new_path))
                    asset_list.append(new_path)

        for i in bpy.data.images:
            new_path = os.path.realpath(bpy.path.abspath(i.filepath))
            asset_list.append(os.path.normpath(new_path))

        for l in bpy.data.libraries:
            new_path = os.path.realpath(bpy.path.abspath(l.filepath))
            asset_list.append(os.path.normpath(new_path))

        bpy.context.scene.batchapps_session.log.info(
            "Found %d asset files." % (len(asset_list)))

        return asset_list

    def name_generator(self, size=8, chars=string.hexdigits):
        """
        Generates a random blend filename for a temporary blend file.

        :Kwargs:
            - size (int): The number of random chars to use. Default is 8.
            - chars (string): The chars from which random chars will be
              selected. Default is '0123456789abcdefABCDEF'

        :Returns:
            - A file name (str) with the prefix ``BATCHAPPSTMP_`` and
              suffix ".blend".
        """
        return "BATCHAPPSTMP_"+''.join(random.choice(chars) for x in range(size))+".blend"

    def get_jobpath(self):
        """
        Gets the filepath to the job blend file. If currently using a saved
        blend file, this path will be returned.
        If the current blend file has never been saved (i.e. it has no path),
        a temporary path will be generated in the Blender User Preferences
        temporary directory.
        This temp filepath will not be saved to until submission.

        :Returns:
            - The file path (str) to the .blend file.
        """
        #TODO: Test relative vs. absolute paths.
        session = bpy.context.scene.batchapps_session

        if bpy.data.filepath == '' and self.props.temp:
            session.log.debug(
                "Blend path: Using current temp {0}".format(self.props.path))
            return self.props.path

        elif bpy.data.filepath == '':
            temp_dir = bpy.context.user_preferences.filepaths.temporary_directory
            temp_path = os.path.join(temp_dir, self.name_generator())
            self.props.temp = True

            session.log.debug(
                "Blend path: Using new temp {0}".format(temp_path))
            return temp_path

        else:
            self.props.temp = False

            session.log.debug(
                "Blend path: Using saved {0}".format(bpy.data.filepath))
            return bpy.data.filepath

    def generate_collection(self):
        """
        Runs :func:`.collect_assets` and converts the result path list into
        BatchApps UserFile objects, which the props class then adds to
        the display assets list as well as the UserFile collection.

        """
        session = bpy.context.scene.batchapps_session

        self.props.reset()
        assets = self.collect_assets()

        for asset in assets:
            session.log.debug("Discovered asset {0}.".format(asset))
            user_file = self.batchapps.file_from_path(asset)

            if user_file and user_file not in self.props.collection:
                self.props.add_asset(user_file)

            else:
                session.log.warning("File {0} either duplicate or does not "
                                "exist.".format(user_file.name))
        
        if not self.props.temp:
            session.log.debug("Adding blend file as asset.")
            jobfile = self.batchapps.file_from_path(self.props.path)

            if jobfile and jobfile not in self.props.collection:
                self.props.add_asset(jobfile)

    def pending_upload(self):
        """
        Get a list of the assets that have selected for upload. 

        :Returns:
            - A list of the indexes (int) of the items in the display
              assets list that have been selected for upload.
        """

        upload_me = []

        for index, asset in enumerate(self.props.assets):
            if asset.upload_checkbox:
                upload_me.append(index)

        return upload_me




