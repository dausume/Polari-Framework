"""
@module cmod.custom.config_checks

cfg-0: THE CHECK REGISTRY - which checks judge a variable group, and running them cheapest first.

  register(group, layer, name, fn)   fn(option, context) -> None (does not apply to this option) or
                                     {outcome: invalid | compromise | ideal, margin, gives_up, why, evidence}
        option  = the ConfigOption as a dict, plus `values` (its sets)
        context = {bench_solution, conditions (the BenchConditions dict), firmware_solution, configuration (the CatomConfiguration dict)}
  unregister(group, name)
  run(option, context) -> [result + {check, layer}]   in layer order; once one says invalid, the rest are recorded as skipped
                                                       (the cheap check already settled it). [] = no check applies.

The groups' real checks register themselves from their own files (cfg-1: clock); this file holds none.
"""
from cmod.custom.config_groups import GROUPS, LAYERS

_CHECKS = {}


def register(group, layer, name, fn):
    if group not in GROUPS:
        raise ValueError('unknown variable group %r' % group)
    if layer not in LAYERS:
        raise ValueError('layer must be one of %s' % sorted(LAYERS))
    _CHECKS[group] = [c for c in _CHECKS.get(group, []) if c[1] != name] + [(layer, name, fn)]
    _CHECKS[group].sort(key=lambda c: (c[0], c[1]))


def unregister(group, name):
    _CHECKS[group] = [c for c in _CHECKS.get(group, []) if c[1] != name]


def checks(group):
    return [{'layer': layer, 'check': name} for layer, name, _ in _CHECKS.get(group, [])]


def run(option, context):
    out, settled = [], False
    for layer, name, fn in _CHECKS.get(option.get('group'), []):
        if settled:
            out.append({'check': name, 'layer': layer, 'outcome': 'skipped', 'margin': 0.0, 'gives_up': '',
                        'why': 'not run: a cheaper check already found it invalid', 'evidence': ''})
            continue
        r = fn(option, context)
        if r is None:
            continue
        r = dict({'margin': 0.0, 'gives_up': '', 'why': '', 'evidence': ''}, **r, check=name, layer=layer)
        out.append(r)
        settled = r['outcome'] == 'invalid'
    return out
