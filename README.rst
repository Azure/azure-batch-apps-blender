===============================
Azure Batch Apps Blender Sample
===============================

Warning - Code currently being re-written
==========================================

This sample is based on the now-deprecated Azure Batch Apps service. The Blender sample is currently being re-written to work directly against
`Azure Batch <https://azure.microsoft.com/en-us/services/batch/>`_.
This updated version of the code can be accessed in the following fork while it is under-going development:
`<https://github.com/annatisch/azure-batch-apps-blender/tree/dev/>`_.

Please check the issues forum for guidance on using the in-development code and to report any bugs.


Summary
=======


Microsoft Azure Batch Apps is an Azure service offering on-demand capacity for compute-intensive workloads.
This sample uses the Azure Batch Apps SDK and the Azure Batch Apps Python client to show how 
one could set up a cloud-based rendering platform using Blender.

The sample involves two parts, the cloud assembly project, and the Blender client project for job submission.
For more information on Batch Apps concepts, terms, and project structure `check out this article <http://azure.microsoft.com/en-us/documentation/articles/batch-dotnet-get-started/#tutorial2>`_.

The client project is a Python 'Addon' for Blender, to allow for a seamless user experience for submitting render
jobs to the cloud from within Blender.

The compiled components can be downloaded in the release. 


License
========

This project is licensed under the MIT License.
For details see LICENSE.txt or visit `opensource.org/licenses/MIT <http://opensource.org/licenses/MIT>`_.

Blender
========

Blender is a free and open source 3D animation suite.
It supports the entirety of the 3D pipeline - modeling, rigging, animation, simulation, rendering, compositing and motion tracking, even video editing and game creation. 
Advanced users employ Blender's API for Python scripting to customize the application and write specialized tools; often these are included in Blender's future releases. 
Blender is well suited to individuals and small studios who benefit from its unified pipeline and responsive development process.

For more information and to download Blender, visit `blender.org <http://www.blender.org>`_.



Building and Installing the Addon
----------------------------------

To package up the addon, zip up the Blender.Client/batchapps_blender directory.
Alternatively set Blender.Client as the start-up project and run the solution. This will zip up the addon into Blender.Client/build

To install the Addon:

1. Run Blender
2. Open File > User Preferences
3. Navigate to the Addons tab
4. Click 'Install from File...' at the bottom of the dialog window.
5. Navigate to and select the packaged client zip.
6. The Addon 'Batch Apps Blender' will now be registered under the 'Render' category. Once located, select the 
   check box to activate the Addon.
7. Once activated, the Addon UI will appear in the 'Render Properties' panel - by default, in the lower right corner
   of the screen.


Addon Logging and Configuration
--------------------------------

The sample addon logs to both Blender's stdout and to file.
By default this log file will be saved to $HOME/BatchAppsData. This directory is also the location of the Addon
configuration file.

This directory, the config file to use, and the level of logging detail are all configurable within the Blender UI.
The authentication configuration settings of the file can also be overridden in the Blender UI.

1. Run Blender
2. Open File > User Preferences
3. Navigate to the Addons tab
4. Either search for 'Batch Apps Blender', or navigate to the Addon under the 'Render' category.
5. Select the arrow next to the Addon to open the details drop down - here you will find info on the version and installation directory.
6. Listed here you will also find the configuration preferences. If modified, click 'Save User Settings' at the bottom 
   of the dialog window (Note: this will also cause the Batch Apps Blender Addon to be activated on Blender start-up).
7. Once saved, restart Blender for the changes to take effect.







