"""
Shared in-process server for API test modules (NOT test_*-named, so
unittest discovery skips it). run_tests.py imports every test module
into ONE process — caching the booted manager here means the API sweep
and the per-fix honesty tests share a single ~40s server boot instead
of paying it per module.

Usage:
    from tests.api_test_server import shared_server, register_scratch
    manager, client = shared_server()
    register_scratch(MyScratchClass)   # idempotent per class
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falcon import testing

_CACHE = {}


def shared_server():
    """(manager, falcon TestClient) for a booted in-process server."""
    if 'manager' not in _CACHE:
        from objectTreeManagerDecorators import managerObject
        manager = managerObject(hasServer=True)
        _CACHE['manager'] = manager
        _CACHE['client'] = testing.TestClient(manager.polServer.falconServer)
    return _CACHE['manager'], _CACHE['client']


def register_scratch(cls):
    """Register a scratch treeObject class + its CRUDE endpoint on the
    shared server (idempotent — repeated calls return the same server)."""
    manager, client = shared_server()
    name = cls.__name__
    if name not in _CACHE:
        manager.getObjectTyping(classObj=cls)
        manager.polServer.registerCRUDEforObjectType(
            name, overrideExclusion=True)
        _CACHE[name] = True
    return manager, client


def multipart(fields):
    """Encode a dict of form fields as (body, content_type) — the CRUDE
    write protocol's wire format."""
    boundary = 'api-test-boundary'
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                     f'name="{name}"\r\n\r\n{value}\r\n')
    body = (''.join(parts) + f'--{boundary}--\r\n').encode()
    return body, f'multipart/form-data; boundary={boundary}'
