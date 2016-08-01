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
def framecheck(*args):
    """
    Event handler to detect when global frame range has been changed
    and updates addon UI accordingly.
    Also issues a warning if the selected frame range falls outside the
    global frame range.

    Run when scene is updated and page is SUBMIT.

    """
    submission = bpy.context.scene.batch_submission
    session = bpy.context.scene.batch_session

    if bpy.context.scene.batch_session.page not in ["SUBMIT"]:
        return

    if submission.end_f < submission.start_f:
        session.log.warning("Start frame can't be greater than end frame.")
        submission.end_f = submission.start_f

    if ((submission.start_f < bpy.context.scene.frame_start) or 
        (submission.end_f > bpy.context.scene.frame_end)):
        submission.valid_range = False

    else:
        submission.valid_range = True

@bpy.app.handlers.persistent
def formatcheck(*args):
    """
    Event handler to detect when the global render output format has been
    changed and update UI accordingly.
    Also issues a warning if the selected output format is not supported.

    Run when scene is updated and page is SUBMIT.

    """
    submission = bpy.context.scene.batch_submission
    session = bpy.context.scene.batch_session

    if session.page not in ["SUBMIT"]:
        return

    format = bpy.context.scene.render.image_settings.file_format
    if format not in submission.supported_formats:
        submission.valid_format = False
        submission.image_format = 'PNG'

    else:
        submission.valid_format = True
        submission.image_format = format

@bpy.app.handlers.persistent
def on_load(*args):
    """
    Event handler to update the frame range when a new blender scene
    has been opened.

    Run on blend file load.

    """
    submission = bpy.context.scene.batch_submission

    submission.start_f = bpy.context.scene.frame_start
    submission.end_f = bpy.context.scene.frame_end


class SubmissionDisplayProps(bpy.types.PropertyGroup):
    """
    A display object representing a new job submission.
    This class is added to the Blender context.
    """
      
    title = bpy.props.StringProperty(
        description="Job Title",
        maxlen=64,
        default="")

    start_f = bpy.props.IntProperty(
        description="Start Frame",
        default=1,
        min=0,
        soft_min=0)

    end_f = bpy.props.IntProperty(
        description="End Frame",
        default=1,
        min=0,
        soft_min=0)

    image_format = bpy.props.StringProperty(
        description="Image Format",
        default='PNG')

    supported_formats = {
        'PNG': 'PNG',
        'JPEG': 'JPEG',
        'BMP': 'BMP',
        'CINEON': 'CINEON',
        'DPX': 'DPX',
        'HDR': 'HDR',
        'IRIS': 'IRIS',
        'OPEN_EXR': 'EXR',
        'TARGA': 'TGA',
        'TIFF': 'TIFF',
        'OPEN_EXR_MULTILAYER': 'MULTILAYER',
        'TARGA_RAW': 'RAWTGA'}

    pool_size = bpy.props.IntProperty(
        description="Number of instances in pool",
        default=1,
        min=1,
        max=20)

    valid_range = bpy.props.BoolProperty(
        description="Valid frame range",
        default=True)

    valid_format = bpy.props.BoolProperty(
        description="Valid image format",
        default=True)

    pool = bpy.props.EnumProperty(
        items=[("new", "Auto Pool", "Auto provision a pool for this job"),
               ("reuse", "Use Pool ID", "Reuse an existing persistent pool"),
               ("create", "Create Pool", "Create a new persistent pool")],
        description="Pool on which job will run",
        options={'ENUM_FLAG'},
        default={"new"})

    pool_id = bpy.props.StringProperty(
        description="Existing Pool ID",
        default="")


class SubmissionProps(object):
    """
    Submission Properties.
    Once instantiated, this class is assigned to submission.BatchSubmission.props
    but is not added to the Blender context.
    """

    thread = None
    display = None

    def register_handlers(self):
        """
        Register submission event handlers.

        """
        bpy.app.handlers.load_post.append(on_load)
        bpy.app.handlers.scene_update_post.append(framecheck)
        bpy.app.handlers.scene_update_post.append(formatcheck)
        on_load(None)


def register_props():
    """
    Register the submission property classes and assign to the blender
    context under "batch_submission".
    Also registers submission event handlers.

    :Returns:
        - A :class:`.SubmissionProps` object
    
    """
    props_obj = SubmissionProps()
    bpy.types.Scene.batch_submission = \
        bpy.props.PointerProperty(type=SubmissionDisplayProps)

    props_obj.display = bpy.context.scene.batch_submission
    props_obj.register_handlers()

    return props_obj
