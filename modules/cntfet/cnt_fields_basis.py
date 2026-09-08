"""
@module cntfet.cnt_fields_basis

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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_fields/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import math
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.custom.cnt_bandstructure import dos_per_j_per_m
from cntfet.custom.cnt_constants import KB_J_PER_K, Q_C, lit_value
from cntfet.custom.cnt_derive import resolve_components
from cntfet.cnt_device_viz_seed import _device_graph, device_model
from cntfet.cnt_states_basis import frame_at
from cntfet.custom.cnt_vs_model import _softplus

from cntfet.objects.cnt_fields._shared import CURVE_BUILDERS, FIDELITY, FIELDS, FIELD_KNOBS, SCALAR_FIELDS, SEEDED_STYLE_NAMES, SEED_CNT_FIELD_GRAPHS, SEED_FET_FIELD_BANDS, SEED_FET_FIELD_MATERIALS_3D, _INF, _analytic_ec, _band, _doping_curve, _drop_old_samples, _field_graph, _mat, _material_curve, _material_of, _now, _potential, _refuse, _scalar_curve, _scf_profile_rows, _x_grid, band_for, device_regions, field_profile, field_rows, n_ext_per_m, qxo_c_per_m, region_at, region_band_rows, run_ref  # noqa: F401
from cntfet.objects.cnt_fields.FETFieldSample import FETFieldSample  # noqa: F401
from cntfet.objects.cnt_fields.FETFieldBand import FETFieldBand  # noqa: F401

from cntfet.cnt_device_viz_seed import _device_graph, device_model

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
    Vdd; a SILICON device is banded with sifet.custom.si_fields.
    SI_FIELD_BANDS (areal cm^-2 / cm^-3 ranges — the CNT per-tube 1/m
    bands would put every silicon value in the top band)."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    name = device if isinstance(device, str) else getattr(device, 'name', '')
    _id_fn, _p, dev, refusal = device_model(manager, name)
    if refusal is not None:
        return {**refusal, 'fidelity': FIDELITY}
    from cntfet.cnt_device_viz_seed import device_vdd
    vdd = device_vdd(dev)
    if vd is None:
        vd = vdd
    if vg_list is None:
        vg_list = tuple(round(vdd * i / 6.0, 4) for i in range(7))
    if bands is None and not hasattr(dev, 'material'):
        try:
            from sifet.custom.si_fields import SI_FIELD_BANDS
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
