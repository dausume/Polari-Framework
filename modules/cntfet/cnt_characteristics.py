"""
@module cntfet.cnt_characteristics

fv-3 (FET_VIEWS_PLAN §1): the FET-CHARACTERISTIC registry — "select
FET characteristics and get appropriate views and description of them
and what they mean for the performance of a FET" (Dustin 2026-08-27).

Each characteristic is a ROW (FETCharacteristic): the physics
description, the performance meaning, the governing equation, the
regimes / states / transport nodes it touches, the ScoreTerms it
feeds, and an ORDERED list of VIEWS — each view names a seeded
GraphDefinition (or an API panel, or a sim-space scene) and a
device-relative dataPath template, plus WHY that view is the one to
look at. Nothing here renders: the explorer (fv-5) and the per-device
detail page resolve `{device}` and hand the paths to the existing
named-graph-panel / api-structured-panel / sim-space components
(report views carry `pick` / `hideKeys` so no JSON reaches the
screen).

Honesty: a view whose graph is not (yet) seeded on this node is
reported `status: 'unbuilt'` with the phase that owns it — a
characteristic never silently loses a view.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/device/{name}/characteristics,
    …/characteristic/{key})
  - cntfet.cnt_compare (detail page seeds, fv-5)
  - polariServer (FETCharacteristic registration + seeds)
  - cntfet.selftest_cntfet
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class FETCharacteristic(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',            # kebab key
        display_name: str = '',
        order: int = 0,
        group: str = '',           # iv | switching | transport | fields | quality
        description: str = '',     # the physics
        performance_meaning: str = '',
        equation: str = '',
        related_states_json: str = '[]',
        related_regimes_json: str = '[]',
        related_terms_json: str = '[]',
        views_json: str = '[]',    # [{kind, graphName|componentName|simSpaceName, dataPath, title, why}]
        # fp-6: input | output | transfer | structure — how a device
        # datasheet organises characteristics (Dustin 2026-08-27)
        category: str = '',
        # fp-6: the average-person explanation (no equations)
        explain: str = '',
        citations_json: str = '[]',
        fidelity: str = '',
        origin: str = 'seeded',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.group = group
        self.description = description
        self.performance_meaning = performance_meaning
        self.equation = equation
        self.related_states_json = related_states_json
        self.related_regimes_json = related_regimes_json
        self.related_terms_json = related_terms_json
        self.views_json = views_json
        self.category = category
        self.explain = explain
        self.citations_json = citations_json
        self.fidelity = fidelity
        self.origin = origin
        self.notes = notes
        self.is_prior = is_prior


def _graph(graph, curve, title, why, extra=''):
    return {'kind': 'graph', 'graphName': graph,
            'dataPath': '/api/cntfet/device/{device}/points?curve='
                        + curve + extra,
            'title': title, 'why': why}


def _api(path, title, why, pick='', hide=''):
    """A report view: the STRUCTURED reading of the device's GET
    payload (chips / prose / tables / key-value — never a JSON
    wall). `pick` = dot-path to render; `hide` = csv of keys to
    drop so nothing lands in the panel's JSON expander (an empty
    `refusals` dict is that shape)."""
    return {'kind': 'api', 'componentName': 'api-structured-panel',
            'dataPath': '/api/cntfet/device/{device}' + path,
            'pick': pick, 'hideKeys': hide,
            'title': title, 'why': why}


def _scene(scene, field, title, why):
    """fv-4 sim-space views (scene rows seeded by cnt_scene)."""
    # scene = cnt_scene.scene_name(device) = 'fet-3d-{device}';
    # run = cnt_fields.run_ref(device, field) selects that field's
    # FETFieldSample rows (compile_3d's only row filter is ?run=).
    return {'kind': 'simspace', 'simSpaceName': scene + '-{device}',
            'run': 'fet-fields:{device}:' + field,
            'dataPath': '/api/cntfet/device/{device}/fields?field='
                        + field,
            'field': field, 'title': title, 'why': why,
            'sampleAction': 'POST {"action": "sample-fields"} to '
                            '/api/cntfet/devices/{device} generates '
                            'the rows the scene binds (scrub Vg)'}


def _c(key, display, order, group, description, meaning, equation,
       views, states=(), regimes=(), terms=(), cites=(), fidelity='F1'):
    return {
        'name': key, 'display_name': display, 'order': order,
        'group': group, 'description': description,
        'performance_meaning': meaning, 'equation': equation,
        'related_states_json': json.dumps(list(states)),
        'related_regimes_json': json.dumps(list(regimes)),
        'related_terms_json': json.dumps(list(terms)),
        'views_json': json.dumps(views),
        'citations_json': json.dumps(list(cites)),
        'fidelity': fidelity,
    }


SEED_FET_CHARACTERISTICS = [
    # ── IV ──────────────────────────────────────────────────────
    _c('transfer-characteristic', 'Transfer characteristic Id(Vg)', 0,
       'iv',
       'Drain current versus gate voltage at fixed drain bias. On a '
       'log axis the subthreshold tail (one decade per SS), the '
       'threshold knee and the on-state plateau are all visible.',
       'The whole switch in one curve: how far off is off (Ioff), '
       'how hard on is on (Ion), how much gate swing the transition '
       'costs (SS).',
       'Id = Qxo(Vgs) · v_xo · Fsat(Vds)  [VS1]',
       [_graph('cnt-device-transfer', 'transfer',
               'Id(Vg) per drain bias, log Y',
               'log Y makes the decade band visible'),
        _graph('cnt-device-transfer-states', 'transfer-states',
               'the operating states on the same curve',
               'bands = which state, guides = what qualifies it')],
       states=('off', 'transition-on', 'on-saturation'),
       terms=('fet-on-off-decades', 'fet-ss'), cites=('[VS1]',)),
    _c('output-characteristic', 'Output characteristic Id(Vd)', 1,
       'iv',
       'Drain current versus drain voltage per gate voltage: the '
       'resistor-like linear leg, the Vdsat knee and the saturated '
       'plateau (tilted only by DIBL).',
       'Sets how much current the device delivers into a load and '
       'how stiff a current source it is (output conductance).',
       'Fsat = x/(1+x^β)^(1/β), x = Vds/Vdsat  [KHA09 via VS1]',
       [_graph('cnt-device-output', 'output', 'Id(Vd) per gate bias',
               'the family itself'),
        _graph('cnt-device-output-states', 'output-states',
               'linear vs saturation on Id(Vd)',
               'the Vdsat locus marks the knee'),
        _graph('cnt-device-output-regimes', 'output-regimes',
               'Id(Vd) coloured by regime',
               'each point carries the law it obeys (fv-1)')],
       states=('on-linear', 'on-saturation'),
       regimes=('linear-triode', 'velocity-saturated', 'square-law'),
       terms=('fet-g-on-distance',), cites=('[VS1]', '[KHA09]')),
    _c('regime-map', 'Operating regimes (linear / square / velocity-saturated)',
       2, 'iv',
       'The MOSFET regimes as data: subthreshold-exponential, '
       'linear-triode, square-law (Id ∝ Vov², long channel), '
       'velocity-saturated (Id ∝ Vov, short channel), and the DIBL-'
       'tilted plateau — classified from the local exponent '
       'm = d ln Id / d ln Vov and Vds vs Vdsat.',
       'Tells you which law to design with: square-law devices gain '
       'current quadratically with overdrive, velocity-saturated ones '
       'only linearly — drive, gm and the Vdd scaling story differ.',
       'm = d ln Id / d ln(Vgs − Vt) at fixed Vds; Id ∝ Vov^m',
       [_graph('cnt-device-regime-map', 'regime-map',
               'regime over the (Vd, Vg) plane',
               'one dot per bias point, coloured by regime'),
        _graph('cnt-device-exponent', 'exponent',
               'the exponent m(Vg) with the square-law and velocity-'
               'saturated bands',
               'shows WHICH law the device obeys and where'),
        _api('/regimes?vg=0.6&vd=0.6', 'regime report at Vdd',
             'the criteria with their numbers')],
       regimes=('subthreshold-exponential', 'linear-triode',
                'square-law', 'velocity-saturated',
                'dibl-tilted-saturation'),
       terms=('fet-gm-over-g0',), cites=('[VS1]', '[KHA09]')),
    # ── switching ───────────────────────────────────────────────
    _c('subthreshold-swing', 'Subthreshold swing', 3, 'switching',
       'Gate voltage per decade of current below threshold: '
       'SS = n_ss·φt·ln10; n_ss = 1 is the thermionic floor '
       '(59.5 mV/dec at 300 K).',
       'The cost of turning off: a steeper SS lets Vt sit lower for '
       'the same Ioff, so more of Vdd is overdrive — lower Vdd, less '
       'leakage, faster.',
       'SS = n_ss φt ln10',
       [_graph('cnt-device-transfer-states', 'transfer-states',
               'the subthreshold decade band on Id(Vg)',
               'the slope IS the swing'),
        _api('/score', 'score: SS vs its ideal',
             'distance to the 59.5 mV/dec floor', pick='idealTable')],
       states=('off',), terms=('fet-ss',), cites=('[VS1]',)),
    _c('threshold-voltage', 'Threshold voltage', 4, 'switching',
       'The gate voltage at which the barrier collapses: '
       'Vt(Vds) = vt0 − dVt − DIBL·Vds (the model), or a constant-'
       'current crossing (the measurement convention).',
       'Where the switch sits inside the supply: too low leaks, too '
       'high wastes overdrive — the fi-2 target is the centre of the '
       'window [off_decades·SS, Vdd − vov_decades·SS].',
       'Vt(Vds) = vt0 − dVt − DIBL·Vds  [VS1] eq.(8)',
       [_graph('cnt-device-transfer-states', 'transfer-states',
               'Vt and Vt + Vov_min as guides',
               'the guides are the threshold and the "on" line'),
        _api('/states?vd=0.6&vg=0.3', 'boundaries + sweep events',
             'every boundary with its equation')],
       states=('transition-on', 'transition-off'),
       terms=('fet-vt-distance',), cites=('[VS1]',)),
    _c('dibl', 'DIBL (drain-induced barrier lowering)', 5, 'switching',
       'The drain reaches the source barrier through the channel '
       'electrostatics: Vt drops by DIBL·Vds; scale-length λ ≪ Lg '
       'suppresses it.',
       'Output conductance in saturation and Vt roll-off at high '
       'drain bias — worse noise margins and leakage at Vdd.',
       'DIBL = (Vt(Vd_lin) − Vt(Vdd)) / (Vdd − Vd_lin);  λ from [VS1] eq.(7)',
       [_graph('cnt-device-transfer', 'transfer',
               'Id(Vg) at three drain biases',
               'the curves shift left with Vd by DIBL'),
        _graph('cnt-device-regime-map', 'regime-map',
               'the DIBL-tilted region of the map',
               'where saturation is no longer flat')],
       regimes=('dibl-tilted-saturation',), terms=('fet-dibl',),
       cites=('[VS1]',)),
    _c('on-off-ratio', 'On/off ratio', 6, 'switching',
       'Ion = Id(Vdd, Vdd) over Ioff = Id(0, Vdd): decades of gate '
       'control across the supply window.',
       'Static leakage versus drive — the yield criterion the '
       'Monte Carlo uses (≥ 1e4) and the ceiling Vdd/SS_ideal.',
       'log10(Ion/Ioff) ≤ Vdd/SS',
       [_graph('cnt-device-transfer-envelope', 'transfer-envelope',
               'Id(Vg) with the stochastic envelope',
               'shows how the ratio spreads across the process'),
        _api('/score?samples=100', 'score + MC best/worst',
             'the decades term and its spread', hide='refusals')],
       states=('off', 'on-saturation'), terms=('fet-on-off-decades',),
       cites=('[VS1]',)),
    _c('transconductance', 'Transconductance gm', 7, 'switching',
       'gm = dId/dVg — how strongly the gate steers the current; '
       'peaks just above threshold and is bounded by G0 for one '
       'ballistic 1-D channel.',
       'Gain and speed: intrinsic delay ≈ Cgg/gm; the score term is '
       'gm/G0.',
       'gm = ∂Id/∂Vgs;  gm_max(1-D ballistic) = G0 = 4e²/h',
       [_graph('cnt-device-exponent', 'exponent',
               'the exponent curve (gm/Id ∝ m/Vov)',
               'm and Vov set gm/Id'),
        _api('/characterization', 'characterization: gm_peak',
             'the measured peak and where', pick='metrics',
             hide='refusals')],
       terms=('fet-gm-over-g0',), cites=('[FC10]', '[LUN97]')),
    _c('on-conductance', 'On-conductance g_on vs 0.7·G0', 8,
       'switching',
       'g_on = Id(Vdd, Vd_lin)/Vd_lin — the on-state resistance '
       'including the two contacts; [FC10] measured 0.7·G0 at best.',
       'Series resistance eats drive: g_on far below 0.7·G0 means '
       'contacts, not the channel, limit Ion.',
       'g_on = Id/Vds at Vds → 0;  Rc floor = RQ/2 = h/8e²',
       [_graph('cnt-device-output', 'output',
               'the slope at the origin of each Id(Vd)',
               'that slope is g_on'),
        _api('/transport', 'transport: contact transmission',
             'how much of g_on the contacts cost')],
       terms=('fet-g-on-distance',), cites=('[FC10]',)),
    _c('switching-states', 'Switching states and transitions', 9,
       'switching',
       'Off → transition-on → on-linear / on-saturation → '
       'transition-off, each qualified by explicit criteria over the '
       'model frame (Vt, Vov_min, Vdsat).',
       'The switching event itself — the proof the device IS a FET '
       '(validity gate) and the basis of every timing number.',
       'criteria: Vgs vs Vt(Vds), Vgs vs Vt+Vov_min, Vds vs Vdsat',
       [_graph('cnt-device-transfer-states', 'transfer-states',
               'states on Id(Vg)', 'bands + guides'),
        _graph('cnt-device-output-states', 'output-states',
               'linear vs saturation on Id(Vd)', 'the Vdsat locus'),
        _api('/states?vd=0.6&vg=0.3', 'states report',
             'definitions, boundaries, events')],
       states=('off', 'transition-on', 'on-linear', 'on-saturation',
               'transition-off')),
    # ── transport ───────────────────────────────────────────────
    _c('transport-regime', 'Transport regime (ballistic … scattered)',
       10, 'transport',
       'Transmission T = λ/(λ+Lg) from the Matthiessen mean free '
       'path of every active scattering mechanism; Ballistic (T ≥ '
       '0.9), Quasi-Ballistic, Semi-Scattered, Scattered.',
       'Ion = Ion_ballistic · T/(2−T): a scattered device delivers a '
       'fraction of the ballistic current and its injection velocity '
       'falls with it.',
       'T = λ/(λ+Lg);  B = T/(2−T)  [LUN97]',
       [_graph('cnt-device-transport-vs-lg', 'transport-vs-lg',
               'T versus Lg with the regime bands',
               'where this Lg sits on the curve'),
        _api('/transport?vg=0.6&vd=0.6', 'transport report',
             'λ per mechanism, T, regime with criteria')],
       terms=('fet-gm-over-g0', 'fet-g-on-distance'),
       cites=('[LUN97]', '[RAH03]', '[VS1]')),
    _c('scattering-contributors', 'Scattering contributors', 11,
       'transport',
       'Acoustic phonons (always), optical phonons (once carriers '
       'gain ħω_op ≈ 0.18 eV), defects/impurities (purity), contact '
       'interface (Rc vs RQ/2), misalignment (longer path) — combined '
       'by Matthiessen\'s rule.',
       'Names what to fix: a phonon-limited device is at its '
       'physical limit; a defect- or contact-limited one is a process '
       'problem.',
       '1/λ = Σ 1/λ_i(bias, T, t)',
       [_graph('cnt-device-scattering-contributions',
               'scattering-contributions',
               'fraction of 1/λ per mechanism',
               'the dominant contributor is the tallest'),
        _api('/transport?vg=0.6&vd=0.6', 'per-mechanism detail',
             'λ_i, activation, enforced properties')],
       cites=('[JAV04]', '[PARK04]', '[LUN97]')),
    _c('transport-over-time', 'Properties enforced by scattering over time',
       12, 'transport',
       'Defect accumulation (aging/dose prior) lengthens nothing and '
       'shortens the defect mean free path over time; T, the regime '
       'and the Ion factor follow.',
       'A ballistic device today may be semi-scattered after years — '
       'the drift the design margin must absorb.',
       'λ_def(t) = λ_def0/(1 + t/τ) (PRIOR);  T(t), B(t)',
       [_graph('cnt-device-transport-over-time', 'transport-over-time',
               'T and Ion factor versus time',
               'the regime bands show when the label flips'),
        _api('/transport?t=8760', 'transport at t = 1 year',
             'the numbers at a chosen instant')],
       cites=('[LUN97]',), fidelity='F1 + labelled prior'),
    # ── fields (fv-4 sim-space views) ───────────────────────────
    _c('material-composition', 'Material composition', 13, 'fields',
       'The device as regions: Pd source/drain contacts, doped CNT '
       'extensions, the intrinsic (16,0) CNT channel, the HfO2 '
       'gate-all-around shell and the gate metal — each region tied '
       'to its component row.',
       'Every electrical number traces to a material choice: contact '
       'metal → Rc, oxide k/t → Cinv and SS, tube chirality → Eg.',
       'regions ← CNTMaterialState / GateStack / CNTContact rows',
       [_scene('fet-3d', 'material',
               '3-D device coloured by material',
               'the geometry the equations live in'),
        _graph('cnt-device-field-material', 'field-material',
               '2-D cross-section by material',
               'the same regions along the channel axis')],
       fidelity='geometry from the component rows'),
    _c('potential-at-instant', 'Voltage potential across the transistor',
       14, 'fields',
       'The conduction-band edge U(x) at one bias instant: the '
       'source barrier at the virtual source x0 set by Vgs, the drop '
       'across the channel set by Vds, decaying over the scale '
       'length λ — an analytic F1 SKETCH; the D13 SCF profile is the '
       'row-backed truth where present.',
       'Barrier height = Ioff; barrier width and slope = tunnelling '
       'and DIBL; the drop = where carriers gain the optical-phonon '
       'energy.',
       'U(x) ≈ U_barrier(Vgs) · exp(−|x−x0|/λ) − q·Vds·f(x)  [F1 SKETCH]',
       [_scene('fet-3d', 'potential',
               'potential along the channel, at this Vg/Vd',
               'the barrier you switch'),
        _graph('cnt-device-field-potential', 'field-potential',
               'U(x) at several gate voltages',
               'watch the barrier collapse with Vg')],
       states=('off', 'transition-on', 'on-saturation'),
       fidelity='F1 SKETCH (D13 SCF rows where present)'),
    _c('gate-voltage', 'Gate voltage', 15, 'fields',
       'The gate terminal sets the barrier through Cinv (oxide + '
       'quantum capacitance in series): Vgs → Qxo → barrier height.',
       'The control knob: overdrive Vgs − Vt buys current linearly '
       '(velocity-saturated) or quadratically (square-law).',
       'Qxo = Cinv n_ss φt ln(1 + exp((Vgsi − Vt)/(n_ss φt)))',
       [_scene('fet-3d', 'potential',
               'potential with the gate at Vgs',
               'the gate region and what it does to U(x)'),
        _graph('cnt-device-transfer-states', 'transfer-states',
               'Id(Vg) with states', 'the gate sweep')],
       states=('transition-on',)),
    _c('drain-voltage', 'Drain voltage', 16, 'fields',
       'The drain terminal drops Vds across the channel; above Vdsat '
       'the extra voltage falls near the drain and only DIBL still '
       'reaches the source barrier.',
       'Sets the linear/saturation boundary, the DIBL penalty and '
       'whether carriers reach the optical-phonon energy.',
       'Vdsat = (v_xo Lg/μ)(1 − Ff) + φt Ff',
       [_scene('fet-3d', 'potential',
               'potential with the drain at Vds', 'the drop'),
        _graph('cnt-device-output-states', 'output-states',
               'Id(Vd) with the Vdsat locus', 'the drain sweep')],
       states=('on-linear', 'on-saturation')),
    _c('electron-density', 'Electron density', 17, 'fields',
       'n(x) along the channel: the virtual-source charge Qxo/q at '
       'x0 and the semi-classical Boltzmann fall-off with U(x) — '
       'high in the doped extensions, gated in the channel.',
       'The charge that carries Id (Id = Qxo·v_xo): where it thins '
       'the device is resistive, where it is pinned the gate has '
       'lost control.',
       'n(x) ≈ (Qxo/q) · exp(−(U(x) − U(x0))/kT)  [F1 SKETCH]',
       [_scene('fet-3d', 'electron-density',
               'electron density along the channel',
               'where the carriers are at this bias'),
        _graph('cnt-device-field-density', 'field-density',
               'n(x) at several gate voltages',
               'the channel filling with Vg')],
       fidelity='F1 SKETCH'),
    _c('n-doping-density', 'n-doping density', 18, 'fields',
       'Donor doping of the source/drain extensions (the Efsd '
       'parameter: Fermi level above the band edge → carrier density '
       'through the 1-D DOS); the channel is intrinsic.',
       'Doped extensions lower series resistance and set the contact '
       'barrier picture ([FIO05] doped-extension CNTFETs).',
       'n_ext = ∫ D1D(E) f(E − Efsd) dE',
       [_scene('fet-3d', 'n-doping', 'n-doping by region',
               'the extensions vs the intrinsic channel'),
        _graph('cnt-device-field-doping', 'field-doping',
               'n/p doping along x', 'the profile')],
       cites=('[FIO05]',)),
    _c('p-doping-density', 'p-doping density', 19, 'fields',
       'Acceptor doping — zero everywhere on the n-FET; the p-twin '
       'mirrors the extension doping (polarity flip, [VS1] premise '
       'ii).',
       'For a CMOS pair the p-device\'s doping mirrors the n-device; '
       'unequal doping = unequal drive = skewed cells.',
       'p-twin: n_ext → p_ext, Vt → −Vt',
       [_scene('fet-3d', 'p-doping', 'p-doping by region',
               'zero on the n-FET, mirrored on the p-twin'),
        _graph('cnt-device-field-doping', 'field-doping',
               'n/p doping along x', 'the profile')],
       cites=('[VS1]',)),
    # ── quality ─────────────────────────────────────────────────
    _c('stochastic-spread', 'Stochastic spread (best / worst case)',
       20, 'quality',
       'The process set\'s distributions (diameter, Lg, alignment, '
       'oxide, Vt0, Rc) sampled into a population; the envelope of '
       'Id(Vg) and the best/worst devices by score.',
       'Yield and margin: what the design must tolerate, and which '
       'distribution moves the score most.',
       'Monte Carlo over the process rows; score per sample',
       [_graph('cnt-device-transfer-envelope', 'transfer-envelope',
               'Id(Vg) envelope', 'p05–p95 and min–max'),
        _graph('cnt-device-score-terms', 'score-terms',
               'terms with their MC spread', 'best/worst dots')]),
    _c('switching-quality-score', 'Switching quality score', 21,
       'quality',
       'The weighted mean of every figure of merit normalized against '
       'its characteristic-equation ideal — gated to 0 if the device '
       'cannot be proven to switch.',
       'One number to rank FETs by, with every term inspectable.',
       'score = Σ w·norm / Σ w;  validity gate',
       [_graph('cnt-device-score-terms', 'score-terms',
               'terms vs ideal', 'the rule at 1.0'),
        _graph('cnt-device-compare', 'compare',
               'this FET vs every FET', 'the ranking'),
        _api('/score?samples=100', 'score + validity proofs',
             'the numbers', hide='refusals')],
       terms=tuple()),
]


# ── fp-6: datasheet categories + plain-language explanations ──────
#
# input     = what the gate/input terminal sees and sets
# output    = what the drain/output terminal delivers
# transfer  = how input becomes output (the switch itself)
# structure = what the device is made of / how it is built

CATEGORY = {
    'input': ('gate-voltage', 'threshold-voltage', 'subthreshold-swing',
              'n-doping-density', 'p-doping-density'),
    'output': ('output-characteristic', 'drain-voltage', 'dibl',
               'on-conductance', 'regime-map'),
    'transfer': ('transfer-characteristic', 'on-off-ratio',
                 'transconductance', 'switching-states',
                 'transport-regime', 'scattering-contributors',
                 'transport-over-time', 'stochastic-spread',
                 'switching-quality-score'),
    'structure': ('material-composition', 'potential-at-instant',
                  'electron-density'),
}
CATEGORY_MEANING = {
    'input': 'What you put in at the gate, and what it takes to make '
             'the device listen.',
    'output': 'What comes out at the drain: how much current, and how '
              'steady it is.',
    'transfer': 'How the input becomes the output — the switch itself, '
                'how sharply and how reliably it flips.',
    'structure': 'What the device is made of and what is happening '
                 'inside it at a given moment.',
}

EXPLAIN = {
    'transfer-characteristic':
        'Turn the gate knob and watch the current: nothing, nothing, '
        'then a steep climb, then a plateau. That curve is the whole '
        'personality of the switch.',
    'output-characteristic':
        'Hold the gate steady and push harder on the drain: at first '
        'the current grows like a resistor, then it stops growing — '
        'the device has become a current source.',
    'regime-map':
        'A map of where the device behaves like a resistor, where it '
        'behaves like a current source, and which law it obeys in '
        'each region.',
    'subthreshold-swing':
        'How much gate voltage it costs to make the leakage ten times '
        'smaller. Smaller is better; nature sets a floor at about 60 '
        'millivolts per factor of ten at room temperature.',
    'threshold-voltage':
        'The gate voltage where the switch starts to open. Too low and '
        'it leaks when it should be off; too high and there is little '
        'supply left to turn it hard on.',
    'dibl':
        'When the drain pulls hard it also weakens the gate\'s grip — '
        'the switch opens a little earlier than it should. Longer '
        'channels and wrap-around gates fight this.',
    'on-off-ratio':
        'How much bigger the on-current is than the leak. More decades '
        '= a cleaner switch and less wasted power.',
    'transconductance':
        'How much the current changes for a small nudge of the gate — '
        'the device\'s sensitivity, and the engine of both speed and '
        'amplifier gain.',
    'on-conductance':
        'How much resistance is left when the switch is fully on — the '
        'contacts often dominate here.',
    'switching-states':
        'Off, waking up, on-as-a-resistor, on-as-a-current-source, and '
        'back — each with the exact test that puts a bias point in it.',
    'transport-regime':
        'Do the electrons fly straight through (ballistic) or bounce '
        'their way across (scattered)? Short channels fly; heat and '
        'high voltage make them bounce.',
    'scattering-contributors':
        'What the electrons bounce off: lattice vibrations (always), '
        'high-energy vibrations (only at high drain voltage), defects, '
        'the contacts, and a crooked tube.',
    'transport-over-time':
        'Defects accumulate with use, so a device that flies today may '
        'bounce in a few years — a margin the design must carry.',
    'material-composition':
        'The parts: metal contacts, doped ends, the bare nanotube '
        'channel, the thin oxide shell, and the gate metal around it.',
    'potential-at-instant':
        'The hill electrons must climb to get from source to drain at '
        'this instant; the gate lowers the hill, the drain tilts it.',
    'gate-voltage':
        'The control knob. It sets how tall the hill is.',
    'drain-voltage':
        'The pull. It tilts the hill and decides whether the device is '
        'resistor-like or current-source-like.',
    'electron-density':
        'Where the electrons are along the channel right now — crowded '
        'at the doped ends, thin over the hill.',
    'n-doping-density':
        'Extra electrons deliberately added at the ends so the contacts '
        'connect well.',
    'p-doping-density':
        'Extra holes — zero on this n-type device; its p-type partner '
        'mirrors the doping.',
    'stochastic-spread':
        'Manufacturing is never exact: this is how much the device '
        'varies across a batch, and which imperfection matters most.',
    'switching-quality-score':
        'One number from 0 to 1 that says how close to an ideal switch '
        'this device is — and 0 if it cannot even be shown to switch.',
}


def _apply_fp6(seed):
    for cat, keys in CATEGORY.items():
        if seed['name'] in keys:
            seed['category'] = cat
    seed.setdefault('category', 'transfer')
    seed['explain'] = EXPLAIN.get(seed['name'], '')
    return seed


SEED_FET_CHARACTERISTICS = [_apply_fp6(s) for s in SEED_FET_CHARACTERISTICS]


# ── resolution ─────────────────────────────────────────────────────

def _rows(manager):
    rows = {}
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'FETCharacteristic') or {}
        for row in (table.values() if isinstance(table, dict)
                    else table):
            rows[row.name] = {k: getattr(row, k) for k in (
                'name', 'display_name', 'order', 'group', 'description',
                'performance_meaning', 'equation', 'related_states_json',
                'related_regimes_json', 'related_terms_json',
                'views_json', 'citations_json', 'fidelity',
                'category', 'explain')}
    for seed in SEED_FET_CHARACTERISTICS:
        rows.setdefault(seed['name'], seed)
    return dict(sorted(rows.items(), key=lambda kv: kv[1]['order']))


def _seeded_graph_names(manager):
    names = set()
    if manager is not None:
        table = getattr(manager, 'objectTables', {}).get(
            'GraphDefinition') or {}
        names = {getattr(r, 'name', '')
                 for r in (table.values() if isinstance(table, dict)
                           else table)}
    return names


def resolve_views(views, device_name, graph_names, scene_names):
    """Fill {device}; mark views whose graph/scene is not seeded on
    this node as 'unbuilt' (with the owning phase) — never dropped."""
    out = []
    for v in views:
        r = dict(v)
        for key in ('dataPath', 'simSpaceName', 'run', 'sampleAction'):
            if isinstance(v.get(key), str):
                r[key] = v[key].replace('{device}', device_name)
        if v['kind'] == 'graph':
            r['status'] = ('ready' if (not graph_names
                                      or v['graphName'] in graph_names)
                           else 'unbuilt')
            if r['status'] == 'unbuilt':
                r['owner'] = ('fv-4 (cnt_fields)'
                              if v['graphName'].startswith(
                                  'cnt-device-field') else 'fv-1/fv-2')
        elif v['kind'] == 'simspace':
            r['status'] = ('ready' if r['simSpaceName'] in scene_names
                           else 'unbuilt')
            if r['status'] == 'unbuilt':
                r['owner'] = 'fv-4 (cnt_scene)'
        else:
            r['status'] = 'ready'
        out.append(r)
    return out


def characteristics_index(manager, device_name):
    rows = _rows(manager)
    return {'ok': True, 'device': device_name,
            'groups': ['iv', 'switching', 'transport', 'fields',
                       'quality'],
            # fp-6: the datasheet organisation (input / output /
            # transfer / structure) beside the physics grouping
            'categories': [{'key': c, 'meaning': CATEGORY_MEANING[c]}
                           for c in ('input', 'output', 'transfer',
                                     'structure')],
            'characteristics': [
                {'key': r['name'], 'display_name': r['display_name'],
                 'group': r['group'], 'order': r['order'],
                 'category': r.get('category', ''),
                 'explain': r.get('explain', ''),
                 'performance_meaning': r['performance_meaning'],
                 'viewCount': len(json.loads(r['views_json']))}
                for r in rows.values()],
            'provenance': _device_provenance(manager, device_name),
            'detailPath': f'/api/cntfet/device/{device_name}'
                          '/characteristic/{key}'}


def characteristic_detail(manager, device_name, key, scene_names=()):
    rows = _rows(manager)
    row = rows.get(key)
    if row is None:
        return {'ok': False, 'error': f'no characteristic "{key}"',
                'known': sorted(rows)}
    views = resolve_views(json.loads(row['views_json']), device_name,
                          _seeded_graph_names(manager), set(scene_names))
    return {'ok': True, 'device': device_name, 'key': key,
            'display_name': row['display_name'], 'group': row['group'],
            'category': row.get('category', ''),
            'explain': row.get('explain', ''),
            'description': row['description'],
            'performance_meaning': row['performance_meaning'],
            'equation': row['equation'], 'fidelity': row['fidelity'],
            'related': {'states': json.loads(row['related_states_json']),
                        'regimes': json.loads(row['related_regimes_json']),
                        'terms': json.loads(row['related_terms_json'])},
            'citations': json.loads(row['citations_json']),
            'views': views,
            'unbuiltViews': [v['title'] for v in views
                             if v['status'] == 'unbuilt']}


def _device_provenance(manager, device_name):
    from cntfet.cnt_device_viz import provenance
    return provenance(manager, 'device', device_name)
