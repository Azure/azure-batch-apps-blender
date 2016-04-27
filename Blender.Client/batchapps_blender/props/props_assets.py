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

@bpy.app.handlers.persistent
def on_load(*args):
    """
    Handler to ensure assets list is reset inbetween .blend files.
    Also resets the job file path inbetween blend files.

    Run on blend file load.

    """
    bpy.context.scene.batch_assets.path = ""
    if bpy.context.scene.batch_session.page == "ASSETS":
        bpy.ops.batch_assets.refresh()

def format_date(asset):
    """
    Format an assets last modified date for the UI.

    :Args:
        - asset (:class:`batch.files.UserFile`): Asset whos date we
          want to format.

    :Returns:
        - The last modified date as a string. If formatting fails,
          an empty string.
    """
    try:
        datelist = asset.get_last_modified().isoformat().split('T')
        datelist[1] = datelist[1].split('.')[0]
        return ' '.join(datelist)

    except:
        bpy.context.scene.batch_session.log.debug(
            "Couldn't format date {0}.".format(asset.get_last_modified()))
        return ""

class AssetDisplayProps(bpy.types.PropertyGroup):
    """
    A display object representing an asset.
    Displayed by :class:`.ui_assets.AssetListUI`.
    """

    name = bpy.props.StringProperty(
        description="Asset filename")

    fullpath = bpy.props.StringProperty(
        description="Asset full path")
    
    upload_checkbox = bpy.props.BoolProperty(
        description = "Check to upload asset",
        default = False)

    upload_check = bpy.props.BoolProperty(
        description="Selected for upload",
        default=False)

    timestamp = bpy.props.StringProperty(
        description="Asset last modified timestamp",
        default="")

class AssetProps(bpy.types.PropertyGroup):
    """
    Asset Properties,
    Once instantiated, this class is set to both the Blender context, and
    assigned to assets.BatchAssets.props.
    """

    collection = []

    path = bpy.props.StringProperty(
        description="Blend file path to be rendered")

    temp = bpy.props.BoolProperty(
        description="Whether we're using a temp blend file",
        default=False)

    assets = bpy.props.CollectionProperty(
        type=AssetDisplayProps,
        description="Asset display list")

    index = bpy.props.IntProperty(
        description="Selected asset index")

    def add_asset(self, asset):
        """
        Add an asset to both the display and object lists.

        """
        log = bpy.context.scene.batch_session.log
        log.debug("Adding asset to ui list {0}.".format(asset.name))

        self.collection.append(asset)
        self.assets.add()
        entry = self.assets[-1]
        entry.name = asset.name
        entry.timestamp = format_date(asset)
        entry.fullpath = asset.path
        entry.upload_check = asset.is_uploaded()

        log.debug("Total assets now {0}.".format(len(self.assets)))

    def remove_selected(self):
        """
        Remove selected asset from both display and object lists.

        """
        bpy.context.scene.batch_session.log.debug(
            "Removing index {0}.".format(self.index))

        self.collection.pop(self.index)
        self.assets.remove(self.index)
        self.index = max(self.index - 1, 0)

    def get_jobfile(self):
        """
        Get the asset object whos path is the job file path.

        """
        log = bpy.context.scene.batch_session.log

        for asset in self.collection:
            if asset.path == self.path:
                log.debug("Found job asset at {0}".format(self.path))
                return asset
        else:
            log.debug("Found no job asset, using {0}".format(self.path))
            raise ValueError("Job Asset not in collection")

    def reset(self):
        """
        Clear both asset display and object lists.

        """
        self.collection.clear()
        self.assets.clear()
        self.index = 0

        bpy.context.scene.batch_session.log.debug("Reset asset lists.")

    def set_uploaded(self):
        """
        Mark all assets as having been uploaded.

        """
        for asset in self.assets:
            asset.upload_check = True


def register_props():
    """
    Register the asset property classes and assign to the blender
    context under "batch_assets".

    :Returns:
        - A :class:`.AssetProps` object
    """

    bpy.types.Scene.batch_assets = \
        bpy.props.PointerProperty(type=AssetProps)

    bpy.app.handlers.load_post.append(on_load)

    return bpy.context.scene.batch_assets