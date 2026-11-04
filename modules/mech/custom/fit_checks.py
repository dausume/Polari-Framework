"""
@module mech.custom.fit_checks

mxc-2: the fit checks — what BoardConflict is to a PCB, MechConflict
is to an assembly. Every check is a pure function over NUMBERS
(thread size, engagement, hole diameter, cell counts, loads) with
the knob tables beside it, and `check_assembly` is the one walk that
pulls those numbers out of the rows and runs them all (plus the DOF
solver's findings). Nothing here reads a material row: the counter
material CLASS (steel / aluminium / plastic) comes in as a parameter,
so these checks do not depend on the material slice.

Catalogue access goes through ONE accessor, `variant_params`, which
reads a MechPartVariant's `parameters_json` (fallback `dims_json`);
the keys it expects are listed on it. Swapping to the mxc-1
catalogue's real field names is a one-place change.

Knobs (all cited-or-stated, none measured):
  THREAD_ENGAGEMENT_FACTOR  minimum engagement as multiples of d by
                            the material carrying the FEMALE thread
                            (steel 1.0, aluminium 2.0, plastic 2.5 —
                            the shop rule of thumb; a real joint is
                            sized by shear area, mxc-4+)
  ISO_273_CLEARANCE         ISO 273 fine / medium / coarse series
  SLOT_THREADS              which nut threads a slot opening takes
                            (DIN 508 / the 20-30-40-series catalogues)
  DRAWER_LOAD_CENTROID      0.5 = uniform load over the open length

@consumers mech.mech_assembly_selftest, mech.mech_api (mxc-6),
the mxc-5 generator (0 conflicts is its acceptance)
"""

import json
import re

from composition.custom.data_refs import named, rows
from mech.custom.dof_solver import dof_conflicts, solve_dof
from mech.objects.assembly._shared import loads, roles_pair

#: minimum thread engagement, multiples of nominal d, by the class
#: of the material that carries the FEMALE thread.
THREAD_ENGAGEMENT_FACTOR = {'steel': 1.0, 'aluminium': 2.0,
                            'plastic': 2.5, 'brass': 1.5, 'zinc': 1.5}
THREAD_ENGAGEMENT_BASIS = ('shop rule of thumb (Machinery\'s Handbook '
                           'order of magnitude): 1·d steel-in-steel, 2·d '
                           'in aluminium, 2.5·d in plastic — a KNOB until '
                           'a pull-out test replaces it')

#: ISO 273 clearance holes (mm): nominal -> (fine, medium, coarse).
#: The check is against MEDIUM.
ISO_273_CLEARANCE = {
    2.0: (2.2, 2.4, 2.6), 2.5: (2.7, 2.9, 3.1), 3.0: (3.2, 3.4, 3.6),
    4.0: (4.3, 4.5, 4.8), 5.0: (5.3, 5.5, 5.8), 6.0: (6.4, 6.6, 7.0),
    8.0: (8.4, 9.0, 10.0), 10.0: (10.5, 11.0, 12.0),
    12.0: (13.0, 13.5, 14.5),
}

#: slot key -> the nut threads that slot takes. 'slot-B<opening>/
#: <series>'. An M6 nut needs an 8 mm opening (30/40 series); a
#: 20-series B6 slot takes M3-M5 (DIN 508 / NopSCADlib tnut tables).
SLOT_THREADS = {
    'slot-B6/20': ('M3', 'M4', 'M5'),
    'slot-B8/30': ('M4', 'M5', 'M6'),
    'slot-B8/40': ('M5', 'M6', 'M8'),
    'slot-B10/45': ('M6', 'M8', 'M10'),
}

#: fraction of the open length at which a uniformly loaded drawer's
#: weight acts (0.5 = uniform). A front-heavy drawer is a knob > 0.5.
DRAWER_LOAD_CENTROID = 0.5

GRID_PITCH_MM = 42.0


def _g(obj, key, default=''):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def parse_thread(key):
    """'M5x0.8' -> (5.0, 0.8); 'M5' -> (5.0, None); else (None, None)."""
    m = re.match(r'^M(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?$', key or '')
    if not m:
        return None, None
    return float(m.group(1)), (float(m.group(2)) if m.group(2) else None)


def _nominal(d):
    return f'M{int(d) if float(d).is_integer() else d}'


# ---------------------------------------------------------------
# the checks — pure
# ---------------------------------------------------------------

def thread_engagement(d_mm, engagement_mm, counter_material_class):
    """Is `engagement_mm` of an M<d> thread enough in a female thread
    cut in `counter_material_class`? -> {ok, required, actual,
    factor, class, basis}. An unknown class is UNASSESSED (ok=None),
    never a pass."""
    factor = THREAD_ENGAGEMENT_FACTOR.get(counter_material_class)
    if factor is None or d_mm is None:
        return {'ok': None, 'required': None, 'actual': engagement_mm,
                'factor': None, 'class': counter_material_class,
                'why': f'material class "{counter_material_class}" has '
                       f'no engagement factor — unassessed',
                'basis': THREAD_ENGAGEMENT_BASIS}
    required = factor * d_mm
    return {'ok': engagement_mm >= required, 'required': required,
            'actual': engagement_mm, 'factor': factor, 'd': d_mm,
            'class': counter_material_class,
            'basis': THREAD_ENGAGEMENT_BASIS}


def available_engagement(screw_length_mm, stack_mm, female_depth_mm):
    """What is actually engaged: the screw beyond the clamped stack,
    capped by the female thread's depth."""
    beyond = screw_length_mm - stack_mm
    return max(min(beyond, female_depth_mm), 0.0)


def clearance_hole(d_mm, hole_mm):
    """ISO 273: is `hole_mm` at least the MEDIUM clearance for M<d>?
    -> {ok, required, actual, series}. Over the coarse series is
    noted ('loose'), not a conflict."""
    row = ISO_273_CLEARANCE.get(float(d_mm)) if d_mm is not None else None
    if row is None:
        return {'ok': None, 'required': None, 'actual': hole_mm,
                'why': f'no ISO 273 row for M{d_mm} in the table'}
    fine, medium, coarse = row
    return {'ok': hole_mm >= medium, 'required': medium, 'actual': hole_mm,
            'series': {'fine': fine, 'medium': medium, 'coarse': coarse},
            'loose': hole_mm > coarse}


def slot_pairing(rider_key, channel_key, nut_thread_key=''):
    """A T-nut in a slot: the rider's slot key must equal the
    channel's, and the nut's thread must be one the slot takes.
    -> {ok, why}."""
    if rider_key != channel_key:
        return {'ok': False, 'why': f'slot key mismatch: nut is '
                                    f'"{rider_key}", slot is '
                                    f'"{channel_key}"'}
    d, _ = parse_thread(nut_thread_key)
    if d is not None:
        allowed = SLOT_THREADS.get(channel_key)
        if allowed is None:
            return {'ok': None, 'why': f'"{channel_key}" is not in '
                                       f'SLOT_THREADS — unassessed'}
        if _nominal(d) not in allowed:
            return {'ok': False,
                    'why': f'{_nominal(d)} nut in a {channel_key} slot: '
                           f'that opening takes {list(allowed)}'}
    return {'ok': True, 'why': ''}


def feature_pairing(feature_a, feature_b):
    """Plan §3.2: a joint is valid when KEY matches and ROLES pair."""
    if feature_a is None or feature_b is None:
        return {'ok': None, 'why': 'a feature does not resolve'}
    ka, kb = _g(feature_a, 'key'), _g(feature_b, 'key')
    ra, rb = _g(feature_a, 'role'), _g(feature_b, 'role')
    if ka != kb:
        return {'ok': False, 'why': f'key mismatch: "{ka}" vs "{kb}"'}
    if not roles_pair(ra, rb):
        return {'ok': False, 'why': f'roles do not pair: {ra} vs {rb}'}
    return {'ok': True, 'why': ''}


def grid_occupancy(plate_cells, bins):
    """plate_cells = (nx, ny); bins = [{'name', 'origin': (cx, cy),
    'cells': (nx, ny)}] in plate cell coordinates. -> {ok, overflow:
    [...], overlap: [...], occupied, free}."""
    px, py = plate_cells
    occupied = {}
    overflow, overlap = [], []
    for b in bins:
        cx, cy = b['origin']
        nx, ny = b['cells']
        out = [(x, y) for x in range(cx, cx + nx) for y in range(cy, cy + ny)
               if x < 0 or y < 0 or x >= px or y >= py]
        if out:
            overflow.append({'bin': b['name'], 'cells': (nx, ny),
                             'origin': (cx, cy), 'plate': (px, py),
                             'outside': len(out)})
        for x in range(cx, cx + nx):
            for y in range(cy, cy + ny):
                if (x, y) in occupied and occupied[(x, y)] != b['name']:
                    overlap.append({'cell': (x, y),
                                    'bins': [occupied[(x, y)], b['name']]})
                occupied[(x, y)] = b['name']
    inside = {c for c in occupied if 0 <= c[0] < px and 0 <= c[1] < py}
    return {'ok': not overflow and not overlap, 'overflow': overflow,
            'overlap': overlap, 'occupied': len(inside),
            'free': px * py - len(inside)}


def rating_moment_nm(load_rating):
    """A slide's rated tip moment from its load_rating_json: direct
    'moment_nm', else dynamic_load_n over the rated extension with
    the load centroid at DRAWER_LOAD_CENTROID. -> (nm, basis)."""
    if not isinstance(load_rating, dict):
        return None, 'no load rating'
    if load_rating.get('moment_nm') not in (None, -1):
        return float(load_rating['moment_nm']), \
            load_rating.get('basis', 'cited moment')
    dyn = load_rating.get('dynamic_load_n')
    ext = load_rating.get('rated_extension_mm')
    if dyn in (None, -1) or ext in (None, -1):
        return None, 'rating lacks moment_nm or dynamic_load_n + ' \
                     'rated_extension_mm'
    return float(dyn) * float(ext) * DRAWER_LOAD_CENTROID / 1000.0, \
        f'derived: dynamic_load_n x rated_extension_mm x ' \
        f'{DRAWER_LOAD_CENTROID} ({load_rating.get("basis", "?")})'


def cantilever_tip(load_n, extension_mm, load_rating, n_slides=2,
                   centroid=DRAWER_LOAD_CENTROID):
    """Drawer at full extension: tip moment per slide = (load /
    n_slides) x extension x centroid, against the slide's rated
    moment; plain load against dynamic_load_n. -> {ok, moment_nm,
    rated_nm, load_per_slide_n, rated_load_n, overload, basis}."""
    per = load_n / max(n_slides, 1)
    moment = per * extension_mm * centroid / 1000.0
    rated, basis = rating_moment_nm(load_rating)
    rated_load = (load_rating or {}).get('dynamic_load_n')
    overload = (rated_load not in (None, -1)) and per > float(rated_load)
    if rated is None:
        return {'ok': None, 'moment_nm': moment, 'rated_nm': None,
                'load_per_slide_n': per, 'rated_load_n': rated_load,
                'overload': overload, 'why': basis}
    return {'ok': moment <= rated and not overload, 'moment_nm': moment,
            'rated_nm': rated, 'load_per_slide_n': per,
            'rated_load_n': rated_load, 'overload': overload,
            'basis': basis}


# ---------------------------------------------------------------
# row access — ONE accessor for the catalogue
# ---------------------------------------------------------------

def variant_params(variant):
    """The numbers a variant carries, as a dict. Keys used here:
      screws   thread ('M5x0.8'), length (mm)
      T-nuts   thread, slot ('slot-B6/20'), thread_depth (mm),
               material_class (steel | aluminium | plastic)
      brackets thickness (mm), hole_d (mm), material_class
      profiles slot
      bins / baseplates  grid_x, grid_y (cells)
      slides   load_rating {dynamic_load_n, rated_extension_mm |
               moment_nm, basis}, extension_mm
    Reads parameters_json, then dims_json. Swap HERE when the
    catalogue's field names land."""
    if variant is None:
        return {}
    p = loads(_g(variant, 'parameters_json', ''), None)
    if isinstance(p, dict):
        return p          # the mxc-2 contract stand-in: keys as listed above
    # mxc-1 catalogue rows (landed 2026-11-03): axis_values_json carries the
    # variant axes, dims_json the standard's dimension letters. Map them
    # onto the keys the checks read; nothing is invented — a key the
    # catalogue lacks stays absent and the check says so.
    axis = loads(_g(variant, 'axis_values_json', ''), None) or {}
    dims = loads(_g(variant, 'dims_json', ''), None) or {}
    if not isinstance(axis, dict) or not isinstance(dims, dict):
        return {}
    out = dict(dims)
    thread = axis.get('thread') or ('M%g' % dims['d'] if dims.get('d') else None)
    if thread and dims.get('P'):
        out.setdefault('thread', f"{thread}x{dims['P']:g}")
    if dims.get('L') not in (None, -1):
        out.setdefault('length', dims['L'])
    elif axis.get('nominal_length') not in (None, -1):
        out.setdefault('length', axis['nominal_length'])
    slot_type = axis.get('slot_type') or (f"B{dims['slot_w']:g}" if dims.get('slot_w') else None)
    series = dims.get('series') or axis.get('series')
    if slot_type and series:
        out.setdefault('slot', f'slot-{slot_type}/{series}')
    if dims.get('height') not in (None, -1) and axis.get('thread'):
        out.setdefault('thread_depth', dims['height'])   # a T-nut's full height is threaded
    if 'thread_depth' not in out and dims.get('m') not in (None, -1):
        out.setdefault('thread_depth', dims['m'])        # a nut's height m (ISO 4032)
    if dims.get('screw_d') and dims.get('P'):
        out.setdefault('hole_d', dims['screw_d'] + 0.5)  # bracket hole ≈ medium clearance
    for k in ('grid_x', 'grid_y'):
        if axis.get(k) is not None:
            out.setdefault(k, axis[k])
    if dims.get('rated_load_kg_pair') not in (None, -1) and 'load_rating' not in out:
        length = dims.get('length') or axis.get('cut_length') or _g(variant, 'length_mm', -1)
        ratio = dims.get('extension_ratio') or 1.0
        out['load_rating'] = {
            'dynamic_load_n': float(dims['rated_load_kg_pair']) * 9.80665 / 2.0,
            'rated_extension_mm': float(length) * float(ratio) if length not in (None, -1) else -1,
            'basis': 'knob: catalogue rated_load_kg_pair / 2 per slide at full extension (mxc-1 hand:drawer-slide)'}
        out.setdefault('extension_mm', out['load_rating']['rated_extension_mm'])
    return out


#: MechMaterialOption name -> engagement class. Coatings and
#: additives are not a body material and map to nothing.
_OPTION_CLASS_RULES = (
    (('steel', 'stainless'), 'steel'), (('al_',), 'aluminium'),
    (('brass',), 'brass'), (('zinc_alloy',), 'zinc'),
)


def option_engagement_class(option_name, material_class=''):
    """'steel_carbon' -> 'steel', 'al_diecast' -> 'aluminium',
    'petg' (polymer) -> 'plastic'; coatings/additives/unknown -> ''."""
    name = (option_name or '').lower()
    for needles, cls in _OPTION_CLASS_RULES:
        if any(n in name for n in needles):
            return cls
    if material_class in ('polymer', 'elastomer'):
        return 'plastic'
    return ''


def material_class_for(manager, instance, variant):
    """(engagement class, basis) for the body carrying a thread —
    a ROW lookup, never an import: the instance's
    material_option_ref first, else the variant's family default
    (MechPartFamily.material_default_ids_json, first id that is a
    body material, not a coating), else ('', why) = UNASSESSED."""
    opt_name = _g(instance, 'material_option_ref') if instance else ''
    if opt_name:
        opt = named(manager, 'MechMaterialOption', opt_name)
        cls = option_engagement_class(opt_name,
                                      _g(opt, 'material_class') if opt else '')
        if cls:
            return cls, f'instance material_option_ref {opt_name}'
        return '', f'material option "{opt_name}" maps to no engagement class'
    fam = named(manager, 'MechPartFamily', _g(variant, 'family_ref')) \
        if variant is not None else None
    for oid in loads(_g(fam, 'material_default_ids_json', '[]'), []) \
            if fam is not None else []:
        opt = named(manager, 'MechMaterialOption', oid)
        cls = option_engagement_class(oid, _g(opt, 'material_class')
                                      if opt else '')
        if cls:
            return cls, (f'family {_g(fam, "name")} default material '
                         f'{oid} (instance material_option_ref is \'\')')
    return '', 'no material option on the instance and no family default'


def _features_of(manager, variant_name):
    return [f for f in rows(manager, 'MechFeature')
            if _g(f, 'variant_ref') == variant_name]


def _feature(manager, variant_name, kind, role=None):
    for f in _features_of(manager, variant_name):
        if _g(f, 'kind') == kind and (role is None or _g(f, 'role') == role):
            return f
    return None


def _conflict(assembly, name, kind, detail, severity='error', notes=''):
    return {'name': f'{assembly}:{name}', 'assembly_ref': assembly,
            'kind': kind, 'severity': severity,
            'detail_json': json.dumps(detail, default=str),
            'notes': notes}


def _placement_origin(instance):
    p = loads(_g(instance, 'placement_json', '{}'), {})
    o = p.get('origin') if isinstance(p, dict) else None
    return list(o) if isinstance(o, (list, tuple)) else [0.0, 0.0, 0.0]


def check_fastened_joint(joint, instances, manager, assembly_name):
    """Fit checks for one fixed joint realised by [screw, nut]:
    feature pairing, screw<->nut thread, nut<->slot, clearance hole
    in the clamped part, thread engagement in the nut's material."""
    out = []
    jn = _g(joint, 'name')
    fasteners = loads(_g(joint, 'fastener_refs_json', '[]'), [])
    screws, nuts = [], []
    for fn in fasteners:
        inst = instances.get(fn)
        v = _g(inst, 'variant_ref') if inst else ''
        if _feature(manager, v, 'thread', 'male') is not None:
            screws.append((fn, v))
        elif _feature(manager, v, 'thread', 'female') is not None:
            nuts.append((fn, v))
    if not screws or not nuts:
        return out
    screw_name, screw_v = screws[0]
    nut_name, nut_v = nuts[0]
    male = _feature(manager, screw_v, 'thread', 'male')
    female = _feature(manager, nut_v, 'thread', 'female')
    pair = feature_pairing(male, female)
    if pair['ok'] is False:
        out.append(_conflict(assembly_name, f'{jn}:thread', 'wrong_pairing',
                             {'joint': jn, 'screw': screw_name,
                              'nut': nut_name, 'why': pair['why']}))
    d, _pitch = parse_thread(_g(male, 'key'))
    sp = variant_params(named(manager, 'MechPartVariant', screw_v))
    npar = variant_params(named(manager, 'MechPartVariant', nut_v))
    # nut in the slot of the OTHER body (instance_b by convention,
    # either side accepted)
    rider = _feature(manager, nut_v, 'slot', 'rider')
    if rider is not None:
        channel = None
        for side in ('instance_b', 'instance_a'):
            inst = instances.get(_g(joint, side))
            channel = _feature(manager, _g(inst, 'variant_ref'), 'slot',
                               'channel') if inst else None
            if channel is not None:
                break
        if channel is None:
            out.append(_conflict(assembly_name, f'{jn}:slot', 'wrong_pairing',
                                 {'joint': jn, 'nut': nut_name,
                                  'why': 'T-nut on a joint whose bodies '
                                         'have no slot channel'}))
        else:
            sp_ = slot_pairing(_g(rider, 'key'), _g(channel, 'key'),
                               _g(female, 'key'))
            if sp_['ok'] is False:
                out.append(_conflict(assembly_name, f'{jn}:slot',
                                     'wrong_pairing',
                                     {'joint': jn, 'nut': nut_name,
                                      'why': sp_['why']}))
    # clamped part = the body that is not the slot carrier
    clamped = None
    for side in ('instance_a', 'instance_b'):
        inst = instances.get(_g(joint, side))
        v = _g(inst, 'variant_ref') if inst else ''
        if inst is not None and _feature(manager, v, 'slot', 'channel') is None:
            clamped = inst
            break
    cp = variant_params(named(manager, 'MechPartVariant',
                              _g(clamped, 'variant_ref'))) if clamped else {}
    if cp.get('hole_d') is not None and d is not None:
        ch = clearance_hole(d, float(cp['hole_d']))
        if ch['ok'] is False:
            out.append(_conflict(assembly_name, f'{jn}:hole',
                                 'clearance_hole_small',
                                 {'joint': jn, 'part': _g(clamped, 'name'),
                                  **ch}))
    stack = float(cp.get('thickness', 0.0) or 0.0)
    if sp.get('length') is not None and npar.get('thread_depth') is not None \
            and d is not None:
        actual = available_engagement(float(sp['length']), stack,
                                      float(npar['thread_depth']))
        cls = npar.get('material_class', '')
        basis = 'variant parameters material_class'
        if not cls:
            cls, basis = material_class_for(
                manager, instances.get(nut_name),
                named(manager, 'MechPartVariant', nut_v))
        eng = thread_engagement(d, actual, cls)
        eng.update({'joint': jn, 'screw': screw_name, 'nut': nut_name,
                    'screw_length': sp['length'], 'stack': stack,
                    'female_depth': npar['thread_depth'],
                    'class_basis': basis})
        if eng['ok'] is False:
            out.append(_conflict(assembly_name, f'{jn}:engagement',
                                 'thread_engagement_short', eng))
        elif eng['ok'] is None:
            out.append(_conflict(assembly_name, f'{jn}:engagement',
                                 'thread_engagement_short', eng,
                                 severity='warning',
                                 notes='unassessed: material class '
                                       'unknown'))
    return out


def check_grid(assembly_name, joints, instances, manager):
    """Per baseplate: the bins seated on it (by grid joints) against
    its cells, positions from the instances' placements."""
    out = []
    plates = {}
    for j in joints:
        if _g(j, 'kind') != 'grid':
            continue
        a, b = instances.get(_g(j, 'instance_a')), \
            instances.get(_g(j, 'instance_b'))
        if a is None or b is None:
            continue
        # the plate is the side whose variant has more cells than
        # the other or whose name says baseplate; bins go on plates
        pa = variant_params(named(manager, 'MechPartVariant',
                                  _g(a, 'variant_ref')))
        pb = variant_params(named(manager, 'MechPartVariant',
                                  _g(b, 'variant_ref')))
        if pa.get('grid_role', '') == 'plate' or 'baseplate' in \
                _g(a, 'variant_ref'):
            plate, bin_ = a, b
        else:
            plate, bin_ = b, a
        plates.setdefault(_g(plate, 'name'), {'plate': plate, 'bins': {}})
        plates[_g(plate, 'name')]['bins'][_g(bin_, 'name')] = bin_
        _ = (pa, pb)
    for pname, entry in plates.items():
        plate = entry['plate']
        pp = variant_params(named(manager, 'MechPartVariant',
                                  _g(plate, 'variant_ref')))
        if pp.get('grid_x') is None:
            out.append(_conflict(assembly_name, f'grid:{pname}',
                                 'grid_mismatch',
                                 {'plate': pname, 'why': 'plate variant '
                                  'has no grid_x/grid_y'}, 'warning'))
            continue
        po = _placement_origin(plate)
        bins = []
        for bname, binst in entry['bins'].items():
            bp = variant_params(named(manager, 'MechPartVariant',
                                      _g(binst, 'variant_ref')))
            if bp.get('grid_x') is None:
                continue
            bo = _placement_origin(binst)
            bins.append({'name': bname,
                         'origin': (int(round((bo[0] - po[0]) / GRID_PITCH_MM)),
                                    int(round((bo[1] - po[1]) / GRID_PITCH_MM))),
                         'cells': (int(bp['grid_x']), int(bp['grid_y']))})
        occ = grid_occupancy((int(pp['grid_x']), int(pp['grid_y'])), bins)
        for o in occ['overflow']:
            out.append(_conflict(assembly_name, f'grid:{pname}:{o["bin"]}',
                                 'grid_mismatch',
                                 {'plate': pname, 'plate_cells':
                                  (int(pp['grid_x']), int(pp['grid_y'])),
                                  **o, 'why': 'bin cells overflow the plate'}))
        for o in occ['overlap']:
            out.append(_conflict(assembly_name,
                                 f'grid:{pname}:overlap:{o["cell"]}',
                                 'grid_mismatch',
                                 {'plate': pname, **o,
                                  'why': 'two bins claim one cell'}))
    return out


def check_drawers(assembly, joints, instances, manager):
    """Slider joints on a slide variant with a load rating, loaded
    by the assembly's parameters_json {drawer_load_n, extension_mm,
    slides_per_drawer}."""
    out = []
    a_name = _g(assembly, 'name')
    params = loads(_g(assembly, 'parameters_json', '{}'), {})
    load = params.get('drawer_load_n')
    if load is None:
        return out
    for j in joints:
        if _g(j, 'kind') != 'slider':
            continue
        for side in ('instance_a', 'instance_b'):
            inst = instances.get(_g(j, side))
            vp = variant_params(named(manager, 'MechPartVariant',
                                      _g(inst, 'variant_ref'))) if inst else {}
            rating = vp.get('load_rating')
            if not isinstance(rating, dict):
                continue
            ext = float(params.get('extension_mm',
                                   vp.get('extension_mm', 0)) or 0)
            res = cantilever_tip(float(load), ext, rating,
                                 int(params.get('slides_per_drawer', 2)))
            res.update({'joint': _g(j, 'name'), 'slide': _g(inst, 'name')})
            if res['overload']:
                out.append(_conflict(a_name, f'{_g(j, "name")}:overload',
                                     'slide_overload', res))
            if res['ok'] is False and not res['overload']:
                out.append(_conflict(a_name, f'{_g(j, "name")}:tip',
                                     'cantilever_tip', res))
            break
    return out


def check_assembly(assembly, manager):
    """Run every fit check and the DOF solver over one assembly;
    returns MechConflict dicts (not rows — the API decides whether
    to persist them)."""
    a_name = _g(assembly, 'name')
    instances = {_g(i, 'name'): i for i in rows(manager, 'MechPartInstance')
                 if _g(i, 'assembly_ref') == a_name}
    joints = [j for j in rows(manager, 'MechJoint')
              if _g(j, 'assembly_ref') == a_name]
    out = []
    have_features = bool(rows(manager, 'MechFeature'))
    for j in joints:
        fa = named(manager, 'MechFeature', _g(j, 'feature_a'))
        fb = named(manager, 'MechFeature', _g(j, 'feature_b'))
        for side, f in (('feature_a', fa), ('feature_b', fb)):
            # a NAMED feature that does not resolve is a typo or a
            # catalogue drift — said, as a warning; '' is an honest
            # "no feature on this side" and stays silent
            if _g(j, side) and f is None and have_features:
                out.append(_conflict(a_name, f'{_g(j, "name")}:{side}',
                                     'wrong_pairing',
                                     {'joint': _g(j, 'name'), 'side': side,
                                      'feature': _g(j, side),
                                      'why': 'feature name does not '
                                             'resolve to a MechFeature'},
                                     severity='warning'))
        if fa is not None and fb is not None:
            pair = feature_pairing(fa, fb)
            if pair['ok'] is False:
                out.append(_conflict(a_name, f'{_g(j, "name")}:features',
                                     'wrong_pairing',
                                     {'joint': _g(j, 'name'),
                                      'feature_a': _g(j, 'feature_a'),
                                      'feature_b': _g(j, 'feature_b'),
                                      'why': pair['why']}))
        if _g(j, 'kind') == 'fixed':
            out.extend(check_fastened_joint(j, instances, manager, a_name))
    out.extend(check_grid(a_name, joints, instances, manager))
    out.extend(check_drawers(assembly, joints, instances, manager))
    out.extend(dof_conflicts(solve_dof(assembly, manager)))
    return out
