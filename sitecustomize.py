"""
mp-1 import seam: `modules/` is a second import root, so feature
modules relocated there (MODULE_PROJECTS_PLAN) keep their import
names — `import biomining` works whether the code sits in the
framework root (legacy) or in modules/ (the destination).

Python imports sitecustomize automatically from sys.path at
interpreter start; running anything from the framework root (host
selftests, `python3 -m <suite>`, the testing-over-topology
subprocess runner, docker exec) picks this up. The server also
inserts the path explicitly in initLocalhostPolariServer — this file
covers every OTHER entry point.
"""

import os
import sys

_modules_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'modules')
if os.path.isdir(_modules_dir) and _modules_dir not in sys.path:
    sys.path.insert(0, _modules_dir)
