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


class BatchPreferences(bpy.types.AddonPreferences):
    """Batch Blender addon user preferences."""

    bl_idname = __package__.split('.')[0]

    log_dir = bpy.props.StringProperty(
            name="Log directory",
            description="Location of log file",
            subtype='DIR_PATH',
            default=os.path.expanduser('~'))

    log_level = bpy.props.EnumProperty(items=(('10', 'Debug', ''),
                                              ('20', 'Info', ''),
                                              ('30', 'Warning', ''),
                                              ('40', 'Error', ''),
                                              ('50', 'Critical', '')),
                                       name="Logging level",
                                       description="Level of logging detail",
                                       default="30")

    account = bpy.props.StringProperty(
        name="Batch Account",
        description="Batch account name.",
        default="")

    key = bpy.props.StringProperty(
        name="Batch Account Key",
        description="Batch account key.",
        default="")

    endpoint = bpy.props.StringProperty(
        name="Batch Account URL",
        description="Batch service endpoint.",
        default="")

    storage = bpy.props.StringProperty(
        name="Storage Account",
        description="Azure Storage account name where assets will be uploaded to.",
        default="")

    storage_key = bpy.props.StringProperty(
        name="Storage Account Key",
        description="Azure Storage account key.",
        default="")

    storage_container = bpy.props.StringProperty(
        name="Storage Container",
        description="Name of container in storage where assets will be uploaded.",
        default="batched-blender-assets")

    vm_type = bpy.props.EnumProperty(items=(('STANDARD_A1', 'STANDARD_A1', ''),
                                            ('STANDARD_A2', 'STANDARD_A2', ''),
                                            ('STANDARD_A3', 'STANDARD_A3', ''),
                                            ('STANDARD_A4', 'STANDARD_A4', ''),
                                            ('STANDARD_A5', 'STANDARD_A5', ''),
                                            ('STANDARD_A6', 'STANDARD_A6', ''),
                                            ('STANDARD_A7', 'STANDARD_A7', ''),
                                            ('STANDARD_A8', 'STANDARD_A8', ''),
                                            ('STANDARD_A9', 'STANDARD_A9', ''),
                                            ('STANDARD_A10', 'STANDARD_A10', ''),
                                            ('STANDARD_A11', 'STANDARD_A11', ''),
                                            ('STANDARD_D1', 'STANDARD_D1', ''),
                                            ('STANDARD_D2', 'STANDARD_D2', ''),
                                            ('STANDARD_D3', 'STANDARD_D3', ''),
                                            ('STANDARD_D4', 'STANDARD_D4', ''),
                                            ('STANDARD_D11', 'STANDARD_D11', ''),
                                            ('STANDARD_D12', 'STANDARD_D12', ''),
                                            ('STANDARD_D13', 'STANDARD_D13', ''),
                                            ('STANDARD_D14', 'STANDARD_D14', ''),
                                            ('STANDARD_D1_v2', 'STANDARD_D1_v2', ''),
                                            ('STANDARD_D2_v2', 'STANDARD_D2_v2', ''),
                                            ('STANDARD_D3_v2', 'STANDARD_D3_v2', ''),
                                            ('STANDARD_D4_v2', 'STANDARD_D4_v2', ''),
                                            ('STANDARD_D5_v2', 'STANDARD_D5_v2', ''),
                                            ('STANDARD_D11_v2', 'STANDARD_D11_v2', ''),
                                            ('STANDARD_D12_v2', 'STANDARD_D12_v2', ''),
                                            ('STANDARD_D13_v2', 'STANDARD_D13_v2', ''),
                                            ('STANDARD_D14_v2', 'STANDARD_D14_v2', ''),
                                            ('STANDARD_D15_v2', 'STANDARD_D15_v2', '')),
                                           name="VM Type",
                                           description="The type of machine on which to render.",
                                           default="STANDARD_A1")

    vm_distro = bpy.props.StringProperty(
        name="Cloud VM Linux Distro",
        description="The OS to be used on the Cloud VMs.",
        default="Ubuntu")

    vm_version = bpy.props.StringProperty(
        name="Cloud VM Linux Distro Version",
        description="The version of the OS to be used on the Cloud VMs.",
        default="14")

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

        layout.prop(self, "log_dir")
        layout.prop(self, "log_level")

        layout.label(text="")
        layout.label(text="Service Authentication Configuration")

        layout.prop(self, "endpoint")
        layout.prop(self, "account")
        layout.prop(self, "key")

        layout.label(text="")
        layout.label(text="Storage Configuration")

        layout.prop(self, "storage")
        layout.prop(self, "storage_key")
        layout.prop(self, "storage_container")

        layout.label(text="")
        layout.label(text="VM Configuration")

        layout.prop(self, "vm_type")
        layout.prop(self, "vm_distro")
        layout.prop(self, "vm_version")