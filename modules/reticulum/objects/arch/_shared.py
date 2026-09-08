"""@module reticulum.objects.arch._shared — what the arch row classes share (constants, seeds, helpers); split from arch_basis.py (sap-2c)."""
from reticulum.reticulum_basis import measurement_fresh

ARCH_NODE_KIND_VALUES = ('peer-isle', 'device', 'relay')
TRUST_GRADE_VALUES = ('observe', 'gossip', 'telemetry', 'propose',
                      'propose-low-preapproved')
_GRADE_AUTO_LEVEL = {
    'observe': 0,
    'gossip': 0,
    'telemetry': 2,
    'propose': 2,
    'propose-low-preapproved': 3,
}
def effective_auto_level(grade):
    """Auto-approval ceiling for a trust grade. Unknown grades get 0 —
    an unrecognized grade is refused authority, never guessed into
    some."""
    return _GRADE_AUTO_LEVEL.get(grade, 0)
def reachable_now(node_fact, now_ms, horizon_ms=900_000):
    """§5c: reachability is a MEASUREMENT with a timestamp. True only
    when the node was heard inside the freshness horizon — listing
    hopeful names is exactly what this refuses to do."""
    return measurement_fresh(node_fact.get('last_heard_ms', 0), now_ms,
                             horizon_ms)
