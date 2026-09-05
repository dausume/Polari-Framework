"""
@module cntfet.cnt_fields

fv-4 (FET_VIEWS_PLAN §1 fv-4, decision 3): the device as REGIONS
along its axis and the spatial fields over them — material,
electrostatic potential (conduction-band edge) U(x), electron
density n(x), n-/p-doping — served as long-form graph rows AND as
FETFieldSample rows the 3-D sim-space binding renders (cnt_scene).

HONESTY (decision 3): every spatial field here is an ANALYTIC
SKETCH from the F1 compact model — the [VS1] eq.(7) scale-length
Laplace profile (kwant_worker.analytic_ec, the same function the
D13 worker seeds its SCF loop with), NOT a solved Poisson/NEGF
field. Every payload says so in `fidelity`. Where a row-backed
F3_NEGF_SCF profile exists for the device (cnt_figures' D13
chart), the potential graph draws it BESIDE the sketch as the
truth; promote when NEGF fields land.

Formulas (all stated on the payloads):
  U(x)   = Ec(x) from analytic_ec(x - x_c, x_edge, lambda,
           c_const = Vt(Vdsi) - Vgsi, Efsd, Vdsi)     [VS1] eq.(5)/(7)
           lead values -Efsd (source) and -Efsd - Vds (drain); the
           channel barrier top falls with Vg (c_const) and the
           drain side drops with Vd.
  n(x)   = min(n_ext, (Qxo/q) exp(-(U(x) - U(x0))/kT))   [1/m]
           Qxo = Cinv n_ss phit ln(1 + exp((Vgsi - (Vt - alpha phit
           Ff))/(n_ss phit)))  ([VS1] eq.(10)) — the virtual-source
           line charge; x0 = the barrier top; n_ext in the
           extensions.
  n_ext  = ∫_{Eg/2}^{∞} D(E) f(E - (Eg/2 + Efsd)) dE   [1/m]
           D(E) = 4/(π ħ v_F) · E/sqrt(E² - (Eg/2)²)
           (cnt_bandstructure.dos_per_j_per_m, 2 spin × 2 valley)
  doping n-type: n_ext in the extensions, 0 in the intrinsic
           channel, None in the metal contacts (refusal); p-type
           mirrors ([VS1] premise ii: symmetric bands).

@consumers cnt_api (/api/cntfet/device/{name}/fields), cnt_scene,
  cnt_characteristics (view names), selftest_fields, polariServer
  (SEED_CNT_FIELD_GRAPHS / SEED_FET_FIELD_BANDS /
  SEED_FET_FIELD_MATERIALS_3D)
"""

import json
import math
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.cnt_bandstructure import dos_per_j_per_m
from cntfet.cnt_constants import KB_J_PER_K, Q_C, lit_value
from cntfet.cnt_derive import resolve_components
from cntfet.cnt_device_viz import _device_graph, device_model
from cntfet.cnt_states import frame_at
from cntfet.cnt_vs_model import _softplus

FIDELITY = ('F1 SKETCH — analytic [VS1] eq.(7) scale-length (Laplace) '
            'profile from the compact model, NOT a solved Poisson/NEGF '
            'field; the D13 F3_NEGF_SCF row-backed profile is drawn '
            'beside it where one exists')

FIELDS = ('material', 'potential', 'electron-density', 'n-doping',
          'p-doping')
SCALAR_FIELDS = ('potential', 'electron-density', 'n-doping')

#: Knobs ([[knobs-and-suggestions]]) — echoed on every payload.
FIELD_KNOBS = {
    # sketch lengths used when a geometry row leaves them at 0
    'l_ext_sketch_nm': 10.0,
    'l_c_default_nm': 20.0,
    # gate-metal shell thickness (sketch; no row carries it)
    'gate_thickness_nm': 3.0,
    'gate_metal': 'W',
    # scene units per nm (a 75 nm device -> 7.5 scene units)
    'scene_scale': 0.1,
    # radial sizes are multiplied by this in the SCENE only so a
    # 1.25 nm tube is visible beside a 75 nm length (stated)
    'radial_exaggeration': 3.0,
    # the Vg series drawn on the 2-D field graphs
    'vg_series_v': (0.0, 0.3, 0.6),
    # 1-D DOS integration for n_ext
    'dos_e_max_ev_above_edge': 1.0,
    'dos_steps': 2000,
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _refuse(error):
    return {'ok': False, 'error': error, 'fidelity': FIDELITY}


# ── regions ────────────────────────────────────────────────────────

def _material_of(kind, rows):
    mat, gate, contact = rows['material'], rows['gate_stack'], rows['contact']
    chir = f'({mat.chirality_n},{mat.chirality_m})'
    return {
        'contact': (getattr(contact, 'metal', 'Pd') or 'Pd',
                    'CNTContact', contact.name),
        'extension': (f'CNT {chir} n+', 'CNTMaterialState', mat.name),
        'channel': (f'CNT {chir}', 'CNTMaterialState', mat.name),
        'oxide': (getattr(gate, 'dielectric_material', 'HfO2') or 'HfO2',
                  'GateStack', gate.name),
        'gate': (FIELD_KNOBS['gate_metal'], 'GateStack', gate.name),
    }[kind]


def device_regions(manager, device, knobs=None):
    """Ordered regions along x (nm, x = 0 at the source-contact
    edge) + the radial layers; each names its material and the
    component ROW it is read from. Returns {ok, regions, radial,
    length_nm, x_channel_center_nm, notes} or a refusal."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    if manager is None or device is None:
        return _refuse('no manager/device — component rows unreachable')
    if not hasattr(device, 'material'):
        return _refuse('device regions are drawn from the CNT component '
                       f'rows; "{getattr(device, "name", "?")}" is not '
                       'an AlignedCNTFETDevice — silicon region sketches '
                       '(bulk / fin / oxide / poly gate) are a sifet '
                       'follow-up')
    rows, missing = resolve_components(manager, device)
    if missing:
        return _refuse(f'missing component rows: {missing}')
    geo, mat, gate = rows['geometry'], rows['material'], rows['gate_stack']
    notes = []
    lc = float(getattr(geo, 'l_c_nm', 0.0) or 0.0)
    if lc <= 0:
        lc = k['l_c_default_nm']
        notes.append(f'l_c_nm is 0 on {geo.name} — contact length is '
                     f'the sketch default {lc:g} nm')
    lext = float(getattr(geo, 'l_ext_nm', 0.0) or 0.0)
    if lext <= 0:
        lext = k['l_ext_sketch_nm']
        notes.append(f'l_ext_nm is 0 on {geo.name} — extension length '
                     f'is the sketch default {lext:g} nm')
    lg = float(geo.lg_nm)
    d = float(getattr(mat, 'diameter_nm', 0.0) or 0.0)
    if d <= 0:
        return _refuse(f'material {mat.name} has no derived diameter — '
                       'derive the device first')
    tox = float(gate.t_ox_nm)
    tg = k['gate_thickness_nm']
    r_tube, r_ox, r_gate = d / 2.0, d / 2.0 + tox, d / 2.0 + tox + tg
    polarity = getattr(device, 'polarity', 'n') or 'n'
    ext_label = 'n+' if polarity == 'n' else 'p+'

    def region(name, kind, x0, x1, r0, r1, doping):
        material, cls, row_name = _material_of(kind, rows)
        if kind == 'extension':
            material = material[:-2] + ext_label
        return {'name': name, 'kind': kind, 'material': material,
                'x0': x0, 'x1': x1, 'r0': r0, 'r1': r1,
                'doping': doping,
                'componentRow': {'className': cls, 'name': row_name}}

    x = 0.0
    regions = []
    for name, kind, length, doping in (
            ('source contact', 'contact', lc, 'metal'),
            ('source extension', 'extension', lext, polarity),
            ('channel', 'channel', lg, 'intrinsic'),
            ('drain extension', 'extension', lext, polarity),
            ('drain contact', 'contact', lc, 'metal')):
        regions.append(region(name, kind, x, x + length, 0.0, r_tube,
                              doping))
        x += length
    for i, r in enumerate(regions):
        r['index'] = i
    x_ch0, x_ch1 = regions[2]['x0'], regions[2]['x1']
    radial = [
        region('tube', 'channel', regions[1]['x0'], regions[3]['x1'],
               0.0, r_tube, 'see regions'),
        region('oxide shell', 'oxide', regions[1]['x0'],
               regions[3]['x1'], r_tube, r_ox, 'dielectric'),
        region('gate metal shell', 'gate', x_ch0, x_ch1, r_ox, r_gate,
               'metal'),
    ]
    for i, r in enumerate(radial):
        r['index'] = i
    return {'ok': True, 'device': device.name, 'regions': regions,
            'radial': radial, 'length_nm': x,
            'x_channel_center_nm': 0.5 * (x_ch0 + x_ch1),
            'diameter_nm': d, 't_ox_nm': tox, 'polarity': polarity,
            'notes': notes, 'knobs': k, 'fidelity': FIDELITY}


def region_at(regions, x):
    for r in regions:
        if r['x0'] <= x < r['x1']:
            return r
    return regions[-1] if x >= regions[-1]['x1'] else regions[0]


# ── physics helpers ────────────────────────────────────────────────

def qxo_c_per_m(p, frame):
    """[VS1] eq.(10) virtual-source line charge at the frame's
    internal biases (the same expression vs_channel_current uses)."""
    phit = p['phit_v']
    return (p['cinv_f_per_m'] * p['n_ss'] * phit
            * _softplus((frame['vgsi'] - (frame['vt'] - p['alpha'] * phit
                                          * frame['ff']))
                        / (p['n_ss'] * phit)))


def n_ext_per_m(eg_ev, efsd_ev, temperature_k, knobs=None):
    """Extension carrier density from Efsd through the CNT 1-D DOS:
    n_ext = ∫_{Δ}^{∞} D(E) f(E - (Δ + Efsd)) dE, Δ = Eg/2, D(E) =
    4/(π ħ v_F) E/sqrt(E² - Δ²) (cnt_bandstructure.dos_per_j_per_m).
    Midpoint rule from the edge (integrable 1/sqrt singularity —
    the midpoints never sit on it)."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    kt = KB_J_PER_K * temperature_k
    delta = eg_ev * Q_C / 2.0
    ef = delta + efsd_ev * Q_C
    e_max = delta + k['dos_e_max_ev_above_edge'] * Q_C
    n_steps = int(k['dos_steps'])
    de = (e_max - delta) / n_steps
    total = 0.0
    for i in range(n_steps):
        e = delta + (i + 0.5) * de
        xarg = (e - ef) / kt
        occ = 1.0 / (1.0 + math.exp(xarg)) if xarg < 500 else 0.0
        total += dos_per_j_per_m(e, eg_ev) * occ * de
    return total


def _analytic_ec(xs, x_edge, lam, c_const, efsd, vd):
    from cntfet.kwant_worker import analytic_ec
    return [float(v) for v in analytic_ec(xs, x_edge, lam, c_const,
                                          efsd, vd)]


def _x_grid(length, n):
    n = max(int(n), 2)
    return [length * i / (n - 1) for i in range(n)]


# ── the fields ─────────────────────────────────────────────────────

def _potential(p, geo_report, frame, transport, gate, xs):
    """U(x) [eV] = Ec(x): the eq.(5) Laplace profile with the
    barrier constant set by the FRAME (Vt(Vdsi) incl. DIBL + roll-
    off, Vgsi after the Rc drop) — so the barrier top falls as Vg
    rises and the drain lead sits Vds lower."""
    xc = geo_report['x_channel_center_nm']
    lg = geo_report['regions'][2]['x1'] - geo_report['regions'][2]['x0']
    x_edge = lg / 2.0 + lit_value('lof_over_tox') * float(gate.t_ox_nm)
    lam = float(getattr(transport, 'lambda_nm', 0.0) or p['lambda_nm'])
    c_const = frame['vt'] - frame['vgsi']
    efsd = float(transport.efsd_ev)
    return _analytic_ec([x - xc for x in xs], x_edge, lam, c_const,
                        efsd, frame['vdsi']), {
        'x_edge_nm': x_edge, 'lambda_nm': lam, 'c_const_ev': c_const,
        'efsd_ev': efsd,
        'formula': 'U(x) = analytic_ec(x - x_c, x_edge = Lg/2 + Lof, '
                   'lambda [VS1] eq.(7), c = Vt(Vdsi) - Vgsi, Efsd, '
                   'Vdsi); leads: -Efsd | -Efsd - Vds'}


def field_profile(manager, device, field, vg=None, vd=None, n=60,
                  knobs=None):
    """{ok, device, field, vg, vd, fidelity, x_nm[], value[], unit,
    regions, note, formula, frame, knobs} — one field along x at one
    bias. `device` is a row or a name. Refusals name the affordance."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    name = device if isinstance(device, str) else getattr(device, 'name', '')
    id_fn, p, dev, refusal = device_model(manager, name)
    if refusal is not None:
        return {**refusal, 'fidelity': FIDELITY}
    if dev is not None and not hasattr(dev, 'material'):
        # fg-4: a SiliconMOSFET row has its OWN field sketch now
        # (sifet.si_fields — same eq.(5) barrier, silicon λ); one
        # dispatch point so /fields and the parts2d overlays
        # un-refuse together. Absent module → the old refusal.
        try:
            from sifet.si_fields import field_profile_si
        except ImportError:
            pass
        else:
            return field_profile_si(manager, dev, field,
                                    vg=vg, vd=vd, n=n, knobs=knobs)
    # CNT legacy defaults (bit-identical to the fv-4 behavior);
    # the Si path above defaults to the device's OWN Vdd instead.
    vg = 0.0 if vg is None else vg
    vd = 0.6 if vd is None else vd
    if field not in FIELDS:
        return _refuse(f'unknown field "{field}" ({" | ".join(FIELDS)})')
    geo_report = device_regions(manager, dev, knobs=k)
    if not geo_report.get('ok'):
        return geo_report
    rows, _missing = resolve_components(manager, dev)
    regions = geo_report['regions']
    xs = _x_grid(geo_report['length_nm'], n)
    polarity = geo_report['polarity']
    out = {'ok': True, 'device': dev.name, 'field': field, 'vg': vg,
           'vd': vd, 'fidelity': FIDELITY, 'x_nm': xs,
           'regions': regions, 'radial': geo_report['radial'],
           'polarity': polarity, 'knobs': k,
           'note': ('F1 SKETCH: analytic profile from the compact '
                    'model, not a solved field; '
                    + '; '.join(geo_report['notes']))}
    if field == 'material':
        out['value'] = [region_at(regions, x)['index'] for x in xs]
        out['material'] = [region_at(regions, x)['material'] for x in xs]
        out['unit'] = 'region index'
        out['formula'] = 'region lookup along x (row-backed materials)'
        return out
    frame = frame_at(p, vg, vd)
    out['frame'] = {key: frame[key] for key in
                    ('vgsi', 'vdsi', 'vt', 'ff', 'fsat', 'vdsat', 'id_a')}
    mat, transport, gate = rows['material'], rows['transport'], rows['gate_stack']
    n_ext = n_ext_per_m(float(mat.eg_ev), float(transport.efsd_ev),
                        float(dev.temperature_k), knobs=k)
    out['n_ext_per_m'] = n_ext
    out['n_ext_formula'] = ('n_ext = ∫_{Eg/2}^∞ D(E) f(E - (Eg/2 + Efsd)) '
                            'dE, D(E) = 4/(π ħ v_F) E/sqrt(E² - (Eg/2)²)')
    if field == 'potential':
        u, meta = _potential(p, geo_report, frame, transport, gate, xs)
        out['value'] = u
        out['unit'] = 'eV'
        out.update(meta)
        ch = regions[2]
        in_ch = [v for x, v in zip(xs, u) if ch['x0'] <= x <= ch['x1']]
        out['barrier_top_ev'] = max(in_ch) if in_ch else None
        out['barrier_height_ev'] = ((max(in_ch) - u[0]) if in_ch
                                    else None)
        out['source_lead_ev'] = u[0]
        out['drain_lead_ev'] = u[-1]
        return out
    if field == 'electron-density':
        u, meta = _potential(p, geo_report, frame, transport, gate, xs)
        kt_ev = KB_J_PER_K * float(dev.temperature_k) / Q_C
        q_line = qxo_c_per_m(p, frame) / Q_C
        ch = regions[2]
        u0 = max(v for x, v in zip(xs, u) if ch['x0'] <= x <= ch['x1'])
        vals = []
        for x, uu in zip(xs, u):
            kind = region_at(regions, x)['kind']
            if kind == 'contact':
                vals.append(None)
            elif kind == 'extension':
                vals.append(n_ext)
            else:
                vals.append(min(n_ext, q_line * math.exp(-(uu - u0) / kt_ev)))
        out['value'] = vals
        out['unit'] = '1/m'
        out['qxo_per_m'] = q_line
        out['formula'] = ('n(x) = min(n_ext, (Qxo/q) exp(-(U(x) - U(x0))/kT)); '
                          'x0 = barrier top; contacts: None (metal)')
        out['potential_meta'] = meta
        return out
    # doping
    mirror = (field == 'n-doping') == (polarity == 'n')
    vals, refusals = [], set()
    for x in xs:
        kind = region_at(regions, x)['kind']
        if kind == 'contact':
            vals.append(None)
            refusals.add('metal — no doping')
        elif kind == 'extension':
            vals.append(n_ext if mirror else 0.0)
        else:
            vals.append(0.0)
    out['value'] = vals
    out['unit'] = '1/m'
    out['refusals'] = sorted(refusals)
    out['formula'] = (f'{field}: extensions = n_ext ({polarity}-type '
                      f'device{" — mirrored" if polarity == "p" else ""}), '
                      'channel intrinsic = 0, contacts refused (metal)'
                      if mirror else
                      f'{field} = 0 everywhere on a {polarity}-type device '
                      '(contacts refused: metal)')
    return out


# ── long-form rows ─────────────────────────────────────────────────

def region_band_rows(regions, y_lo, y_hi):
    """Shaded region bands (one band series per region, label =
    material) + boundary guides."""
    rows = []
    for r in regions:
        label = f"{r['name']}: {r['material']}"
        for x in (r['x0'], r['x1']):
            rows.append({'series': label, 'style': 'band', 'dash': False,
                         'x': x, 'lo': y_lo, 'hi': y_hi, 'label': label})
    for r in regions[1:]:
        rows.append({'series': 'region boundary', 'style': 'guide',
                     'dash': True, 'x': r['x0'],
                     'label': f"{r['name']} starts"})
    return rows


def field_rows(profile, include_regions=True, y_range=None):
    """Long-form rows for one profile: potential/density/doping as a
    line series labelled by Vg (None values skipped); material as
    one dot series per material at y = region index; plus region
    bands + guides when include_regions."""
    if not profile.get('ok'):
        return []
    rows = []
    xs, vals = profile['x_nm'], profile['value']
    if profile['field'] == 'material':
        for x, v, m in zip(xs, vals, profile['material']):
            rows.append({'series': m, 'style': 'dot', 'dash': False,
                         'x': x, 'y': v, 'label': m})
    else:
        label = f"Vg = {profile['vg']:g} V, Vd = {profile['vd']:g} V"
        for x, v in zip(xs, vals):
            if v is None:
                continue
            rows.append({'series': label, 'style': 'line', 'dash': False,
                         'x': x, 'y': v})
    if include_regions:
        ys = [r['y'] for r in rows if r.get('y') is not None]
        if y_range is None:
            lo, hi = (min(ys), max(ys)) if ys else (0.0, 1.0)
            if profile.get('unit') == '1/m':
                lo = max(lo, 1.0)
                hi = max(hi, lo * 10.0)
            elif hi <= lo:
                hi = lo + 1.0
            y_range = (lo, hi)
        rows.extend(region_band_rows(profile['regions'], *y_range))
    return rows


def _scf_profile_rows(manager, device_name, x_center):
    """The D13 row-backed SCF profile(s) for THIS device — the truth
    beside the sketch (up to 2 bias points), x shifted from the
    worker's centred grid onto the region axis."""
    tables = getattr(manager, 'objectTables', None) or {}
    best, best_time = None, ''
    for row in (tables.get('CNTFETSimResult') or {}).values():
        if (getattr(row, 'physics_fidelity', '') == 'F3_NEGF_SCF'
                and getattr(row, 'device', '') == device_name
                and getattr(row, 'ran_at', '') > best_time):
            best, best_time = row, row.ran_at
    if best is None:
        return []
    try:
        profiles = json.loads(best.metrics_json or '{}').get('profiles') or []
    except (ValueError, TypeError):
        return []
    rows = []
    for prof in profiles[:2]:
        label = (f"SCF Vg = {prof['vg_v']:g} V, Vd = {prof['vd_v']:g} V "
                 f"(D13 row {best.name})")
        for x, e in zip(prof['x_nm'], prof['ec_ev']):
            rows.append({'series': label, 'style': 'line', 'dash': True,
                         'x': x + x_center, 'y': e})
    return rows


def _scalar_curve(field, log_floor=None):
    def build(id_fn, p, device, manager, knobs=None):
        k = {**FIELD_KNOBS, **(knobs or {})}
        from cntfet.cnt_device_viz import device_vdd
        vdd = device_vdd(device)
        # device-relative rule (fg-4): sweep 0 → the device's OWN
        # Vdd unless the caller pinned an explicit series. For the
        # S1 0.6 V window the fractions give exactly the old
        # (0, 0.3, 0.6) series — CNT graphs bit-identical; a 1.0 V
        # silicon device now sweeps (0, 0.5, 1.0) instead of being
        # drawn at CNT voltages.
        vd = k.get('vd', vdd)
        vg_series = ((knobs or {}).get('vg_series_v')
                     or [round(f * vdd, 4) for f in (0.0, 0.5, 1.0)])
        rows, profiles = [], []
        for vg in vg_series:
            prof = field_profile(manager, device, field, vg=vg, vd=vd,
                                 n=k.get('n', 60), knobs=k)
            if not prof.get('ok'):
                return None, prof   # refusal, not an empty chart
            profiles.append(prof)
            rows.extend(field_rows(prof, include_regions=False))
        if field == 'potential':
            ch = profiles[0]['regions'][2]
            rows.extend(_scf_profile_rows(
                manager, device.name, 0.5 * (ch['x0'] + ch['x1'])))
        ys = [r['y'] for r in rows if r.get('y') is not None]
        if log_floor is not None:
            ys = [y for y in ys if y > 0] or [log_floor]
            lo, hi = max(min(ys), log_floor), max(max(ys), log_floor * 10)
        else:
            lo, hi = (min(ys), max(ys)) if ys else (0.0, 1.0)
            if hi <= lo:
                hi = lo + 1.0
        rows.extend(region_band_rows(profiles[0]['regions'], lo, hi))
        return rows
    return build


def _material_curve(id_fn, p, device, manager, knobs=None):
    prof = field_profile(manager, device, 'material', knobs=knobs)
    return field_rows(prof, include_regions=True,
                      y_range=(-0.5, len(prof['regions']) - 0.5)
                      if prof.get('ok') else (None, prof))


def _doping_curve(id_fn, p, device, manager, knobs=None):
    """Both dopings on one graph (n- and p-doping series)."""
    rows = []
    prof_n = field_profile(manager, device, 'n-doping', knobs=knobs)
    prof_p = field_profile(manager, device, 'p-doping', knobs=knobs)
    for prof, label in ((prof_n, 'n-doping'), (prof_p, 'p-doping')):
        if not prof.get('ok'):
            return rows
        for x, v in zip(prof['x_nm'], prof['value']):
            if v is None:
                continue
            rows.append({'series': label, 'style': 'line', 'dash': False,
                         'x': x, 'y': v})
    ys = [r['y'] for r in rows]
    hi = max(ys) if ys else 1.0
    rows.extend(region_band_rows(prof_n['regions'], 0.0, hi or 1.0))
    return rows


CURVE_BUILDERS = {
    'field-material': _material_curve,
    'field-potential': _scalar_curve('potential'),
    'field-density': _scalar_curve('electron-density', log_floor=1.0),
    'field-doping': _doping_curve,
}


def _field_graph(kind, description, x_label, y_label, y_type='linear'):
    g = _device_graph(kind, description, x_label, y_label, y_type=y_type)
    g['description'] = (description + ' — F1 SKETCH; data: /api/cntfet/'
                        'device/{name}/points?curve=' + kind)
    return g


SEED_CNT_FIELD_GRAPHS = [
    _field_graph('field-material',
                 'Material composition along the device axis: one dot '
                 'series per row-backed material at y = region index, '
                 'regions shaded', 'x (nm)', 'region'),
    _field_graph('field-potential',
                 'Conduction-band edge U(x) at Vd for Vg = 0/0.3/0.6 V: '
                 'the source barrier collapses as Vg rises, the drain '
                 'lead sits Vds lower; dashed = D13 SCF row-backed '
                 'profile where one exists', 'x (nm)', 'Ec (eV)'),
    _field_graph('field-density',
                 'Electron line density n(x) (semi-classical from Qxo and '
                 'U(x); n_ext in the extensions)', 'x (nm)', 'n (1/m)',
                 y_type='log'),
    _field_graph('field-doping',
                 'n- and p-doping along the axis: n_ext from Efsd through '
                 'the 1-D DOS in the extensions, 0 in the intrinsic '
                 'channel, metal contacts refused', 'x (nm)',
                 'doping (1/m)'),
]


# ── rows for the 3-D scene ─────────────────────────────────────────

class FETFieldSample(treeObject):
    """One cell of a field sample along the tube axis — the row the
    `FETFieldSample-3d` binding renders as a banded cube; vg_v is
    the scrubber's 'instant'. simulation_run_ref =
    'fet-fields:{device}:{field}' is the scene's row filter
    (?run=)."""

    @treeObjectInit
    def __init__(self, name='', device='', field='', vg_v=0.0,
                 vd_v=0.0, x_nm=0.0, pos_x=0.0, pos_y=0.0, pos_z=0.0,
                 cell_nm=0.0, cell_scene=0.0, value=0.0, band=-1,
                 band_label='', band_style='fet-band-none',
                 material='', simulation_run_ref='', fidelity=FIDELITY,
                 generated_at='', manager=None):
        self.name = name
        self.device = device
        self.field = field
        self.vg_v = vg_v
        self.vd_v = vd_v
        self.x_nm = x_nm
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.cell_nm = cell_nm
        self.cell_scene = cell_scene
        self.value = value
        self.band = band
        self.band_label = band_label
        self.band_style = band_style
        self.material = material
        self.simulation_run_ref = simulation_run_ref
        self.fidelity = fidelity
        self.generated_at = generated_at


class FETFieldBand(treeObject):
    """One value band of a scalar field (colour is DISCRETE in the
    scene — mag-fv FieldThresholdBand precedent): [min, max) in the
    field's unit, its colour/label and the Material3DDefinition it
    wears. Editable data, not code."""

    @treeObjectInit
    def __init__(self, name='', field='', order=0, min_value=0.0,
                 max_value=0.0, unit='', color='#888888', label='',
                 style_ref='', notes='', manager=None):
        self.name = name
        self.field = field
        self.order = order
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.color = color
        self.label = label
        self.style_ref = style_ref
        self.notes = notes


def _band(field, order, lo, hi, unit, color, label):
    return {'name': f'fet-band-{field}-{order}', 'field': field,
            'order': order, 'min_value': lo, 'max_value': hi,
            'unit': unit, 'color': color, 'label': label,
            'style_ref': f'fet-band-{field}-{order}',
            'notes': 'fv-4 default band (knob)'}


_INF = float('inf')
SEED_FET_FIELD_BANDS = [
    # potential (Ec, eV): from the drain lead (-Efsd - Vdd ~ -0.7) up
    # to a tall off-state barrier (~ +0.4)
    _band('potential', 0, -_INF, -0.5, 'eV', '#0d47a1', 'Ec < -0.5 eV'),
    _band('potential', 1, -0.5, -0.3, 'eV', '#1976d2', '-0.5..-0.3 eV'),
    _band('potential', 2, -0.3, -0.1, 'eV', '#4fc3f7', '-0.3..-0.1 eV'),
    _band('potential', 3, -0.1, 0.05, 'eV', '#ffe082', '-0.1..0.05 eV'),
    _band('potential', 4, 0.05, 0.2, 'eV', '#ff8f00', '0.05..0.2 eV'),
    _band('potential', 5, 0.2, _INF, 'eV', '#c62828', 'Ec > 0.2 eV'),
    # electron density (1/m), log-spaced decades
    _band('electron-density', 0, 0.0, 1e5, '1/m', '#eceff1', 'n < 1e5'),
    _band('electron-density', 1, 1e5, 1e6, '1/m', '#b3e5fc', '1e5..1e6'),
    _band('electron-density', 2, 1e6, 1e7, '1/m', '#4fc3f7', '1e6..1e7'),
    _band('electron-density', 3, 1e7, 1e8, '1/m', '#0288d1', '1e7..1e8'),
    _band('electron-density', 4, 1e8, 1e9, '1/m', '#01579b', '1e8..1e9'),
    _band('electron-density', 5, 1e9, _INF, '1/m', '#1a237e', 'n > 1e9'),
    # doping (1/m)
    _band('n-doping', 0, 0.0, 1.0, '1/m', '#eceff1', 'intrinsic'),
    _band('n-doping', 1, 1.0, 1e8, '1/m', '#a5d6a7', 'n < 1e8'),
    _band('n-doping', 2, 1e8, 1e9, '1/m', '#43a047', 'n 1e8..1e9'),
    _band('n-doping', 3, 1e9, _INF, '1/m', '#1b5e20', 'n > 1e9'),
    _band('p-doping', 0, 0.0, 1.0, '1/m', '#eceff1', 'intrinsic'),
    _band('p-doping', 1, 1.0, 1e8, '1/m', '#f8bbd0', 'p < 1e8'),
    _band('p-doping', 2, 1e8, 1e9, '1/m', '#e91e63', 'p 1e8..1e9'),
    _band('p-doping', 3, 1e9, _INF, '1/m', '#880e4f', 'p > 1e9'),
]


def _mat(name, color, description, opacity=1.0):
    return {'name': name, 'description': description,
            'material_type': 'standard', 'color': color,
            'emissive': '#000000', 'emissive_intensity': 0.0,
            'metalness': 0.1, 'roughness': 0.7, 'opacity': opacity,
            'transparent': opacity < 1.0, 'double_sided': False,
            'flat_shading': False, 'wireframe': False}


SEED_FET_FIELD_MATERIALS_3D = [
    _mat(b['style_ref'], b['color'],
         f"fv-4 field band: {b['field']} {b['label']}")
    for b in SEED_FET_FIELD_BANDS
] + [
    _mat('fet-band-none', '#9e9e9e',
         'fv-4: no band (metal contact / refused value)', opacity=0.25),
    _mat('fet-pd-contact', '#b0bec5', 'Pd source/drain contact (metal)'),
    _mat('fet-cnt-channel', '#212121', 'Intrinsic CNT channel (tube)',
         opacity=0.35),
    _mat('fet-cnt-extension-n', '#2e7d32', 'n+ doped CNT extension',
         opacity=0.35),
    _mat('fet-cnt-extension-p', '#ad1457', 'p+ doped CNT extension',
         opacity=0.35),
    _mat('fet-hfo2-oxide', '#80deea', 'HfO2 gate-all-around oxide shell',
         opacity=0.15),
    _mat('fet-gate-metal', '#ffb300', 'Gate metal shell (W prior)',
         opacity=0.45),
    # fg-6: silicon region materials (sifet.si_scene box stacks)
    _mat('fet-si-body', '#546e7a', 'Silicon body / substrate',
         opacity=0.30),
    _mat('fet-si-sd-n', '#2e7d32', 'n+ source/drain junction',
         opacity=0.45),
    _mat('fet-si-sd-p', '#ad1457', 'p+ source/drain junction',
         opacity=0.45),
    _mat('fet-si-channel', '#263238', 'Gated silicon channel',
         opacity=0.40),
    _mat('fet-sio2-oxide', '#b3e5fc', 'Gate dielectric (thermal '
         'SiO2 / sol-gel)', opacity=0.20),
]

SEEDED_STYLE_NAMES = [m['name'] for m in SEED_FET_FIELD_MATERIALS_3D]


def band_for(field, value, bands=None):
    """(band dict | None) for a value — None for a refused value."""
    if value is None:
        return None
    for b in (bands or SEED_FET_FIELD_BANDS):
        if b['field'] == field and b['min_value'] <= value < b['max_value']:
            return b
    return None


def run_ref(device_name, field):
    """The scene row filter (?run=) for one device × field."""
    return f'fet-fields:{device_name}:{field}'


def _drop_old_samples(manager, device_name):
    tables = getattr(manager, 'objectTables', None) or {}
    table = tables.get('FETFieldSample')
    if not isinstance(table, dict):
        return 0
    prefix = f'{device_name}-field-'
    doomed = [key for key, row in table.items()
              if str(getattr(row, 'name', '')).startswith(prefix)]
    db = getattr(manager, 'db', None)
    for key in doomed:
        row = table.pop(key, None)
        if db is not None and row is not None:
            try:
                db.deleteInstanceInDB(row)
            except Exception:
                pass
    return len(doomed)


def sample_fields(manager, device, vg_list=None,
                  vd=None, n_cells=40, row_factory=None, knobs=None,
                  bands=None):
    """Generate FETFieldSample rows for the 3 scalar fields along the
    channel axis (pos_x centred, scene units; one cube per cell), band
    them, replace older samples of the device, persist when a db
    exists. Returns {ok, rows, perField, vgSteps, replaced, ...}.

    Device-relative (fg-6): vg_list defaults to 7 steps 0 → the
    device's OWN Vdd (for the S1 0.6 V window that is exactly the old
    (0, 0.1, …, 0.6) list — CNT bit-identical) and vd defaults to its
    Vdd; a SILICON device is banded with sifet.si_fields.
    SI_FIELD_BANDS (areal cm^-2 / cm^-3 ranges — the CNT per-tube 1/m
    bands would put every silicon value in the top band)."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    name = device if isinstance(device, str) else getattr(device, 'name', '')
    _id_fn, _p, dev, refusal = device_model(manager, name)
    if refusal is not None:
        return {**refusal, 'fidelity': FIDELITY}
    from cntfet.cnt_device_viz import device_vdd
    vdd = device_vdd(dev)
    if vd is None:
        vd = vdd
    if vg_list is None:
        vg_list = tuple(round(vdd * i / 6.0, 4) for i in range(7))
    if bands is None and not hasattr(dev, 'material'):
        try:
            from sifet.si_fields import SI_FIELD_BANDS
            bands = SI_FIELD_BANDS
        except ImportError:
            pass
    if row_factory is None:
        row_factory = FETFieldSample
    tables = getattr(manager, 'objectTables', None)
    if isinstance(tables, dict) and 'FETFieldSample' not in tables:
        tables['FETFieldSample'] = {}
    replaced = _drop_old_samples(manager, dev.name)
    db = getattr(manager, 'db', None)
    stamp = _now()
    scale = k['scene_scale']
    per_field, total = {}, 0
    for field in SCALAR_FIELDS:
        count = 0
        for vg in vg_list:
            prof = field_profile(manager, dev, field, vg=vg, vd=vd,
                                 n=n_cells, knobs=k)
            if not prof.get('ok'):
                return prof
            length = prof['regions'][-1]['x1']
            dx = length / max(n_cells - 1, 1)
            for i, (x, v) in enumerate(zip(prof['x_nm'], prof['value'])):
                band = band_for(field, v, bands)
                region = region_at(prof['regions'], x)
                fields = dict(
                    name=f'{dev.name}-field-{field}-vg{vg:g}-{i:03d}',
                    device=dev.name, field=field, vg_v=float(vg),
                    vd_v=float(vd), x_nm=float(x),
                    pos_x=(x - length / 2.0) * scale, pos_y=0.0,
                    pos_z=0.0, cell_nm=dx, cell_scene=dx * scale,
                    value=v if v is not None else 0.0,
                    band=band['order'] if band else -1,
                    band_label=band['label'] if band
                    else ('metal — refused' if v is None else 'out of bands'),
                    band_style=band['style_ref'] if band else 'fet-band-none',
                    material=region['material'],
                    simulation_run_ref=run_ref(dev.name, field),
                    fidelity=FIDELITY, generated_at=stamp)
                row = row_factory(manager=manager, **fields)
                if isinstance(tables, dict) and row_factory is FETFieldSample:
                    tables['FETFieldSample'][id(row)] = row
                try:
                    if db is not None:
                        db.saveInstanceInDB(row)
                except Exception:
                    pass
                count += 1
        per_field[field] = count
        total += count
    return {'ok': True, 'device': dev.name, 'rows': total,
            'perField': per_field, 'vgSteps': list(vg_list), 'vd': vd,
            'nCells': n_cells, 'replaced': replaced,
            'runRefs': {f: run_ref(dev.name, f) for f in SCALAR_FIELDS},
            'fidelity': FIDELITY, 'knobs': k, 'generatedAt': stamp}
