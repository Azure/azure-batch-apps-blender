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

bl_info = {
    "name": "Batch Apps Blender",
    "author": "Microsoft Corp. <bigcompute@microsoft.com>",
    "version": (0, 1, 1),
    "blender": (2, 7, 2),
    "location": "Render Properties",
    "description": ("Export Blender files to be rendered externally by "
                    "Microsoft Batch Apps."),
    "category": "Render"}

import bpy

from batchapps import credentials
from batchapps import config as logging

from batchapps_blender.props.props_shared import BatchAppsPreferences
from batchapps_blender.shared import BatchAppsSettings
from batchapps_blender.draw import *

@bpy.app.handlers.persistent
def start_session(self):
    """
    Instantiate the Batch Apps session and register all the property
    classes to the Blender context.
    This is handled in an event to allow it to run under the full
    Blender context rather than the limited loading scope.

    Once the session has started (or reported an error), this function
    is removed from the event handlers.
    """
    try:
        session = BatchAppsSettings()

        def get_session(self):
            return session
        bpy.types.Scene.batchapps_session = property(get_session)

    except Exception as e:
        print("BatchApps Addon failed to load.")
        print ("Error: {0}".format(e))
        bpy.types.Scene.batchapps_error = e

    finally:
        bpy.app.handlers.scene_update_post.remove(start_session)
    

def register():
    """
    Register module and applicable classes.
    This method also sets some BatchApps globals. In particular, the
    python module Requests that is packaged with blender does not allow
    for certificates to be verified, so we have to either turn this off,
    or replace the included Requests module (recommended).

    Here we also register the User Preferences for the Addon, so it can
    be configured in the Blender User Preferences window.
    """
    credentials.VERIFY = False
    logging.STREAM_LOG = False

    bpy.app.handlers.scene_update_post.append(start_session)

    bpy.utils.register_class(BatchAppsPreferences)
    bpy.utils.register_module(__name__)


def unregister():
    """
    Unregister the addon if deselected from the User Preferences window.
    """
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()

