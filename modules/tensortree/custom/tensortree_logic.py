"""
@module tensortree.custom.tensortree_logic

THE SOFT SEAM to mathproofs (plan §I, D-pf-4): tensortree never imports mathproofs at top level. When the module is
present, a mapping's obligations (refuted / open / ok) are read from it; when absent, every reader gets the same
honest shape with `available: False` and a reason — the validator's `logic` section says "no proof module", discovery
skips the refusal filter and SAYS so.
"""


def available():
    try:
        import mathproofs.custom.rules  # noqa: F401
        return True
    except Exception:
        return False


def of_mapping(manager, mapping_name):
    """{'available', 'refuted': [...], 'open': [...], 'ok': [...], 'badge': ok|open|refuted|none|unavailable}"""
    if not available():
        return {'available': False, 'refuted': [], 'open': [], 'ok': [], 'badge': 'unavailable', 'why': 'no mathproofs module on this instance'}
    from mathproofs.custom.rules import logic_of_mapping
    r = logic_of_mapping(manager, mapping_name)
    badge = 'refuted' if r['refuted'] else ('open' if r['open'] else ('ok' if r['ok'] else 'none'))
    return {'available': True, 'badge': badge, **r}


def of_tree(manager, tree_name):
    if not available():
        return {'available': False, 'why': 'no mathproofs module on this instance', 'obligations': [], 'summary': {}}
    from mathproofs.custom.rules import obligations_of
    obs = obligations_of(manager, tree=tree_name)
    summary = {}
    for o in obs:
        k = o['status'].split(' ')[0] + (' (stale)' if '(stale)' in o['status'] else ''); summary[k] = summary.get(k, 0) + 1
    return {'available': True, 'obligations': obs, 'summary': summary, 'refuted': [o for o in obs if o['status'].startswith('refuted')]}
