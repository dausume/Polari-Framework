"""
@cross-cutting
@module supplychain.custom.chain_analysis
@tags @xc:bindings

chain-1 analysis — roll a SupplyChainDefinition up into one ledger:
the MATERIALS inventory (all bio-derivable outputs), the FOOD inventory,
and the CARBON balance (sinks − sources). Also a dependency check: is
every node input satisfied by an upstream flow or an external feedstock?
Duck-typed manager (stdlib-only selftests). Declared throughputs are
flagged priors until live-resolved from each module.

@consumers
  - supplychain.chain_api
@see nutrition/ aquaponics/ tanks/ microalgae/ biomining/ waxsupply/
"""

import json

PRIORS_NOTE = ('node throughputs are declared priors until live-resolved '
               'from each module')


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _f(row, attr, default=0.0):
    value = getattr(row, attr, default)
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def _parse(text, fallback='[]'):
    try:
        loaded = json.loads(text or fallback)
        return loaded if loaded is not None else json.loads(fallback)
    except Exception:
        return json.loads(fallback)


def _chain_nodes(manager, chain):
    names = _parse(getattr(chain, 'node_names_json', '[]'))
    return [n for n in (_named(manager, 'SupplyNode', nm)
                        for nm in names) if n is not None]


def chain_inventory(manager, chain_name):
    """The full rollup: materials + food + carbon + energy, aggregated
    across all node outputs, plus per-node and per-module breakdowns."""
    chain = _named(manager, 'SupplyChainDefinition', chain_name)
    if chain is None:
        return {'ok': False,
                'error': f"no SupplyChainDefinition named '{chain_name}'"}
    nodes = _chain_nodes(manager, chain)
    if not nodes:
        return {'ok': False,
                'error': f"chain '{chain_name}' has no resolvable nodes",
                'suggestion': {'knob': 'SupplyChainDefinition.'
                                       'node_names_json',
                               'action': 'add SupplyNode names',
                               'evidence': 'nothing to account'}}
    by_kind = {}          # kind -> {resource -> {rate, unit}}
    by_module = {}        # module -> total output entries
    for node in nodes:
        module = getattr(node, 'module', '')
        for out in _parse(getattr(node, 'outputs_json', '[]')):
            kind = out.get('kind', 'material')
            resource = out.get('resource', '')
            rate = float(out.get('ratePerYear', 0) or 0)
            unit = out.get('unit', '')
            entry = by_kind.setdefault(kind, {}).setdefault(
                resource, {'ratePerYear': 0.0, 'unit': unit})
            entry['ratePerYear'] = round(entry['ratePerYear'] + rate, 3)
            by_module.setdefault(module, []).append(
                {'resource': resource, 'kind': kind, 'ratePerYear': rate})
    materials = sorted(by_kind.get('material', {}).keys())
    foods = sorted(by_kind.get('food', {}).keys())
    return {
        'ok': True, 'chain': chain_name, 'nodeCount': len(nodes),
        'materials': by_kind.get('material', {}),
        'foods': by_kind.get('food', {}),
        'carbon': by_kind.get('carbon', {}),
        'nutrients': by_kind.get('nutrient', {}),
        'materialResourceCount': len(materials),
        'foodResourceCount': len(foods),
        'byModule': {m: len(v) for m, v in by_module.items()},
        'priorsFlagged': True, 'note': PRIORS_NOTE}


def carbon_balance(manager, chain_name):
    """Carbon sinks vs sources across the chain → net sequestered/cycled
    per year, with the per-node contributions."""
    inv = chain_inventory(manager, chain_name)
    if not inv.get('ok'):
        return inv
    chain = _named(manager, 'SupplyChainDefinition', chain_name)
    sinks = 0.0
    sources = 0.0
    contributions = []
    for node in _chain_nodes(manager, chain):
        for out in _parse(getattr(node, 'outputs_json', '[]')):
            if out.get('kind') != 'carbon':
                continue
            rate = float(out.get('ratePerYear', 0) or 0)
            # positive = sequestered/fixed (sink); negative = emitted.
            if rate >= 0:
                sinks += rate
            else:
                sources += -rate
            contributions.append({
                'node': getattr(node, 'name', ''),
                'resource': out.get('resource', ''),
                'ratePerYear': rate, 'unit': out.get('unit', 'g')})
    net = sinks - sources
    return {
        'ok': True, 'chain': chain_name,
        'carbonSinkPerYear': round(sinks, 3),
        'carbonSourcePerYear': round(sources, 3),
        'netSequesteredPerYear': round(net, 3),
        'isNetSink': net > 0,
        'contributions': contributions,
        'verdict': ('net carbon SINK' if net > 0 else
                    'net carbon SOURCE — add algae reactors / biochar / '
                    'macroalgae density to close it'),
        'priorsFlagged': True, 'note': PRIORS_NOTE}


def dependency_check(manager, chain_name):
    """Is every node INPUT satisfied by an upstream flow or an external
    feedstock node? Unmet inputs are named (honest-absence)."""
    chain = _named(manager, 'SupplyChainDefinition', chain_name)
    if chain is None:
        return {'ok': False,
                'error': f"no SupplyChainDefinition named '{chain_name}'"}
    nodes = _chain_nodes(manager, chain)
    flow_names = _parse(getattr(chain, 'flow_names_json', '[]'))
    flows = [f for f in (_named(manager, 'SupplyFlow', fn)
                         for fn in flow_names) if f is not None]
    # resources delivered TO each node by flows + external feedstock.
    delivered = {}
    for f in flows:
        delivered.setdefault(getattr(f, 'to_node', ''), set()).add(
            getattr(f, 'resource', ''))
    external = {getattr(n, 'name', '') for n in nodes
                if getattr(n, 'module', '') == 'external-feedstock'}
    unmet = []
    for node in nodes:
        node_name = getattr(node, 'name', '')
        got = delivered.get(node_name, set())
        for inp in _parse(getattr(node, 'inputs_json', '[]')):
            resource = inp.get('resource', '')
            # satisfied if a flow delivers it, or an external feedstock
            # supplies that resource anywhere in the chain.
            supplied_ext = any(
                resource in {o.get('resource')
                             for o in _parse(getattr(
                                 _named(manager, 'SupplyNode', en),
                                 'outputs_json', '[]'))}
                for en in external)
            if resource not in got and not supplied_ext:
                unmet.append({'node': node_name, 'resource': resource,
                              'kind': inp.get('kind', '')})
    return {
        'ok': True, 'chain': chain_name,
        'satisfied': not unmet, 'unmetInputs': unmet,
        'flowCount': len(flows),
        'limitingFactor': None if not unmet else
            f'{len(unmet)} unmet input(s) — add a flow or an '
            f'external-feedstock node',
        'note': 'a node input is met by an upstream flow or an '
                'external-feedstock output.'}
