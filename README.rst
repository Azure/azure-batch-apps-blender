===============================
Azure Batch Apps Blender Sample
===============================

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
For details see LICENSE.txt or visit `<http://opensource.org/licenses/MIT>`_.

Blender
========

Blender is a free and open source 3D animation suite.
It supports the entirety of the 3D pipeline - modeling, rigging, animation, simulation, rendering, compositing and motion tracking, even video editing and game creation. 
Advanced users employ Blender's API for Python scripting to customize the application and write specialized tools; often these are included in Blender's future releases. 
Blender is well suited to individuals and small studios who benefit from its unified pipeline and responsive development process.

For more information and to download Blender, visit `<http://www.blender.org>`_.


Set up
======

In order to build the projects you will need to have the following tools:

- `Visual Studio <http://www.visualstudio.com/>`_
- `Microsoft Azure Batch Apps Cloud SDK <http://www.nuget.org/packages/Microsoft.Azure.Batch.Apps.Cloud/>`_
- `Python Tools for Visual Studio <http://pytools.codeplex.com/>`_
- `Azure Batch Apps Python Client and it's required packages <https://github.com/Azure/azure-batch-apps-python>`_
 


Part 1. Blender.Cloud
======================

This project builds a cloud assembly for running rendering jobs using Blender.  
A "cloud assembly" is a zip file containing an application-specific DLL with logic for splitting
jobs into tasks, and for executing each of those tasks.  In this sample, we split the job into
a task for each frame to be rendered, and execute each task by running the blender.exe program. 
The cloud assembly goes hand in hand with an "application image," a zip file 
containing the program or programs to be executed.  In this sample, we have used Blender and 
ImageMagick in the application image.
 

Building the Cloud Assembly
---------------------------

To build the cloud assembly zip file:

1. Build the Blender.Cloud project.
2. Open the output folder of the Blender.Cloud project.
3. Select all the DLLs (and optionally PDB files) in the output folder.
4. Right-click and choose Send To > Compressed Folder.


Building the Application Image
-------------------------------

The application image contains the following applications:

- `Blender <http://www.blender.org/download/>`_. The application we want to cloud-enable.
  It is easiest in this scenario to download as a zip rather than the installer.
- `ImageMagick <http://www.imagemagick.org/script/binary-releases.php#windows>`_. (Optional) Tool for creating preview thumbnails 
  of the rendered frames. Locate the portable Win32 static build.

To build the application image zip file:

1. Open `<http://www.blender.org/download/>`_.
2. Locate the 64bit zip download for the latest Blender release. `Direct download of 2.73 here <http://mirror.cs.umn.edu/blender.org/release/Blender2.73/blender-2.73-windows64.zip>`_.
3. Extract the subfolder (blender-2.7x-windows64) to a location of choice and rename it 'Blender'.
4. Open `<http://www.imagemagick.org/script/binary-releases.php#windows>`_
5. Locate and download the portable Win32 static build. It is important to use the portable build!
6. Extract the subfolder (ImageMagick-6.x.x) next to the earlier 'Blender' directory, and rename it to 'ImageMagick'.
7. Select both the 'Blender' and 'ImageMagick' directories, right-click and choose Send To > Compressed Folder.
8. Rename the resulting zip file to Blender.zip

The final application image zip file should have the following structure::

	Blender.zip
	|
	| -- Blender
	|    |
	|    | -- blender.exe
	|    | -- 2.7x directory
	|    | -- other Blender components
	|
	| -- ImageMagick
	     |
	     | -- convert.exe
	     | -- other ImageMagick components


Uploading the Application to Your Batch Apps Service
-----------------------------------------------------

1. Open the Azure management portal (manage.windowsazure.com).
2. Select Batch Services in the left-hand menu.
3. Select your account in the list and click "Manage Batch Apps" to open the Batch Apps management 
   portal. Your Batch Apps Service should be displayed, or you can navigate to it using the Services left-hand menu option.
4. Choose the Manage Applications tab.
5. Click New Application.
6. Under "Select and upload a cloud assembly," choose your cloud assembly zip file and click Upload.
7. Under "Select and upload an application image," choose your application image zip file and click Upload.  
   (Be sure to leave the version as "default".)
8. Click Done.



Part 2. Blender.Client
=======================

Now that the Blender rendering service is configured in Batch Apps, we need a way to submit Blender files
to be rendered.
The sample client is an Addon for Blender written in Python, that can be used on multiple platforms.

Python Setup
-------------

The Addon requires some additional Python packages in order to run.
By default, Blender is shipped with its own Python environment, so it's into this environment that these
packages will need to be installed.
There are several approaches one could take:

- Run the included dependency_check.py script within Blender. This is an experimental script to conveniently
  download and unpack the required modules into Blenders Python environment. To execute, run the following
  command from a terminal/command line with administrator privileges::

	>> blender.exe -b -P dependency_check.py

- If there is already an installation of Python 3.4 on the machine, one can use pip to install the required
  packages, choosing the Blender bundled Python environment as the target directory for the installation::

	>> pip install --target "Blender Foundation/blender/2.7x/python/lib/site-packages" azure-batch-apps
::Note:: By installing azure-batch-apps first - all the remaining packages will be installed automatically as dependencies.

- Download the packages directly from `<http://pypi.python.org>`_. Extract their module subfolders and copy them into the 
  Blender bundled Python environment::

	Destination: ~/Blender Foundation/blender/2.7x/python/lib/site-packages

The required packages are the following:

- `Batch Apps Python Client <https://pypi.python.org/pypi/azure-batch-apps>`_
- `Keyring <https://pypi.python.org/pypi/keyring>`_
- `OAuthLib <https://pypi.python.org/pypi/oauthlib>`_
- `Requests-OAuthLib <https://pypi.python.org/pypi/requests-oauthlib>`_
- Note: additional package `Requests <https://pypi.python.org/pypi/requests>`_ already comes bundled with Blender.

The Blender site-packages folder should look like this when complete::

	site-packages
	|
	| -- batchapps
	|    |
	|    | -- __init__.py
	|    | -- other batchapps components
	|
	| -- keyring
	|    |
	|    | -- __init__.py
	|    | -- other keyring components
	|
	| -- oauthlib
	|    |
	|    | -- __init__.py
	|    | -- other oauthlib components
	|
	| -- requests (bundled by default)
	|    |
	|    | -- __init__.py
	|    | -- other requests components
	|
	| -- requests_oauthlib
	|    |
	|    | -- __init__.py
	|    | -- other requests_oauthlib components
	|
	| -- Other installed modules (e.g. numpy)


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


Authentication
---------------

To run this addon you will need:

- Your Batch Apps service URL
- Unattended account credentials for your Batch Apps service

1. Open the Azure management portal (manage.windowsazure.com).
2. Select Batch Services in the left-hand menu.
3. Select your account in the list and click "Manage Batch Apps" to open the Batch Apps management 
   portal. Your Batch Apps Service should be displayed, or you can navigate to it using the Services left-hand menu option.
4. Copy the service URL from the page and paste it into the 'Service URL' field in the Blender User Preferences.
5. Click the Unattended Account button at the bottom of the page. 
6. Copy the Account ID from the page and paste it into the 'Unattended Account' field in the Blender User Preferences.
7. Below the Account Keys list, select the desired duration and click the Add Key button.
   Copy the generated key and paste it into the 'Unattended Key' field in the Blender User Preferences.
   NOTE: the generated key will be shown only once!  If you accidentally close the page
   before copying the key, just reopen it and add a new key.


Addon Documentation
--------------------

The Addon User Guide can be found `here <http://dl.windowsazure.com/batchapps/blender/user_guide.html>`_.
Auto generated Sphinx documentation for the Addon code can be found `here <http://dl.windowsazure.com/batchapps/blender/batchapps_blender.html>`_.




