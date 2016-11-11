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
    Event handler to refresh bfiles when a new blender scene is opened.

    Run on blend file load when page is BFILE.
    """
    if bpy.context.scene.batch_session.page in ["BFILES"]:
        bpy.ops.batch_bfiles.page()

class BfileDetails(bpy.types.PropertyGroup):
    """
    A display object representing a bfile.
    his class is added to the Blender context.
    """

    name = bpy.props.StringProperty(
        description="Bfile name",
        default="")

    timestamp = bpy.props.StringProperty(
        description="Bfile last modified timestamp",
        default="")

    size = bpy.props.IntProperty(
        description="Bfile size",
        default=0)


class BfileDisplayProps(bpy.types.PropertyGroup):
    """Display object representing a bfile list"""

    selected = bpy.props.IntProperty(
        description="Selected bfile",
        default=-1)

    bfiles = bpy.props.CollectionProperty(
        type=BfileDetails,
        description="Bfiles currently running")

    def add_bfile(self, bfile):
        """
        Add a bfile reference to the bfile display list.

        """
        log = bpy.context.scene.batch_session.log
        log.debug("Adding bfile to ui list {0}".format(bfile.name))

        self.bfiles.add()
        entry = self.bfiles[-1]
        entry.name = bfile.name
        entry.timestamp = str(bfile.properties.last_modified)
        entry.size = bfile.properties.content_length

class BfilesProps(object):
    """
    Bfiles Properties.
    Once instantiated, this class is assigned to bfiles.BatchBfile.props
    but is not added to the Blender context.
    """
        
    bfiles = []
    display = None
    thread = None

def register_props():
    """
    Register the bfile property classes and assign to the blender
    context under "batch_bfiles".
    Also registers bfile event handlers.

    :Returns:
        - A :class:`.BfilesProps` object

    """
    props_obj = BfilesProps()
    bpy.types.Scene.batch_bfiles = \
        bpy.props.PointerProperty(type=BfileDisplayProps)

    props_obj.display = bpy.context.scene.batch_bfiles
    bpy.app.handlers.load_post.append(on_load)

    return props_obj