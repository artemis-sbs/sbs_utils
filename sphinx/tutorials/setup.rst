Setup
===================================
Setup includes step that you need to do once, and the steps when creating a new mission.


**One time Setup**

#. Install Artemis Cosmos
#. Install git for windows
#. Install command line tools fetch and pip-install

**Each new mission Setup**

#. create a Mission folder
#. create a script.py
#. create a requirements.txt
#. run pip_install.bat


One time Setup
------------------------------------
These step are only need to need to be setup on a new PC setup.

These are only needed on a server machine.


Install artemis cosmos
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install Artemis Cosmos as one would.


Install git for windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

git is a free open source version control system used by many systems to manage code source files and libraries of source code.

git can be `Downloaded here <https://git-scm.com/download/win>`_

git is used by the python pip install process to install dependencies. It is also a useful tool to manage your code versions.

Many missions and libraries will be store using git, and leveraging github. It may be worth learning about both git and github if you plan on doing mission development.



Install command line tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A couple of batch files were created to help in loading missions as DLC (downloadable content).

They are stored on `Github <https://github.com/artemis-sbs/commandline_tools>`_ and can be retrieved there. Or a direct `Download as a zip <https://github.com/artemis-sbs/commandline_tools/archive/refs/heads/main.zip>`_

Place the files fetch.bat and pip_install.bat in your data\\missions folder of Artemis Cosmos.

fetch.bat is used to fetch missions stored on github and install them into the mission directory.
pip_install.bat is used by fetch of by itself to install libraries of code used by a mission script.

A demonstration of this will be to install the sbs_utils library for a new missions script follows.

Setting up a mission to use library
------------------------------------
The following steps you can do to create a new mission.

You cn create it the 'fast way' by copying a boiler plate mission.
Also the step-by-step method is described.


Create the fast way
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The fastest way to create a new mission that use the sbs_utils library is to use the fetch batch files that was described above.

in the Artemis Cosmos directory run:

.. code-block:: PowerShell

    .\\fetch artemis-sbs sbs_example my-new-mission


Running this should retrieve the boilerplate mission sbs_example and place it in the my-new-mission folder

Replacing my-new-mission with the name you desire for your mission.

That should be it. Open my-new-mission\\script.py in your editor and go.


Create mission folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To create a mission from scratch, the first step is to create a mission folder.

in the Artemis Cosmos data\\missions folder create a new folder. 

.. code-block:: PowerShell

    mkdir 


Create script.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The next step is to create a script.py in the mission folder you created.

This can be empty at the start or the library code to allow the script to run without error can be placed in it. 
This code will not run until the library is added by following the next steps.

.. code-block:: python3

    from lib.sbs_utils.handlerhooks import *

This code will add functions that have default behavior for all the handler functions Artemis Cosmos calls.


Create requirements.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The file requirements.txt is a python standard way to list libraries a project (i.e. mission) has.

For more information on requirements.txt `visit <https://pip.pypa.io/en/stable/reference/requirements-file-format/>`pip_install

.. code-block::

    git+https://github.com/artemis-sbs/sbs_utils.git@master#egg=sbs_utils


Adding the above will reference the main branch of sbs_utils on github. A arguably better method is to point to a specific version of the library's releases.

.. code-block::

    sbs_utils @ https://github.com/artemis-sbs/sbs_example/archive/refs/tags/v0.1.zip

This version still leverages github, but it specifies a version **0.1**

Using the version that the script is developed with is a good practice that may assure the script will ot break when new versions are released.

To see what versions exist `go here <https://github.com/artemis-sbs/sbs_example/releases>`_

You can add other python libraries as well.

.. code-block::

    numpy
    pytest
    sphinx


Run pip Install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
PIP is the standard way to install packages/libraries for python.

Artemis Cosmos does not ship with PIP. 

the pip_install.bat files does two things.

#. Install pip if needed
#. Install the packages in requirement.txt into the lib folder of the mission

If pip is not found in Artemis Cosmos it will download and install it.
It will only do this this first time. if pip is already there it does not install it again.

If you change requirements.txt you can run pip_install from the data\\missions folder

.. code-block:: PowerShell

    pip_install my-new-mission

after this the sbs_utils module should be installed in the lib folder of the new mission.

If there are additional packages listed in requirements.txt, then they will also be installed.

The new mission should now be ready to use sbs_utils from script.py






