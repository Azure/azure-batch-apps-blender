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

def format_date(blobdate):
    """
    Format a blob timestamp for the UI.

    :Args:
        - blobdate

    :Returns:
        - The created date as a string. If formatting fails,
          an empty string.
    """
    #TODO: Correctly format blob last modified and last uploaded timestamps
    return str(blobdate)


class BlobDisplayProps(bpy.types.PropertyGroup):
    """
    A display object representing a blob.
    Displayed by :class:`.ui_bfiles.BlobListUI`.
    """
    name = bpy.props.StringProperty(
        description="Blob name",
        default="")

    uploaded = bpy.props.StringProperty(
        description="Date the blob was uploaded",
        default="")

    size = bpy.props.StringProperty(
        description="Size of blob",
        default="")

    checksum = bpy.props.StringProperty(
        description="Checksum of blob",
        default="")

    delete_checkbox = bpy.props.BoolProperty(
        description = "Check to delete blob",
        default = False)


class BlobProps(bpy.types.PropertyGroup):
    """
    Blob Properties,
    Once instantiated, this class is set to both the Blender context, and
    assigned to bfiles.BatchBfiles.props.
    """
    collection = []
    thread = None

    bfiles = bpy.props.CollectionProperty(
        type=BlobDisplayProps,
        description="Blob display list")

    index = bpy.props.IntProperty(
        description="Selected blob index")

    def add_blob(self, blob):
        """
        Add a blob to both the display and object lists.

        """
        log = bpy.context.scene.batch_session.log
        log.debug("Adding blob to ui list {0}".format(blob.name))
        
        self.collection.append(blob)
        self.bfiles.add()
        entry = self.bfiles[-1]
        entry.name = blob.name
        entry.uploaded = format_date(blob.properties.last_modified)
        size = blob.properties.content_length
        if size < 1024:
            entry.size = "{} bytes".format(size)
        elif size/1024 < 1024:
            entry.size = "{0:.2f} Kb".format(size/1024)
        elif size/1024/1024 < 1024:
            entry.size = "{0:.2f} MB".format(size/1024/1024)
        else:
            entry.size = "{0:.2f} GB".format(size/1024/1024/1024)
        
        log.debug("Total blobs now {0}.".format(len(self.bfiles)))

    def remove_selected(self):
        """
        Remove selected blob from both display and object lists.

        """
        bpy.context.scene.batch_session.log.debug(
            "Removing index {0}.".format(self.index))

        self.collection.pop(self.index)
        self.bfiles.remove(self.index)
        self.index = max(self.index - 1, 0)

    def reset(self):
        """
        Clear both blob display and object lists.

        """
        self.collection.clear()
        self.bfiles.clear()
        self.index = 0

        bpy.context.scene.batch_session.log.debug("Reset blob lists.")


def register_props():
    """
    Register the blob property classes and assign to the blender
    context under "batch_bfiles".

    :Returns:
        - A :class:`.BlobProps` object
    """

    bpy.types.Scene.batch_bfiles = \
        bpy.props.PointerProperty(type=BlobProps)

    return bpy.context.scene.batch_bfiles