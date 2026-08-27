"""
@module sifet.si_device

The derive act + the device_model ADAPTOR for silicon MOSFET rows.
`si_device_model(manager, name) -> (id_fn, p, device, refusal)`
satisfies the cntfet.cnt_device_viz.device_model contract, so every
fv/fi consumer (states, regimes, metrics, scoring, validity,
characteristics, compare) runs on a silicon device unchanged. The
integrator dispatches on SI_DEVICE_CLASS from device_model.

@consumers
  - cntfet.cnt_device_viz.device_model (dispatch — to be wired)
  - sifet.selftest_sifet
"""

import json
from datetime import datetime, timezone

from sifet.si_model import (
    SI_CITATIONS, SI_EQUATION_REVISION, SI_LIT, build_si_vs_params,
    polarity_aware_id_fn, provenance_for,
)

SI_DEVICE_CLASS = 'SiliconMOSFET'
SI_TABLES = ('SiliconDopingProfile', 'SolGelDielectric', 'SolGelProcess',
             'SiliconFETShape', 'SiliconMOSFET')


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_row(manager, class_name, name):
    tables = getattr(manager, 'objectTables', None) or {}
    for row in (tables.get(class_name) or {}).values():
        if getattr(row, 'name', '') == name:
            return row
    return None


def _save(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def _refuse(error):
    return {'ok': False, 'error': error}


def resolve_components(manager, device):
    wanted = {
        'shape': ('SiliconFETShape', device.shape),
        'channel_doping': ('SiliconDopingProfile', device.channel_doping),
        'sd_doping': ('SiliconDopingProfile', device.sd_doping),
        'dielectric': ('SolGelDielectric', device.dielectric),
        'process': ('SolGelProcess', device.process),
    }
    rows, missing = {}, []
    for key, (cls, name) in wanted.items():
        row = get_row(manager, cls, name)
        if row is None:
            missing.append(f'{cls} "{name}"')
        rows[key] = row
    return rows, missing


def _as_dict(row, keys):
    return {k: getattr(row, k) for k in keys}


def params_from_rows(rows, device, lg_nm=None):
    """build_si_vs_params from live rows (lg_nm override = the
    'temporary shorter device' affordance for DIBL comparisons)."""
    shape = _as_dict(rows['shape'], ('kind', 'channel_width_nm',
                                     'fin_height_nm', 'fin_width_nm',
                                     'n_fins', 'gate_all_around'))
    ch = _as_dict(rows['channel_doping'], ('dopant_type',
                                           'concentration_cm3',
                                           'activation_fraction'))
    sd = _as_dict(rows['sd_doping'], ('concentration_cm3',))
    diel = _as_dict(rows['dielectric'], ('thickness_nm', 'k_rel'))
    dev = _as_dict(device, ('polarity', 'lg_nm', 'w_nm', 'vfb_v',
                            'rc_ohm_um'))
    if lg_nm is not None:
        dev['lg_nm'] = lg_nm
    return build_si_vs_params(shape, ch, sd, diel, dev,
                              device.temperature_k)


def derive_si_device(manager, device):
    """Stamp the derived VS parameters + provenance on the device
    row. Returns the honest report dict (cnt_derive style)."""
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}',
                'refusal': 'derive refuses on incomplete '
                           'decomposition — no defaults invented'}
    want = 'n' if device.polarity == 'n' else 'p'
    if rows['channel_doping'].dopant_type == want:
        return {'ok': False,
                'error': f'channel doping "{device.channel_doping}" is '
                         f'{want}-type for a {want}-channel device — '
                         'the body must be the opposite type',
                'refusal': 'pick the complementary doping row'}
    p = params_from_rows(rows, device)
    stamp = _now()
    device.vt0_v = p['si_vt0_signed_v']
    device.n_ss = p['n_ss']
    device.dibl_v_per_v = p['dibl_v_per_v']
    device.dvt_v = p['dvt_v']
    device.mu_cm2_per_vs = p['si_mu_eff_cm2_per_vs']
    device.vxo_m_per_s = p['vxo_m_per_s']
    device.cinv_f_per_m = p['cinv_f_per_m']
    device.lambda_nm = p['lambda_nm']
    device.equation_revision = SI_EQUATION_REVISION
    device.derived_at = stamp
    prov = provenance_for(p)
    prov['priors'] = {'vfb_v': device.vfb_source,
                      'rc_ohm_um': 'device row prior',
                      'dielectric': rows['dielectric'].citation,
                      'dielectric_confidence':
                          rows['dielectric'].confidence}
    prov['intermediates'] = {k: v for k, v in p.items()
                             if k.startswith('si_')}
    device.provenance_json = json.dumps(prov)
    _save(manager, device)
    return {'ok': True, 'device': device.name, 'derived_at': stamp,
            'equation_revision': SI_EQUATION_REVISION,
            'params': {k: v for k, v in p.items()
                       if not k.startswith('si_')},
            'intermediates': prov['intermediates'],
            'refusals': prov['refusals']}


def si_device_model(manager, name):
    """(id_fn, p, device, None) or (None, None, None, refusal) — the
    cnt_device_viz.device_model contract for SiliconMOSFET rows."""
    if manager is None:
        return None, None, None, _refuse(
            'no manager — device rows are not reachable')
    device = get_row(manager, SI_DEVICE_CLASS, name)
    if device is None:
        return None, None, None, _refuse(
            f'no {SI_DEVICE_CLASS} named "{name}"')
    if not getattr(device, 'derived_at', ''):
        return None, None, None, _refuse(
            f'device "{name}" never derived — POST '
            f'{{"action": "derive"}} to /api/sifet/devices/{name} '
            'first')
    rows, missing = resolve_components(manager, device)
    if missing:
        return None, None, None, _refuse(
            f'missing component rows: {missing}')
    p = params_from_rows(rows, device)
    return polarity_aware_id_fn(p, device.polarity), p, device, None


def metric_spec(device):
    """extract_metrics spec scaled to this device: Vdd from the row,
    constant-current Vt criterion 100 nA per um of width (the
    silicon convention) instead of the CNT per-tube 1 nA."""
    w_um = device.w_nm / 1000.0
    return {'vdd_v': device.vdd_v, 'id_crit_a': 1e-7 * max(w_um, 1e-3)}


def capability():
    """The D14 honesty surface for sifet."""
    return {
        'module': 'sifet',
        'device_class': SI_DEVICE_CLASS,
        'fidelity': 'VS_SI_MINIMAL — [KHA09] virtual-source core '
                    '(REUSED from cntfet.cnt_vs_model) parameterized '
                    'from doping / dielectric / shape rows',
        'equation_revision': SI_EQUATION_REVISION,
        'provides': {
            'derive': 'Vt, n_ss, DIBL, dVt, mu, v_xo, Cinv, lambda per '
                      'shape kind (planar-bulk | soi | finfet | '
                      'gaa-nanosheet)',
            'device_model': 'si_device_model -> (id_fn, p, device, '
                            'refusal): every cntfet fv/fi surface '
                            'works on a SiliconMOSFET',
            'polarity': 'p devices via the mirror transform '
                        '(ptype = 1, Id_p(vg,vd) = -Id_n(-vg,-vd))',
        },
        'refusals': {
            'gate-leakage': 'no tunnelling / gate-leakage model; the '
                            'sol-gel leakage_prior_a_per_cm2 is a '
                            'PRIOR on the dielectric row and never '
                            'enters Id or power',
            'gidl': 'not modeled',
            'interface-traps': 'SS carries the body factor and SCE '
                               'only; Dit degradation absent',
            'quantum-confinement': 'no Vt shift for thin fins',
            'strain': 'no mobility enhancement',
            'sol-gel-conformality': 'film thickness on a fin sidewall '
                                    'is taken equal to the planar '
                                    'thickness (prior)',
            'vfb': 'flat-band is a per-device PRIOR, not computed '
                   'from a gate work-function row',
        },
        'priors': [k for k, v in SI_LIT.items() if v['role'] ==
                   'compact-model' and v['confidence'] == 'low'],
        'citations': SI_CITATIONS,
    }
