"""
@module hwnocode.hwnocode_endpoints
construct_hwnocode_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.

It also puts the hardware NODE KINDS on the ONE canvas's palette (D-hn-2): each class in NODE_KIND_CLASSES is marked a state-space
class on its typing, so GET /stateSpaceClasses (the existing endpoint) lists it with its `statePalette` — the canvas registers it as
data, the static TS registry stays as it is for the old kinds.
"""
from hwnocode.hwnocode_api import HwNoCodeAPI


def enable_node_kinds(manager):
    """Mark the node-kind typings state-space (idempotent). → the class names now on the palette."""
    from hwnocode.hwnocode_basis import NODE_KIND_CLASSES
    typing = getattr(manager, 'objectTypingDict', None) or {}
    done = []
    for cls in NODE_KIND_CLASSES:
        t = typing.get(cls.__name__)
        if t is None:
            continue
        t.isStateSpaceObject = True
        try:
            t.setStateSpaceDisplayFields(list(cls.statePalette.get('displayFields') or []), 1)
        except Exception:  # noqa: BLE001 — display fields are cosmetic; the palette entry still arrives
            pass
        done.append(cls.__name__)
    return done


def construct_hwnocode_endpoints(polServer):
    enable_node_kinds(polServer.manager)
    return HwNoCodeAPI(polServer=polServer, manager=polServer.manager)
