==========================
Azure Batch Blender Sample
==========================

Microsoft Azure Batch is an Azure service offering on-demand capacity for compute-intensive workloads.
This sample uses the Azure Batch SDK for Python to show how one could set up a cloud-based rendering platform using Blender.

This sample is an "Addon" for Blender, that can create and manage Batch VM pools, upload data to Azure storage, and submit
rendering workloads to the Batch service.
For more information on Azure Batch, documentation can be found `here <https://azure.microsoft.com/en-us/documentation/services/batch/>`_.
Also, documentation for the Azure Batch Python SDK can be found `here <https://azure-sdk-for-python.readthedocs.io/en/latest/index.html>`_.


License
=======

This project is licensed under the MIT License.
For details see LICENSE.txt or visit `opensource.org/licenses/MIT <http://opensource.org/licenses/MIT>`_.

Blender
=======

Blender is a free and open source 3D animation suite.
It supports the entirety of the 3D pipeline - modeling, rigging, animation, simulation, rendering, compositing and motion tracking, even video editing and game creation. 
Advanced users employ Blender's API for Python scripting to customize the application and write specialized tools; often these are included in Blender's future releases. 
Blender is well suited to individuals and small studios who benefit from its unified pipeline and responsive development process.

For more information and to download Blender, visit `blender.org <http://www.blender.org>`_.


Blender.Client
==============

The sample client is an Addon for Blender written in Python, that can be used on multiple platforms.

Python Setup
-------------

The Addon requires some additional Python packages in order to run.
By default, Blender is shipped with its own Python environment, so it's into this environment that these
packages will need to be installed.

The easiest method to do this is with Pip (which requires an existing Python installation).
The required packages can be installed, choosing the Blender bundled Python environment as the target directory for the installation. Note that by
installing azure-batch and azure-storage, all their dependencies will also be installed to Blender::

	>> pip install --target "Blender Foundation/blender/2.7x/python/lib/site-packages" azure-batch

The required packages are the following:

- `Azure Batch <https://pypi.python.org/pypi/azure-batch>`_ and it's dependencies
- `Azure Storage <https://pypi.python.org/pypi/azure-storage>`_ and it's dependencies
- `Setuptools <https://pypi.python.org/pypi/setuptools>`_


Building and Installing the Addon
----------------------------------

To package up the addon, zip up the Blender.Client/batched_blender directory.
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
By default this log file will be saved to $HOME/BatchData. This directory is also the location of the Addon
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


Authentication
---------------

To run this addon you will need:

- An Azure Batch account name, URL and access key
- An Azure Storage account name and access key





