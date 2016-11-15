
import os
import tempfile
import sys
import requests

_GET_PIP = "https://bootstrap.pypa.io/get-pip.py"


temp_dir = os.path.join(tempfile.gettempdir(), 'batched_blender')
if not os.path.isdir(temp_dir):
    os.makedirs(temp_dir)
sys.path.append(temp_dir)
pip_script = os.path.join(temp_dir, 'getpip.py')
if not os.path.exists(pip_script):
    with open(pip_script, 'w') as script:
        data = requests.get(_GET_PIP)
        script.write(data.text)


import getpip
try:
    getpip.main()
except BaseException as e:
    import pip

sys.exit(0)