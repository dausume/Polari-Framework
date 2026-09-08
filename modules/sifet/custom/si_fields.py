"""
@module sifet.custom.si_fields

fg-4 (last item): the SILICON field basis — un-refuses
GET /api/fet/device/{si}/fields and the parts2d overlays
(cnt_fields.field_profile dispatches Si rows here).

Same fidelity grade as the CNT basis and it says so: an F1 SKETCH,
not a solved field. The potential REUSES the very same analytic
eq.(5) barrier profile (cnt_fields._analytic_ec) with the SILICON
device's own scale length λ — which si_model derives from the
seeded shape rows' cited scale-length formulas ([YAN92]/[AP97]/
[SIL96], the same λ that sets DIBL/roll-off in the derive chain) —
and the frame (Vt(Vds), Vgsi after the Rc drop) from cnt_states.
Electron density is the [SZE07] charge-sheet form along that
barrier; doping fields read the ROWS verbatim.

Stated gaps (never silently filled): the S/D degeneracy offset
(source lead is the energy reference, Efsd = 0), vertical (depth)
structure — the profile is along the channel at the surface — and
interface traps.

@consumers
  - cntfet.cnt_fields_basis.field_profile (Si dispatch)
  - cnt_api GET /api/fet/device/{name}/fields (via the dispatch)
  - cntfet.custom.cnt_parts_svg (the 2-D overlay)
  - sifet.si_fields_selftest
"""

import math

from cntfet.cnt_states_basis import frame_at
from sifet.custom.si_device import get_row, resolve_components, si_device_model
from sifet.custom.si_model import KB_J_PER_K, Q_C, lit, thermal_voltage_v

FIELDS = ('material', 'potential', 'electron-density', 'n-doping',
          'p-doping')

FIDELITY = ('F1 SKETCH (charge-sheet + the analytic eq.(5) barrier '
            'with the silicon shape row\'s own cited scale length '
            '[YAN92]/[AP97]/[SIL96]): a sketch along the channel '
            'surface, not a solved field; S/D degeneracy offset and '
            'depth structure are named gaps')

#: sketch lengths shared with the 2-D parts view so overlays align
from cntfet.custom.cnt_parts_svg import PARTS2D_KNOBS  # noqa: E402


def _refuse(error):
    return {'ok': False, 'error': error, 'fidelity': FIDELITY}


def device_regions_si(device, knobs=None):
    """Axial regions along the channel (x = 0 at the source-contact
    edge), the parts2d lengths so the overlay aligns with the 2-D
    view: contact | S/D | channel | S/D | contact."""
    k = {**PARTS2D_KNOBS, **(knobs or {})}
    lc, lsd = k['si_contact_length_nm'], k['si_sd_length_nm']
    lg = float(device.lg_nm)
    pol = getattr(device, 'polarity', 'n') or 'n'
    sd_label = 'n+' if pol == 'n' else 'p+'
    x, regions = 0.0, []
    for i, (name, kind, length, material) in enumerate((
            ('source contact', 'contact', lc, 'silicide / metal'),
            ('source S/D', 'extension', lsd - lc,
             f'silicon {sd_label}'),
            ('channel', 'channel', lg, 'silicon (gated)'),
            ('drain S/D', 'extension', lsd - lc,
             f'silicon {sd_label}'),
            ('drain contact', 'contact', lc, 'silicide / metal'))):
        regions.append({'name': name, 'kind': kind, 'index': i,
                        'material': material,
                        'x0': round(x, 3), 'x1': round(x + length, 3)})
        x += length
    return {'ok': True, 'regions': regions, 'length_nm': round(x, 3),
            'x_channel_center_nm': lc + (lsd - lc) + lg / 2.0,
            'notes': [f'contact ({lc:g} nm) and S/D ({lsd - lc:g} nm) '
                      'lengths are the parts2d SKETCH knobs — no row '
                      'carries them; the channel is the row\'s '
                      f'lg_nm = {lg:g} nm']}


def _region_at(regions, x):
    for r in regions:
        if r['x0'] <= x < r['x1']:
            return r
    return regions[-1] if x >= regions[-1]['x1'] else regions[0]


def _potential_si(p, geo, frame, xs):
    """U(x) [eV]: the same eq.(5) analytic barrier, silicon λ.
    Source lead = 0 reference (Efsd offset is a named gap)."""
    from cntfet.cnt_fields_basis import _analytic_ec
    xc = geo['x_channel_center_nm']
    ch = next(r for r in geo['regions'] if r['kind'] == 'channel')
    lg = ch['x1'] - ch['x0']
    lam = float(p['lambda_nm'])
    c_const = frame['vt'] - frame['vgsi']
    u = _analytic_ec([x - xc for x in xs], lg / 2.0, lam, c_const,
                     0.0, frame['vdsi'])
    meta = {'lambda_nm': lam, 'c_const_ev': c_const,
            'formula': ('U(x) = analytic_ec(x - x_c, x_edge = Lg/2, '
                        'λ = the shape row\'s scale length, c = '
                        'Vt(Vdsi) − Vgsi, Efsd = 0 (named gap), '
                        'Vdsi) — the same eq.(5) profile the CNT '
                        'sketch uses, silicon λ')}
    return u, meta


def field_profile_si(manager, device, field, vg=None, vd=None, n=60,
                     knobs=None):
    """The cnt_fields.field_profile contract for a SiliconMOSFET
    row; vg/vd default to the device's OWN Vdd."""
    name = getattr(device, 'name', str(device))
    _id_fn, p, dev, refusal = si_device_model(manager, name)
    if refusal is not None:
        return {**refusal, 'fidelity': FIDELITY}
    if field not in FIELDS:
        return _refuse(f'unknown field "{field}" '
                       f'({" | ".join(FIELDS)})')
    vdd = float(getattr(dev, 'vdd_v', 1.0) or 1.0)
    vg = vdd if vg is None else vg
    vd = vdd if vd is None else vd
    rows, missing = resolve_components(manager, dev)
    if missing:
        return _refuse(f'missing component rows: {missing}')
    geo = device_regions_si(dev, knobs)
    regions = geo['regions']
    n = max(int(n), 2)
    xs = [geo['length_nm'] * i / (n - 1) for i in range(n)]
    pol = getattr(dev, 'polarity', 'n') or 'n'
    out = {'ok': True, 'device': dev.name, 'field': field, 'vg': vg,
           'vd': vd, 'fidelity': FIDELITY, 'x_nm': xs,
           'regions': regions, 'radial': [], 'polarity': pol,
           'knobs': {**PARTS2D_KNOBS, **(knobs or {})},
           'note': ('F1 SKETCH: analytic profile from the compact '
                    'model, not a solved field; '
                    + '; '.join(geo['notes']))}
    if field == 'material':
        out['value'] = [_region_at(regions, x)['index'] for x in xs]
        out['material'] = [_region_at(regions, x)['material']
                           for x in xs]
        out['unit'] = 'region index'
        out['formula'] = 'region lookup along x (row-backed rows)'
        return out
    ch_row, sd_row = rows['channel_doping'], rows['sd_doping']
    if field in ('n-doping', 'p-doping'):
        vals, refusals = [], set()
        want = field[0]                      # 'n' | 'p'
        n_sd = float(getattr(sd_row, 'concentration_cm3', 0.0) or 0.0)
        n_ch = float(getattr(ch_row, 'concentration_cm3', 0.0) or 0.0)
        sd_type = getattr(sd_row, 'dopant_type', '')
        ch_type = getattr(ch_row, 'dopant_type', '')
        for x in xs:
            kind = _region_at(regions, x)['kind']
            if kind == 'contact':
                vals.append(None)
                refusals.add('metal — no doping')
            elif kind == 'extension':
                vals.append(n_sd if sd_type == want else 0.0)
            else:
                vals.append(n_ch if ch_type == want else 0.0)
        out['value'] = vals
        out['unit'] = 'cm^-3'
        out['refusals'] = sorted(refusals)
        out['formula'] = (f'{field}: the DOPING ROWS verbatim — S/D '
                          f'{sd_type}+ {n_sd:.3g} cm⁻³ '
                          f'({getattr(sd_row, "name", "")}), channel '
                          f'{ch_type} {n_ch:.3g} cm⁻³ '
                          f'({getattr(ch_row, "name", "")}); '
                          'contacts refused (metal)')
        return out
    frame = frame_at(p, vg, vd)
    out['frame'] = {key: frame[key] for key in
                    ('vgsi', 'vdsi', 'vt', 'ff', 'fsat', 'vdsat',
                     'id_a')}
    u, meta = _potential_si(p, geo, frame, xs)
    if field == 'potential':
        out['value'] = u
        out['unit'] = 'eV'
        out.update(meta)
        ch = next(r for r in regions if r['kind'] == 'channel')
        in_ch = [v for x, v in zip(xs, u)
                 if ch['x0'] <= x <= ch['x1']]
        out['barrier_top_ev'] = max(in_ch) if in_ch else None
        out['barrier_height_ev'] = ((max(in_ch) - u[0]) if in_ch
                                    else None)
        out['source_lead_ev'] = u[0]
        out['drain_lead_ev'] = u[-1]
        return out
    # electron-density: [SZE07] charge-sheet SHEET density along the
    # barrier; S/D = row concentration × junction depth (areal),
    # contacts refused (metal).
    phit = thermal_voltage_v(float(dev.temperature_k))
    cinv = float(p['si_cox_f_per_m2']) * lit('cinv_over_cox')
    n_max_cm2 = (cinv * max(frame['vgsi'] - frame['vt'], phit)
                 / Q_C) * 1e-4
    xj_cm = float(getattr(sd_row, 'junction_depth_nm', 20.0)
                  or 20.0) * 1e-7
    n_sd_cm2 = (float(getattr(sd_row, 'concentration_cm3', 0.0)
                      or 0.0) * xj_cm)
    ch = next(r for r in regions if r['kind'] == 'channel')
    u0 = max(v for x, v in zip(xs, u) if ch['x0'] <= x <= ch['x1'])
    vals = []
    for x, uu in zip(xs, u):
        kind = _region_at(regions, x)['kind']
        if kind == 'contact':
            vals.append(None)
        elif kind == 'extension':
            vals.append(n_sd_cm2)
        else:
            vals.append(min(n_sd_cm2,
                            n_max_cm2 * math.exp(-(uu - u0) / phit)))
    out['value'] = vals
    out['unit'] = 'cm^-2'
    out['n_channel_max_cm2'] = n_max_cm2
    out['n_sd_cm2'] = n_sd_cm2
    out['formula'] = ('n_s(x) = min(n_SD, n_ch·exp(−(U(x)−U₀)/φt)); '
                      'n_ch = Cinv·max(Vgsi−Vt, φt)/q (charge sheet '
                      '[SZE07]); n_SD = N_SD·x_j (areal, the S/D '
                      'row); contacts: None (metal)')
    return out


# ---- fg-6: silicon FIELD BANDS for the 3-D sample rows -------------
# Built as a TRANSFORM of the CNT band set: same (field, order) →
# same style_ref (colours / Material3DDefinition rows already
# seeded), silicon RANGES swapped in — the sheet density is areal
# (cm^-2, ~1e9–1e14) and doping volumetric (cm^-3); the CNT per-tube
# 1/m bands would put every silicon value in the top band. Potential
# bands (eV) keep the CNT ranges (same physical scale).

_INF_ = float('inf')

#: (field, order) → (min, max, unit, label); fields absent here keep
#: the CNT band's own range (potential).
_SI_RANGES = {
    ('electron-density', 0): (0.0, 1e10, 'cm^-2', 'n_s < 1e10'),
    ('electron-density', 1): (1e10, 1e11, 'cm^-2', '1e10..1e11'),
    ('electron-density', 2): (1e11, 1e12, 'cm^-2', '1e11..1e12'),
    ('electron-density', 3): (1e12, 1e13, 'cm^-2', '1e12..1e13'),
    ('electron-density', 4): (1e13, 1e14, 'cm^-2', '1e13..1e14'),
    ('electron-density', 5): (1e14, _INF_, 'cm^-2', 'n_s > 1e14'),
    ('n-doping', 0): (0.0, 1.0, 'cm^-3', 'intrinsic'),
    ('n-doping', 1): (1.0, 1e18, 'cm^-3', 'N < 1e18'),
    ('n-doping', 2): (1e18, 1e20, 'cm^-3', 'N 1e18..1e20'),
    ('n-doping', 3): (1e20, _INF_, 'cm^-3', 'N > 1e20'),
    ('p-doping', 0): (0.0, 1.0, 'cm^-3', 'intrinsic'),
    ('p-doping', 1): (1.0, 1e18, 'cm^-3', 'N < 1e18'),
    ('p-doping', 2): (1e18, 1e20, 'cm^-3', 'N 1e18..1e20'),
    ('p-doping', 3): (1e20, _INF_, 'cm^-3', 'N > 1e20'),
}


def _si_bands():
    from cntfet.cnt_fields_basis import SEED_FET_FIELD_BANDS
    out = []
    for b in SEED_FET_FIELD_BANDS:
        r = _SI_RANGES.get((b['field'], b['order']))
        nb = dict(b)
        if r is not None:
            nb['min_value'], nb['max_value'], nb['unit'], nb['label'] = r
        out.append(nb)
    return out


SI_FIELD_BANDS = _si_bands()
