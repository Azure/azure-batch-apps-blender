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
import os


class BatchAppsPreferences(bpy.types.AddonPreferences):
    """BatchApps Blender addon user preferences."""

    bl_idname = __package__.split('.')[0]

    ini_file = bpy.props.StringProperty(
            name="Configuration file",
            description="BatchApps config file",
            subtype='FILE_NAME',
            default="batch_apps.ini")

    data_dir = bpy.props.StringProperty(
            name="Data directory",
            description="Location of config file and log file",
            subtype='DIR_PATH',
            default=os.path.join(os.path.expanduser('~'), 'BatchAppsData'))

    log_level = bpy.props.EnumProperty(items=(('10', 'Debug', ''),
                                              ('20', 'Info', ''),
                                              ('30', 'Warning', ''),
                                              ('40', 'Error', ''),
                                              ('50', 'Critical', '')),
                                       name="Logging level",
                                       description="Level of logging detail",
                                       default="30")

    account = bpy.props.StringProperty(
        name="Unattended Account",
        description="Batch Apps Unattended Account",
        default="")

    key = bpy.props.StringProperty(
        name="Unattended Key",
        description="Batch Apps Unattended Account key",
        default="")

    endpoint = bpy.props.StringProperty(
        name="Service URL",
        description="Batch Apps service endpoint",
        default="")

    client_id = bpy.props.StringProperty(
        name="Client ID",
        description="AAD Client ID",
        default="")

    tenant = bpy.props.StringProperty(
        name="Tenant",
        description="AAD auth tenant",
        default="")

    redirect = bpy.props.StringProperty(
        name="Redirect URI",
        description="AAD auth redirect URI",
        default="")

    def draw(self, context):
        """
        Draw the display for the settings in the User Preferences
        with next to the Addon entry.

        :Args:
            - context (bpy.types.Context): Blenders current runtime
              context.

        """
        layout = self.layout
        layout.label(text="Blender will need to be restarted "
                     "for changes to take effect.")

        layout.prop(self, "data_dir")
        layout.prop(self, "ini_file")
        layout.prop(self, "log_level")

        layout.label(text="")
        layout.label(text="Service Authentication configuration. "
                     "These settings will override those in the config file.")

        layout.prop(self, "endpoint")
        layout.prop(self, "account")
        layout.prop(self, "key")
        layout.prop(self, "client_id")
        layout.prop(self, "tenant")
        layout.prop(self, "redirect")