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

    def __init__(self, manager, storage):

        self.batch = manager

        self.ops = self._register_ops()
        self.props = self._register_props()
        self.ui = self._register_ui()
        self.storage = storage

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
        ops.append(BatchOps.register("bfiles.refresh",
                                     "Refresh blobs",
                                     self._refresh))
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
        session = context.scene.batch_session
        session.page = "BFILES"
        self.props = context.scene.batch_bfiles
        self.props.reset()


        session.log.debug("Getting blob data.")
        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container

        bfiles = [b for b in self.storage.list_blobs(container)]
        session.log.info("Retrieved {0} blob references.".format(len(bfiles)))

        for blob in bfiles:
            self.props.add_blob(blob)
        
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
        session = context.scene.batch_session
        delete = self.pending_delete()
        session.log.info("{0} blobs to be deleted".format(len(delete)))

        container = bpy.context.user_preferences.addons[__package__].preferences.storage_container
        for index in delete:
            blob = self.props.collection[index]
            display = self.props.bfiles[index]

            try:
                session.log.debug("Deleting blob {0}".format(blob.name))
                self.storage.delete_blob(container, blob.name)
            except Exception as exp:
                session.log.warning("Failed to delete {0}".format(blob))
                session.log.warning(str(exp))

        return bpy.ops.batch_bfiles.page()

    def _refresh(self, op, context):
        """
        The execute method for the bfiles.page operator.
        Downloads the data on the pools currently running in the service and
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
        return bpy.ops.batch_bfiles.page()

    def pending_delete(self):
        """
        Get a list of the blobs that have been selected for delete. 

        :Returns:
            - A list of the indexes (int) of the items in the display
              blob list that have been selected for delete.
        """

        delete_me = []

        for index, blob in enumerate(self.props.bfiles):
            if blob.delete_checkbox:
                delete_me.append(index)

        return delete_me