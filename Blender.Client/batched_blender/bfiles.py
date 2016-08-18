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
import threading
import os

import bpy

from batched_blender.utils import BatchOps, BatchUtils
from batched_blender.ui import ui_bfiles
from batched_blender.props import props_bfiles

import azure.batch as batch


class BatchBfiles(object):
    """
    Manager for the display and creation of Batch Apps instance bfiles.
    """

    pages = ["BFILES"]

    def __init__(self, manager, uploader):

        self.batch = manager

        self.ops = self._register_ops()
        self.props = self._register_props()
        self.ui = self._register_ui()
        self.uploader = uploader

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
        Registers and retrieves the bfiles property objects.
        The dispaly properties are defined in a subclass which is assigned
        to the scene.batch_bfiles context.

        :Returns:
            - :class:`.BfilesProps`
        """
        props = props_bfiles.register_props()
        return props

    def _register_ops(self):
        """
        Registers each bfile operator with a batch_bfiles prefix.

        :Returns:
            - A list of the names (str) of the registered bfile operators.
        """
        ops = []
        ops.append(BatchOps.register("bfiles.page",
                                         "Uploaded blobs",
                                         self._bfiles))
        ops.append(BatchOps.register("bfiles.delete",
                                         "Delete blob",
                                         self._delete))
        return ops

    def _register_ui(self):
        """
        Matches the bfiles and create bfile pages with their corresponding
        ui functions.

        :Returns:
            - A dictionary mapping the page name to its corresponding
              ui function.
        """
        def get_bfiles_ui(name):
            name = name.lower()
            return getattr(ui_bfiles, name)

        page_func = map(get_bfiles_ui, self.pages)
        return dict(zip(self.pages, page_func))

    def _bfiles(self, op, context):
        """
        The execute method for the bfiles.page operator.
        Downloads the data on the bfiles currently running in the service and
        registers each as an operator for display in the UI.

        Sets the page to BFILES.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        self.props.display = bpy.context.scene.batch_bfiles

        self.props.display.bfiles.clear()
        self.props.display.selected = -1

        context.scene.batch_session.log.debug("Getting bfile data.")
        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container

        list_bfiles = [b for b in self.uploader.list_blobs(container)]
        self.props.bfiles = list_bfiles

        context.scene.batch_session.log.info(
            "Retrieved {0} bfile references.".format(len(self.props.bfiles)))

        for bfile in self.props.bfiles:
            self.props.display.add_bfile(bfile)

        for index, bfile in enumerate(self.props.display.bfiles):
            self.register_bfile(bfile, index)

        context.scene.batch_session.page = "BFILES"
        return {'FINISHED'}

    def _delete(self, op, context):
        """
        The execute method for the bfiles.delete operator.
        Delete the currently selected bfile, then calls the bfiles.page
        operator to refresh the bfile list in the display.

        :Args:
            - op (:class:`bpy.types.Operator`): An instance of the current
              operator class.
            - context (:class:`bpy.types.Context`): The current blender
              context.

        :Returns:
            - Blender-specific value {'FINISHED'} to indicate the operator has
              completed its action.
        """
        bfile = self.get_selected_bfile()
        context.scene.batch_session.log.debug(
            "Selected bfile {0}".format(bfile.name))

        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
        self.uploader.delete_blob(container, bfile.name)
        context.scene.batch_session.log.info(
            "Deleted bfile : {0}".format(bfile.name))

        return bpy.ops.batch_bfiles.page()

    def get_selected_bfile(self):
        """
        Retrieves the bfile object for the bfile currently selected in
        the dispaly.

        :Returns:
            - A :class:`batch.bfiles.bfile` object.
        """
        return self.props.bfiles[self.props.display.selected]

    def register_bfile(self, bfile, index):
        """
        Register a bfile as an operator class for dispaly in the UI.

        :Args:
            - bfile (:class:`batch.jobs.SubmittedJob`): The bfile to
              register.
            - index (int): The index of the job in list currently displayed.

        :Returns:
            - The newly registered operator name (str).
        """
        name = bfile.name
        label = "Bfile: {0}".format(bfile.name)
        index_prop = bpy.props.IntProperty(default=index)

        def execute(self):
            session = bpy.context.scene.batch_bfiles
            bpy.context.scene.batch_session.log.debug(
                "Bfile details opened: {0}, selected: {1}, index {2}".format(
                    self.enabled,
                    session.selected,
                    self.ui_index))

            if self.enabled and session.selected == self.ui_index:
                session.selected = -1

            else:
                session.selected = self.ui_index

        bpy.context.scene.batch_session.log.debug(
            "Registering {0}".format(name))

        return BatchOps.register_expanding(name, label, execute,
                                               ui_index=index_prop)