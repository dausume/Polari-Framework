"""
@module magnetics.magnetic_netlist

mag-3: the DATA-DRIVEN reluctance-network solver — circuit rows in,
fluxes out, through the registered 'magnetic-netlist' compiler.
Modified nodal analysis over the permeance matrix (numpy lstsq):
unknowns = node magnetic potentials + source-branch fluxes, so ideal
MMF sources (coils, flux probes) stamp cleanly.

Honesty rules (the electrodevice mirror):
- element materials resolve against Section-A catalog rows — a
  missing material/mu refuses BY NAME, never a default;
- SATURATION: linear solve ALWAYS, then per-element B vs the
  material's B_sat — exceeded elements come back FLAGGED with the
  suggestion (bigger area / lower drive / better material); the run
  never silently lies. Nonlinear mu(B) iteration = a later rung,
  data-gated on B-H curves;
- elements on UNDECLARED flux nodes are a suggestion riding the
  result (declare the FluxNodeDefinition row or fix the typo);
- optional SPICE parity renders the same network as resistors via
  the analogy — gated on the electrodevice module + ngspice, refusal
  names both.
"""

import json

import numpy as np

MU0 = 4.0e-7 * np.pi


def _rows(manager, class_name):
    table = getattr(manager, 'objectTables', {}).get(class_name, {})
    return (list(table.values()) if isinstance(table, dict)
            else list(table))


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', None) == name:
            return row
    return None


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


def circuit_rows(manager, circuit_name):
    circuit = _named(manager, 'MagneticCircuitDefinition',
                     circuit_name)
    if circuit is None:
        raise ValueError(f"no MagneticCircuitDefinition named "
                         f"'{circuit_name}'")
    elements = sorted(
        (e for e in _rows(manager, 'MagneticElementDefinition')
         if getattr(e, 'circuit_name', '') == circuit_name),
        key=lambda e: getattr(e, 'name', ''))
    if not elements:
        raise ValueError(f"circuit '{circuit_name}' has no "
                         f'MagneticElementDefinition rows')
    nodes = [n for n in _rows(manager, 'FluxNodeDefinition')
             if getattr(n, 'circuit_name', '') == circuit_name]
    return circuit, elements, nodes


def _material_prop(manager, material_ref, prop, element_name):
    """Property value from the Section-A catalog — refusal by name,
    never a default."""
    opt = _named(manager, 'MagneticMaterialOption', material_ref)
    if opt is None:
        raise ValueError(
            f'element "{element_name}" references unknown material '
            f'"{material_ref}" — seed the MagneticMaterialOption '
            f'row first')
    props = _loads(opt, 'properties_json', {})
    entry = props.get(prop)
    if not isinstance(entry, dict) or entry.get('value') is None:
        raise ValueError(
            f'material "{material_ref}" has no {prop} value — '
            f'element "{element_name}" cannot solve without it '
            f'(measure or cite it on the catalog row)')
    return float(entry['value']), entry.get('provenance', '')


def _element_branch(manager, element, overrides=None):
    """One element -> branch dict {kind, nodes, reluctance?, mmf?,
    area?, material_ref?, provenance}. Overrides patch params for
    sweeps without touching the row."""
    params = _loads(element, 'params_json', {})
    if overrides and getattr(element, 'name', '') in overrides:
        params = {**params, **overrides[getattr(element, 'name', '')]}
    nodes = _loads(element, 'nodes_json', [])
    if len(nodes) != 2:
        raise ValueError(
            f'element "{getattr(element, "name", "?")}" needs '
            f'exactly 2 nodes_json entries, got {nodes}')
    kind = getattr(element, 'kind', '')
    name = getattr(element, 'name', '?')
    branch = {'name': name, 'kind': kind, 'nodes': nodes,
              'provenance': ''}
    if kind == 'mmf-coil':
        branch['mmf'] = (float(params.get('turns', 0))
                         * float(params.get('amps', 0.0)))
    elif kind == 'flux-probe':
        branch['mmf'] = 0.0
    elif kind == 'core-segment':
        mu, prov = _material_prop(manager,
                                  params.get('material_ref', ''),
                                  'mu_r_eff', name)
        length = float(params['length_m'])
        area = float(params['area_m2'])
        branch['reluctance'] = length / (MU0 * mu * area)
        branch['area'] = area
        branch['material_ref'] = params.get('material_ref', '')
        branch['provenance'] = prov
    elif kind == 'air-gap':
        length = float(params['length_m'])
        area = float(params['area_m2'])
        fringing = float(params.get('fringing_factor', 1.0))
        branch['reluctance'] = length / (MU0 * area * fringing)
        branch['area'] = area * fringing
        branch['fringing'] = fringing
    elif kind == 'magnet':
        material = params.get('material_ref', '')
        h_c, prov = _material_prop(manager, material, 'h_c_ka_m',
                                   name)
        mu, _ = _material_prop(manager, material, 'mu_r_eff', name)
        length = float(params['length_m'])
        area = float(params['area_m2'])
        # Thevenin: MMF = H_c * l_m behind the recoil reluctance.
        branch['mmf'] = h_c * 1000.0 * length
        branch['reluctance'] = length / (MU0 * mu * area)
        branch['area'] = area
        branch['material_ref'] = material
        branch['provenance'] = prov
    elif kind == 'leakage-path':
        branch['reluctance'] = float(params['reluctance_per_wb'])
    else:
        raise ValueError(f'unknown element kind "{kind}" on '
                         f'"{name}"')
    return branch


def solve_network(manager, circuit_name, overrides=None):
    """MNA solve -> per-element flux (Wb), B (T) where area is
    known, MMF drops, node potentials, saturation flags, and
    undeclared-node suggestions."""
    circuit, elements, declared = circuit_rows(manager, circuit_name)
    branches = [_element_branch(manager, e, overrides)
                for e in elements]

    node_names = sorted({n for b in branches for n in b['nodes']}
                        - {'0'})
    index = {n: i for i, n in enumerate(node_names)}
    sources = [b for b in branches
               if 'mmf' in b and 'reluctance' not in b]
    n_nodes, n_src = len(node_names), len(sources)
    A = np.zeros((n_nodes + n_src, n_nodes + n_src))
    z = np.zeros(n_nodes + n_src)

    def stamp_permeance(n1, n2, g):
        for a, sign_a in ((n1, 1), (n2, -1)):
            if a == '0':
                continue
            i = index[a]
            A[i, i] += g
            for b, sign_b in ((n1, 1), (n2, -1)):
                if b == '0' or b == a:
                    continue
                A[i, index[b]] -= g

    for b in branches:
        if 'reluctance' in b:
            g = 1.0 / b['reluctance']
            stamp_permeance(b['nodes'][0], b['nodes'][1], g)
            if 'mmf' in b:          # magnet: Norton injection
                j = b['mmf'] / b['reluctance']
                if b['nodes'][0] != '0':
                    z[index[b['nodes'][0]]] += j
                if b['nodes'][1] != '0':
                    z[index[b['nodes'][1]]] -= j
    for k, b in enumerate(sources):
        row = n_nodes + k
        n_pos, n_neg = b['nodes']
        if n_pos != '0':
            A[index[n_pos], row] += 1.0
            A[row, index[n_pos]] += 1.0
        if n_neg != '0':
            A[index[n_neg], row] -= 1.0
            A[row, index[n_neg]] -= 1.0
        z[row] = b['mmf']

    # Direct solve — the MNA matrix mixes ~1e-9 permeances with
    # unit source stamps; lstsq's rank cutoff loses ~1e-4 relative
    # accuracy there. Singular systems (floating subcircuits) fall
    # back to lstsq.
    try:
        solution = np.linalg.solve(A, z)
    except np.linalg.LinAlgError:
        solution, *_ = np.linalg.lstsq(A, z, rcond=None)
    potentials = {n: float(solution[i]) for n, i in index.items()}
    potentials['0'] = 0.0

    results, flags = [], []
    src_flux = {id(b): -float(solution[len(node_names) + k])
                for k, b in enumerate(sources)}
    for b in branches:
        n1, n2 = b['nodes']
        drop = potentials[n1] - potentials[n2]
        if 'reluctance' in b:
            flux = (drop + b.get('mmf', 0.0)) / b['reluctance'] \
                if 'mmf' in b else drop / b['reluctance']
            # magnet convention: internal MMF drives flux OUT of the
            # first node, so flux = (mmf - drop_internal)/R with the
            # Norton stamp already handled; recompute from Norton:
            if b['kind'] == 'magnet':
                flux = (b['mmf'] - drop) / b['reluctance']
        else:
            # mmf-coil reports DELIVERED flux (out of the + node);
            # flux-probe reports through-flux first->second node.
            flux = (src_flux[id(b)] if b['kind'] == 'mmf-coil'
                    else -src_flux[id(b)])
        entry = {'element': b['name'], 'kind': b['kind'],
                 'nodes': b['nodes'], 'fluxWb': float(flux),
                 'mmfDropAt': round(drop, 6)}
        if 'reluctance' in b:
            entry['reluctance'] = b['reluctance']
        if b.get('area'):
            B = flux / b['area']
            entry['fluxDensityT'] = round(B, 9)
            material = b.get('material_ref', '')
            if material:
                entry['materialRef'] = material
                entry['muProvenance'] = b.get('provenance', '')
                opt = _named(manager, 'MagneticMaterialOption',
                             material)
                props = _loads(opt, 'properties_json', {})
                b_sat = (props.get('b_sat_t') or {}).get('value')
                if b_sat is not None and abs(B) > float(b_sat):
                    flags.append({
                        'element': b['name'],
                        'fluxDensityT': round(B, 6),
                        'bSatT': float(b_sat),
                        'refusalGrade': 'FLAGGED-not-refused',
                        'suggestion': {
                            'evidence': 'linear solve exceeded '
                                        'B_sat — the linear answer '
                                        'is optimistic here',
                            'knob': 'MagneticElementDefinition.'
                                    'params_json',
                            'action': 'bigger area / lower drive / '
                                      'better material (nonlinear '
                                      'mu(B) = later rung, needs '
                                      'B-H rows)'}})
        results.append(entry)

    suggestions = []
    declared_names = {getattr(n, 'node', '') for n in declared}
    undeclared = ({n for b in branches for n in b['nodes']}
                  - declared_names)
    if undeclared:
        suggestions.append({
            'knob': 'FluxNodeDefinition',
            'action': f'nodes {sorted(undeclared)} are wired but '
                      f'undeclared — declare them (or fix the '
                      f'typo)'})
    return {'ok': True, 'circuit': circuit_name,
            'elements': results,
            'nodePotentials': {k: round(v, 6)
                               for k, v in potentials.items()},
            'saturationFlags': flags,
            'suggestions': suggestions,
            'validity': 'linear magnetostatics (Hopkinson network); '
                        'hysteresis/remanence dynamics out of '
                        'scope; leakage only where modeled as rows'}


def run_analyses(manager, circuit_name):
    """The circuit's analyses_json executed in order: 'op' = one
    solve; 'sweep' = a parameter sweep over one element (overrides,
    never row mutation)."""
    circuit = _named(manager, 'MagneticCircuitDefinition',
                     circuit_name)
    if circuit is None:
        return {'ok': False,
                'refusal': f'no MagneticCircuitDefinition named '
                           f'"{circuit_name}"'}
    out = {'ok': True, 'circuit': circuit_name, 'analyses': []}
    try:
        for spec in _loads(circuit, 'analyses_json', []):
            if spec.get('type') == 'op':
                out['analyses'].append(
                    {'type': 'op',
                     'result': solve_network(manager, circuit_name)})
            elif spec.get('type') == 'sweep':
                element = spec.get('element', '')
                param = spec.get('param', '')
                points = []
                for value in spec.get('values', []):
                    solved = solve_network(
                        manager, circuit_name,
                        overrides={element: {param: value}})
                    points.append({'value': value,
                                   'result': solved})
                out['analyses'].append(
                    {'type': 'sweep', 'element': element,
                     'param': param, 'points': points})
            else:
                out['analyses'].append(
                    {'type': spec.get('type', '?'),
                     'refusal': 'unknown analysis type'})
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    return out


def compile_magnetic(domain_rows):
    """Compiler-contract entry ('magnetic-netlist'):
    {'manager', 'circuit_name'} -> solved-network artifact."""
    manager = domain_rows['manager']
    circuit_name = domain_rows['circuit_name']
    solved = run_analyses(manager, circuit_name)
    return {'definition': None,
            'artifacts': [{'kind': 'magnetic-solve',
                           'name': f'{circuit_name}.solve.json',
                           'text': json.dumps(solved)}],
            'suggestions': (solved.get('analyses', [{}])[0]
                            .get('result', {}).get('suggestions', [])
                            if solved.get('ok') else [])}


SEED_MAGNETIC_COMPILER = {
    'name': 'magnetic-netlist',
    'domain': 'magnetics',
    'compiler_ref': 'magnetics.magnetic_netlist:compile_magnetic',
    'description': 'MagneticElementDefinition/FluxNodeDefinition '
                   'rows -> a solved reluctance network (Hopkinson '
                   'analogy; MNA over the permeance matrix); '
                   'materials resolve against the Section-A '
                   'catalog, saturation is flagged never hidden.',
    'enabled': True,
}


def render_spice_analog(manager, circuit_name):
    """The SAME network as a SPICE resistor netlist through the
    analogy (MMF -> V, reluctance -> R, flux -> I) — the parity
    text; running it needs electrodevice + ngspice (parity_run)."""
    _, elements, _ = circuit_rows(manager, circuit_name)
    lines = [f'* magnetic analogy of {circuit_name} '
             f'(V~MMF, R~reluctance, I~flux)']
    probes = []
    for e in elements:
        b = _element_branch(manager, e)
        n1, n2 = b['nodes']
        if b['kind'] in ('mmf-coil', 'flux-probe'):
            lines.append(f'v{b["name"]} {n1} {n2} dc {b["mmf"]}')
            probes.append(f'i(v{b["name"]})')
        elif b['kind'] == 'magnet':
            # Thevenin: source + internal resistance via a midnode.
            mid = f'{b["name"]}_int'
            lines.append(f'v{b["name"]} {n1} {mid} dc '
                         f'{-b["mmf"]}')
            lines.append(f'r{b["name"]} {mid} {n2} '
                         f'{b["reluctance"]}')
            probes.append(f'i(v{b["name"]})')
        else:
            lines.append(f'r{b["name"]} {n1} {n2} '
                         f'{b["reluctance"]}')
    lines.append('.op')
    lines.append('.control')
    lines.append('run')
    for p in probes:
        lines.append(f'print {p}')
    lines.append('.endc')
    lines.append('.end')
    return '\n'.join(lines)


def parity_run(manager, circuit_name):
    """Run the analogy netlist through electrodevice's ngspice
    runner and compare source fluxes — two solvers, one truth.
    Gated: refuses naming the missing capability."""
    try:
        from electrodevice.circuit_netlist import run_netlist
    except ImportError:
        return {'ok': False,
                'refusal': 'electrodevice module not enabled on '
                           'this instance — SPICE parity needs it '
                           '(POLARI_MODULES)'}
    netlist = render_spice_analog(manager, circuit_name)
    spice = run_netlist(netlist, label=f'mag-{circuit_name}')
    if not spice.get('ok'):
        return {'ok': False,
                'refusal': spice.get('error',
                                     'ngspice run failed'),
                'netlist': netlist}
    ours = solve_network(manager, circuit_name)
    comparison = []
    for entry in ours['elements']:
        if entry['kind'] not in ('mmf-coil', 'flux-probe', 'magnet'):
            continue
        key = f'i(v{entry["element"]})'
        spice_flux = spice['measurements'].get(key)
        if spice_flux is None:
            continue
        comparison.append({
            'element': entry['element'],
            'oursWb': entry['fluxWb'],
            # SPICE current convention: positive INTO the source's
            # first node = negative of our branch flux.
            'spiceWb': -spice_flux,
            'agrees': abs(entry['fluxWb'] - (-spice_flux))
            <= max(1e-12, abs(entry['fluxWb']) * 1e-3)})
    return {'ok': True, 'circuit': circuit_name,
            'comparison': comparison,
            'allAgree': all(c['agrees'] for c in comparison),
            'netlist': netlist}
