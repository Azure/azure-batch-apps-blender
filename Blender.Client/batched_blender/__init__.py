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
    "name": "Batched Blender",
    "author": "Microsoft Corp. <bigcompute@microsoft.com>",
    "version": (0, 2, 0),
    "blender": (2, 7, 7),
    "location": "Render Properties",
    "description": "Export Blender files to be rendered externally by Azure Batch.",
    "category": "Render"}

import importlib
import os
import subprocess
import bpy

_NEED_INSTALL = False
_DEPENDENCIES = ['azure.batch', 'azure.storage']
_APP_DIR = os.path.dirname(__file__)

print("Checking dependencies...")
for package in _DEPENDENCIES:
    try:
        importlib.import_module(package)
    except ImportError:
        print("Unable to load {}".format(package))
        _NEED_INSTALL = True

if _NEED_INSTALL:
    print("One or more dependencies could not be loaded. Attempting to install via Pip.")
    try:
        import pip
    except ImportError:
        print("Pip not found. Installing Pip.")
        try:
            subprocess.run(
                        [
                            bpy.app.binary_path_python,
                            os.path.join(_APP_DIR, 'scripts', 'install_pip.py')
                        ],
                        stdout=subprocess.PIPE,
                        check=True)
            import pip
        except BaseException as exp:
            print("Failed to install Pip. Please install dependencies manually to continue.")
            raise
        print("Installing dependencies")
        for package in _DEPENDENCIES:
            pip.main(['install', package])
            print("Successfully installed {}".format(package))
    except:
        raise ImportError("Failed to install dependencies")

from batched_blender.props.props_shared import BatchPreferences
from batched_blender.shared import BatchSettings
from batched_blender.draw import *


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
        session = BatchSettings()

        def get_session(self):
            return session
        bpy.types.Scene.batch_session = property(get_session)

    except Exception as e:
        print("Batch Addon failed to load.")
        print("Error: {0}".format(e))
        bpy.types.Scene.batch_error = e

    finally:
        bpy.app.handlers.scene_update_post.remove(start_session)
    

def register():
    """
    Register module and applicable classes.
    This method also sets some Batch globals. In particular, the
    python module Requests that is packaged with blender does not allow
    for certificates to be verified, so we have to either turn this off,
    or replace the included Requests module (recommended).

    Here we also register the User Preferences for the Addon, so it can
    be configured in the Blender User Preferences window.
    """
    bpy.app.handlers.scene_update_post.append(start_session)
    bpy.utils.register_class(BatchPreferences)
    bpy.utils.register_module(__name__)


def unregister():
    """
    Unregister the addon if deselected from the User Preferences window.
    """
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()
