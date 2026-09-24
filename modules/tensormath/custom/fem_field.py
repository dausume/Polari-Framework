"""
@module tensormath.custom.fem_field

THE σ FIELD, WRITTEN DOWN SO IT CAN BE SEEN (tt-6; plan §G.9). The FEM engine returns u/ε/σ as arrays; a sim-space
binding renders ROWS of a CLASS. This module turns one solved case into ONE `FEMFieldState` row:

    elements_json  [[cx, cy, σ_vm, σ_xx, σ_yy, σ_xy, area], …]   one per element (P1: constant per triangle)
    nodes_json     [[x, y, u_x, u_y], …]                          one per node
    triangles_json [[i, j, k], …]                                 the mesh (node indices) — its edges are drawable (tt-9)

Two doors to the same builder:
  * `field_row_from_solution(sol, case_name)` — from `tensor_ops.fem_case_solution` (manager path; the API's
    `POST /api/tensormath/fem/{case}/materialise` and the tensortree page).
  * `seed_field_rows()` — from the SEED case and the SEED material option, with no manager (so the row exists
    from first boot); if the engine cannot solve (scikit-fem absent, magnetics seed unreachable) it returns []
    and says why — the plate then shows "bound but has no instances" until someone materialises it. Nothing is
    pretended: E/ν provenance is the cited line of the material option either way.

von Mises in plane stress: σ_vm = sqrt(σ_xx² − σ_xx σ_yy + σ_yy² + 3 σ_xy²).
"""
import datetime
import json

FIELD_COLUMNS = ['cx', 'cy', 'sigma_vm', 'sigma_xx', 'sigma_yy', 'sigma_xy', 'area']
NODE_COLUMNS = ['x', 'y', 'u_x', 'u_y']
SEED_FIELD_NAME = 'tt2-plate-tension-field'


def _von_mises(sxx, syy, sxy):
    return (sxx * sxx - sxx * syy + syy * syy + 3.0 * sxy * sxy) ** 0.5


def _tri_area(nodes, tri):
    (x1, y1), (x2, y2), (x3, y3) = (nodes[i][:2] for i in tri)
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2.0


def field_row_from_tensor_field(tf, case_name, material_provenance='', assumption='', engine_note=''):
    """Build the FEMFieldState row dict from an engine tensorField (nodes/triangles/displacement/stress/centroids)."""
    nodes = [list(map(float, n)) for n in tf['nodes']]
    tris = [list(map(int, t)) for t in tf['triangles']]
    disp = [list(map(float, d)) for d in tf['displacement']]
    stress = tf['stress']
    cents = [list(map(float, c)) for c in tf['centroids']]
    elements = []
    for e, (c, s, t) in enumerate(zip(cents, stress, tris)):
        sxx, sxy, syy = float(s[0][0]), float(s[0][1]), float(s[1][1])
        elements.append([c[0], c[1], _von_mises(sxx, syy, sxy), sxx, syy, sxy, _tri_area(nodes, t)])
    node_rows = [[n[0], n[1], d[0], d[1]] for n, d in zip(nodes, disp)]
    vms = [e[2] for e in elements] or [0.0]
    umax = max((abs(d[0]) ** 2 + abs(d[1]) ** 2) ** 0.5 for d in disp) if disp else 0.0
    return {'name': '%s-field' % case_name, 'triangles_json': json.dumps(tris), 'description': 'σ per element (von Mises + components) and u per node of the FEM case %s, as a row a 2-D field binding can render' % case_name,
            'case': case_name, 'elements_json': json.dumps(elements), 'nodes_json': json.dumps(node_rows), 'n_elements': len(elements), 'n_nodes': len(node_rows),
            'sigma_vm_max': max(vms), 'sigma_vm_min': min(vms), 'u_max': umax, 'assumption': assumption or str(tf.get('lame', {}).get('assumption', '')),
            'material_provenance': material_provenance, 'columns_json': json.dumps(FIELD_COLUMNS), 'node_columns_json': json.dumps(NODE_COLUMNS),
            'computed_at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'provenance': engine_note or 'materialsScience.engines.fem_engine.solve_elasticity_2d(include_field=True); σ_vm plane-stress form'}


def field_row_from_solution(sol, case_name):
    """From `tensor_ops.fem_case_solution(manager, case)` (numpy arrays inside)."""
    f = sol['fields']
    tf = {'nodes': f['nodes'].tolist(), 'triangles': f['triangles'].tolist(), 'displacement': f['displacement'].tolist(),
          'stress': f['stress'].tolist(), 'centroids': f['centroids'].tolist(), 'lame': sol.get('lame', {})}
    return field_row_from_tensor_field(tf, case_name, material_provenance=sol.get('material_provenance', ''), assumption=sol.get('assumption', ''))


def seed_field_rows(cases=None):
    """The seed row(s) with no manager: solve the seed case with E/ν from the seed material option. [] + reason on failure."""
    try:
        from tensormath.tensormath_seed import SEED_FEM_CASES
        from magnetics.magnet_seed import SEED_MATERIAL_OPTIONS
        from materialsScience.engines.fem_engine import solve_elasticity_2d
    except Exception as exc:   # pragma: no cover - environment-dependent
        print('[tensormath.fem_field] seed field skipped: %s' % exc, flush=True)
        return []
    out = []
    for case in (cases or SEED_FEM_CASES):
        try:
            dom = json.loads(case['domain_json']); mats = json.loads(case['materials_json']); bcs = json.loads(case['boundary_conditions_json'])
            mesh = json.loads(case['mesh_json']); solver = json.loads(case['solver_json'])
            opt_name = mats[0]['material_option']
            opt = next(o for o in SEED_MATERIAL_OPTIONS if o.get('name') == opt_name)
            props = json.loads(opt['properties_json']) if isinstance(opt.get('properties_json'), str) else opt.get('properties_json', {})
            E, nu = props['youngs_modulus_mpa'], props['poisson_ratio']
            prov = '%s: E = %s MPa (%s), nu = %s (%s)' % (opt_name, E['value'], E.get('provenance', '?'), nu['value'], nu.get('provenance', '?'))
            r = solve_elasticity_2d(width=float(dom.get('width', 1.0)), height=float(dom.get('height', 1.0)), youngs_modulus=float(E['value']) * 1e6, poisson_ratio=float(nu['value']),
                                    tractions=tuple(bcs.get('tractions', [])), fixed_edges=tuple(bcs.get('fixed_edges', [])), assumption=str(solver.get('assumption', 'plane-stress')),
                                    hole_radius=dom.get('hole_radius'), hole_center=dom.get('hole_center'), refine=int(mesh.get('refine', 2)), include_field=True)
            if not r.get('ok'):
                print('[tensormath.fem_field] seed field for %s refused: %s' % (case['name'], r.get('error')), flush=True)
                continue
            out.append(field_row_from_tensor_field(r['tensorField'], case['name'], material_provenance=prov, assumption=r.get('assumption', '')))
        except Exception as exc:
            print('[tensormath.fem_field] seed field for %s skipped: %s' % (case.get('name'), exc), flush=True)
    return out


class LazySeedRows(list):
    """A seed list computed on first use (the FEM solve runs at seed time, not import time)."""

    def __init__(self, builder):
        super().__init__()
        self._builder, self._done = builder, False

    def _fill(self):
        if not self._done:
            self._done = True
            self.extend(self._builder())

    def __iter__(self):
        self._fill()
        return super().__iter__()

    def __len__(self):
        self._fill()
        return super().__len__()

    def __getitem__(self, i):
        self._fill()
        return super().__getitem__(i)

    def __bool__(self):
        return True
