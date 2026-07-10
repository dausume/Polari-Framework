"""
@module polariRefs.identity_map

Identity map keyed (authority_key, className, id) with weakref values
(xsim-1). Hydrating the same remote/demoted object twice must hand back
the SAME Python object while it is alive — and instance a row 5 vs
instance b row 5 must stay two objects (edge-case ledger row 1).

Maps are held per manager in a module-level cache keyed id(manager)
(the schema_stability._STATUS_CACHE idiom — avoids attaching attributes
through managerObject's custom __setattr__). treeObject carries no
__slots__, so instances are weakref-able; non-weakrefable values are
tracked strongly-never — register() refuses honestly instead of
crashing.
"""

import weakref
from typing import Any, Dict, Optional, Tuple

_MAPS: Dict[int, 'RefIdentityMap'] = {}


class RefIdentityMap:
    def __init__(self):
        self._by_key = weakref.WeakValueDictionary()

    @staticmethod
    def key(authority_key: str, class_name: str, obj_id: str
            ) -> Tuple[str, str, str]:
        return (authority_key, class_name, str(obj_id))

    def get(self, authority_key: str, class_name: str, obj_id: str
            ) -> Optional[Any]:
        return self._by_key.get(self.key(authority_key, class_name,
                                         obj_id))

    def register(self, authority_key: str, class_name: str, obj_id: str,
                 instance: Any) -> Dict:
        """Idempotent: an already-live entry WINS (callers get the
        canonical object back). Returns {'ok', 'instance', 'note'|...}"""
        k = self.key(authority_key, class_name, obj_id)
        existing = self._by_key.get(k)
        if existing is not None:
            return {'ok': True, 'instance': existing,
                    'note': 'already hydrated — canonical object kept'}
        try:
            self._by_key[k] = instance
        except TypeError:
            return {'ok': False, 'instance': instance,
                    'error': f'{type(instance).__name__} is not '
                             'weakref-able; identity not tracked'}
        return {'ok': True, 'instance': instance, 'note': 'registered'}

    def live_count(self) -> int:
        return len(self._by_key)


def identity_map_for(manager) -> RefIdentityMap:
    m = _MAPS.get(id(manager))
    if m is None:
        m = _MAPS[id(manager)] = RefIdentityMap()
    return m
