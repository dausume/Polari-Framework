"""
@module sifet.si_refinement

fp-4 (2026-08-27): silicon REFINEMENT as data — the grade ladder
MG-Si → UMG-Si → SoG-Si (PV) → EG-Si (semiconductor), the unit steps
that move material up the ladder, the ROUTES that chain them, and
the computable models each step cites so a feed can be pushed
through a route and graded honestly.
Plan: AI-Notes/plans/FET_CELL_POWER_SILICON_PLAN.md §1 fp-4, §2 dec 5.

The characteristic equation of the whole arc is Scheil segregation
during solidification from the melt:

  C_s(f_s) = k_eff · C_0 · (1 − f_s)^(k_eff − 1)

k_eff (the effective segregation coefficient, solid/liquid) is per
IMPURITY: metals (Fe, Al, Ca, Ti…) have k ≪ 1 and are stripped in
one directional pass; B (0.8) and P (0.35) have k close to 1 and
barely move — which is WHY PV-grade silicon is reachable by open
solidification-based routes and semiconductor-grade (9N–11N in B/P)
is not: B/P must be removed by a different physics (evaporation
under vacuum for P, reactive gas/plasma for B, or the Siemens
distillation of chlorosilanes) and the open literature documents
the PV-grade endpoint of those, not the 11N one.

Cross-references (by NAME, not duplicated here):
  techtree: TechNode 'silicon-refinement' (electronics tree),
            'silicon-supply' / 'silicon-supply-pv-grade' /
            'silicon-supply-semiconductor-grade' (supply tree),
            'silicon' (materials tree)  — techtree.techtree_seed
  materials: diamond-cubic silicon seed (msci/ssp) per
            MATERIALS_TECH_TREE_PLAN.md §"Silicon" row
  ceramics ladder rung style: pspp.ceramics_ladder.LadderRung

Honesty: every step / route carries `openness` ∈
  'open-research'          documented in open literature; an
                           open-source implementation is plausible
  'industrial-proprietary' chemistry open, process know-how closed
  'novel-needed'           no open route to the grade; candidate
                           directions are labelled PRIOR rows
and a route's openness is the WORST of its steps. Every numeric
prior is labelled `confidence` and cited; 'to verify' is written
where a value is remembered rather than checked against the source.

@consumers
  - sifet.selftest_refinement
  - sifet API (GET /api/sifet/refinement — wired by the integrator)
  - polariServer (SiliconGrade / RefinementStep / RefinementRoute
    registration + SEED_* lists)
"""

import json
import math

from objectTreeDecorators import treeObject, treeObjectInit

OPENNESS = ('open-research', 'industrial-proprietary', 'novel-needed')
#: worst-first ordering used by route_openness
_OPENNESS_RANK = {'open-research': 0, 'industrial-proprietary': 1,
                  'novel-needed': 2}

IMPURITIES = ('B', 'P', 'Fe', 'Al', 'Ca', 'C', 'O')

#: Explicit knobs — every route_simulation result echoes them.
REFINEMENT_KNOBS = {
    # fraction solidified kept as product in a directional pass
    # (the last 1 − fs_cut is the impurity-rich crop-off)
    'fs_cut': 0.9,
    # zone-refining passes (Pfann multipass)
    'passes': 3,
    # molten-zone length as a fraction of ingot length
    'zone_fraction': 0.1,
    # vacuum / plasma refining hold time (2 h — the NEDO / Zheng
    # experiments run 1–3 h)
    'evaporation_time_s': 7200.0,
    # melt surface-to-volume ratio for evaporation (1/m); a 10 cm
    # deep lab induction melt ≈ 10 /m (a 30 cm industrial melt is
    # 3.3 /m — 3× slower, same floor)
    'area_over_volume_per_m': 10.0,
}

# ------------------------------------------------------------------
# Citations (full references; 'to verify' marks values remembered
# rather than checked against the source in this session).
# ------------------------------------------------------------------
CITATIONS = {
    '[TRU60]': {
        'citation': 'F. A. Trumbore, "Solid Solubilities of Impurity '
                    'Elements in Germanium and Silicon", Bell System '
                    'Technical Journal 39(1):205-233 (1960)',
        'doi': '10.1002/j.1538-7305.1960.tb03928.x',
        'used_for': 'equilibrium segregation coefficients k0 '
                    '(B 0.8, P 0.35, Al 2e-3, Fe 8e-6, C 0.07 '
                    'approx., O ~1.25)',
        'status': 'B/P/Al/Fe/C verified against the commonly '
                  'reproduced table; O and Ca to verify'},
    '[HOP85]': {
        'citation': 'R. H. Hopkins, A. Rohatgi, "Impurity effects in '
                    'silicon for high efficiency solar cells", '
                    'J. Cryst. Growth 75(1):67-79 (1986); and the '
                    'Westinghouse/JPL impurity studies (Davis et al., '
                    'IEEE TED 27(4):677-687, 1980)',
        'doi': '10.1016/0022-0248(86)90226-5',
        'used_for': 'PV tolerance thresholds per impurity; Ca and '
                    'Ti k_eff',
        'status': 'to verify (Ca k_eff ~ 4e-4 quoted from memory)'},
    '[SAF12]': {
        'citation': 'J. Safarian, G. Tranell, M. Tangstad, "Processes '
                    'for Upgrading Metallurgical Grade Silicon to '
                    'Solar Grade Silicon", Energy Procedia 20:88-97 '
                    '(2012)',
        'doi': '10.1016/j.egypro.2012.03.011',
        'used_for': 'metallurgical route overview: slag, leaching, '
                    'vacuum, plasma, directional solidification',
        'status': 'verified (open access)'},
    '[CEC12]': {
        'citation': 'B. Ceccaroli, O. Lohne, "Solar Grade Silicon '
                    'Feedstock", in Handbook of Photovoltaic Science '
                    'and Engineering, 2nd ed., Wiley (2011), ch. 5',
        'doi': '10.1002/9780470974704.ch5',
        'used_for': 'MG-Si typical impurity levels; Siemens and FBR '
                    'energy figures; grade definitions',
        'status': 'verified (widely reproduced tables); exact page '
                  'numbers to verify'},
    '[DEL12]': {
        'citation': 'Y. Delannoy, "Purification of silicon for '
                    'photovoltaic applications", J. Cryst. Growth '
                    '360:61-67 (2012)',
        'doi': '10.1016/j.jcrysgro.2011.12.006',
        'used_for': 'metallurgical (open) route to SoG-Si: '
                    'segregation, evaporation, plasma B removal; '
                    'the statement that B/P are the limiting '
                    'impurities',
        'status': 'verified'},
    '[PFA66]': {
        'citation': 'W. G. Pfann, "Zone Melting", 2nd ed., Wiley '
                    '(1966)',
        'doi': '',
        'used_for': 'single-pass zone-refining equation '
                    'C(x)/C0 = 1 − (1−k) exp(−k x / l) and the '
                    'multipass numeric scheme',
        'status': 'verified (textbook)'},
    '[SCH42]': {
        'citation': 'E. Scheil, "Bemerkungen zur Schichtkristall-'
                    'bildung", Z. Metallkunde 34:70-72 (1942)',
        'doi': '',
        'used_for': 'Scheil (non-equilibrium lever) segregation '
                    'equation',
        'status': 'verified (textbook)'},
    '[BCF52]': {
        'citation': 'J. A. Burton, R. C. Prim, W. P. Slichter, "The '
                    'Distribution of Solute in Crystals Grown from '
                    'the Melt. Part I", J. Chem. Phys. 21:1987 (1953)',
        'doi': '10.1063/1.1698728',
        'used_for': 'k_eff vs k0 (growth-rate / boundary-layer '
                    'correction) — why k_eff > k0 at real pull rates',
        'status': 'verified'},
    '[ZHE11]': {
        'citation': 'S. Zheng, T. A. Engh, M. Tangstad, X. Luo, '
                    '"Separation of Phosphorus from Silicon by '
                    'Induction Vacuum Refining", Sep. Purif. Technol. '
                    '82:128-137 (2011)',
        'doi': '10.1016/j.seppur.2011.09.001',
        'used_for': 'P evaporation coefficient / mass-transfer '
                    'model under vacuum (first-order in [P])',
        'status': 'verified; coefficient value to verify'},
    '[ALE15]': {
        'citation': 'N. Nakamura, H. Baba, Y. Sakaguchi, Y. Kato, '
                    '"Boron Removal in Molten Silicon by a Steam-Added '
                    'Plasma Melting Method", Mater. Trans. 45(3):'
                    '858-864 (2004) (Kawasaki Steel/NEDO process)',
        'doi': '10.2320/matertrans.45.858',
        'used_for': 'B removal via H2/H2O plasma (BOH / HBO species) '
                    '— first-order kinetics prior',
        'status': 'to verify (authors/year from memory)'},
    '[SCH19]': {
        'citation': 'Handbook: "Polysilicon — Siemens process" as '
                    'summarised in Ceccaroli/Lohne [CEC12] and in '
                    'A. Ramos et al., "Deposition reactors for solar '
                    'grade silicon: A comparative thermal analysis of '
                    'a Siemens reactor and a fluidized bed reactor", '
                    'J. Cryst. Growth 431:1-9 (2015)',
        'doi': '10.1016/j.jcrysgro.2015.08.023',
        'used_for': 'Siemens vs FBR energy (50–100 vs 10–30 kWh/kg)',
        'status': 'verified'},
    '[SEMI]': {
        'citation': 'SEMI PV017 / SEMI PV049 standards for '
                    'photovoltaic-grade silicon feedstock '
                    '(impurity limits per grade)',
        'doi': '',
        'used_for': 'SoG-Si B/P ppm limits (~0.3 / ~1 ppmw tier)',
        'status': 'to verify exact grade tiers'},
}


def _cite(*tags):
    return json.dumps([{'tag': t, **CITATIONS[t]} for t in tags])


# ------------------------------------------------------------------
# Rows
# ------------------------------------------------------------------
class SiliconGrade(treeObject):
    """One rung of the silicon purity ladder as a ROW."""

    @treeObjectInit
    def __init__(self, name='', display_name='', order=0,
                 purity_min_fraction=0.0, purity_n_count='',
                 dominant_impurities_json='{}', typical_use='',
                 openness='open-research', openness_reasoning='',
                 techtree_node='', citations='[]', notes='',
                 is_prior=True, manager=None):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.purity_min_fraction = purity_min_fraction
        self.purity_n_count = purity_n_count
        self.dominant_impurities_json = dominant_impurities_json
        self.typical_use = typical_use
        self.openness = openness
        self.openness_reasoning = openness_reasoning
        self.techtree_node = techtree_node
        self.citations = citations
        self.notes = notes
        self.is_prior = is_prior


class RefinementStep(treeObject):
    """One unit operation that moves silicon up the ladder; its
    model kind + parameters are DATA so route_simulation can push
    an impurity vector through it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', order=0,
                 chemistry='', inputs_json='[]', outputs_json='[]',
                 purity_in_grade='', purity_out_grade='',
                 temperature_c=0.0, pressure_pa=101325.0,
                 energy_kwh_per_kg=0.0, energy_range_json='[0, 0]',
                 model_kind='none', model_params_json='{}',
                 openness='open-research', openness_reasoning='',
                 equipment_class='', citations='[]', notes='',
                 confidence='prior', is_prior=True, manager=None):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.chemistry = chemistry
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.purity_in_grade = purity_in_grade
        self.purity_out_grade = purity_out_grade
        self.temperature_c = temperature_c
        self.pressure_pa = pressure_pa
        self.energy_kwh_per_kg = energy_kwh_per_kg
        self.energy_range_json = energy_range_json
        self.model_kind = model_kind
        self.model_params_json = model_params_json
        self.openness = openness
        self.openness_reasoning = openness_reasoning
        self.equipment_class = equipment_class
        self.citations = citations
        self.notes = notes
        self.confidence = confidence
        self.is_prior = is_prior


class RefinementRoute(treeObject):
    """An ordered chain of RefinementStep names toward a target
    grade, with the openness verdict and — for novel-needed routes
    — the candidate directions as labelled PRIOR entries."""

    @treeObjectInit
    def __init__(self, name='', display_name='', order=0,
                 steps_json='[]', feed_grade='mg-si', target_grade='',
                 openness='open-research', reasoning='',
                 novel_directions_json='[]', citations='[]',
                 notes='', is_prior=True, manager=None):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.steps_json = steps_json
        self.feed_grade = feed_grade
        self.target_grade = target_grade
        self.openness = openness
        self.reasoning = reasoning
        self.novel_directions_json = novel_directions_json
        self.citations = citations
        self.notes = notes
        self.is_prior = is_prior


# ------------------------------------------------------------------
# Seeds — grades
# ------------------------------------------------------------------
def _imp(typ_lo, typ_hi, matters_pv, matters_semi, why):
    return {'typical_ppmw': [typ_lo, typ_hi], 'matters_for_pv': matters_pv,
            'matters_for_semiconductor': matters_semi, 'why': why}


#: Typical MG-Si feed (ppmw) — [CEC12] table of MG-Si analyses
#: (Fe 1000–5000, Al 500–3000, Ca 100–1000, B 10–50, P 20–50,
#: C 100–1000, O 100–400); the defaults are mid-range.
DEFAULT_MG_FEED_PPM = {'B': 40.0, 'P': 30.0, 'Fe': 2000.0,
                      'Al': 1500.0, 'Ca': 500.0, 'C': 200.0,
                      'O': 100.0}

#: Grade thresholds (ppmw, max) — B and P DECIDE the grade
#: (segregation-resistant); metals are listed so route_simulation
#: can show they are NOT the bottleneck after solidification.
GRADE_LIMITS_PPM = {
    'mg-si': {'B': 100.0, 'P': 100.0, 'Fe': 10000.0, 'Al': 5000.0,
              'Ca': 2000.0, 'C': 2000.0, 'O': 1000.0},
    'umg-si': {'B': 5.0, 'P': 5.0, 'Fe': 10.0, 'Al': 10.0,
               'Ca': 10.0, 'C': 50.0, 'O': 50.0},
    # SoG: SEMI PV017 tier-III-ish; B ≤ 0.3, P ≤ 1 ppmw [SEMI] (to
    # verify tier), metals ≤ 0.1 (to verify)
    'sog-si': {'B': 0.3, 'P': 1.0, 'Fe': 0.1, 'Al': 0.1, 'Ca': 0.1,
               'C': 10.0, 'O': 20.0},
    # EG: ppb-level B/P (≤ 0.001 ppmw ≈ 1 ppbw) [CEC12]; C/O are
    # crystal-growth quantities, not feedstock ones
    'eg-si': {'B': 0.001, 'P': 0.001, 'Fe': 0.001, 'Al': 0.001,
              'Ca': 0.001, 'C': 1.0, 'O': 20.0},
}

SEED_SILICON_GRADES = [
    {
        'name': 'mg-si', 'display_name': 'Metallurgical-grade Si (MG-Si)',
        'order': 0, 'purity_min_fraction': 0.98, 'purity_n_count': '2N',
        'dominant_impurities_json': json.dumps({
            'Fe': _imp(1000, 5000, False, False,
                       'k_eff 8e-6: gone after one directional pass'),
            'Al': _imp(500, 3000, False, False,
                       'k_eff 2e-3: gone after one directional pass'),
            'Ca': _imp(100, 1000, False, False,
                       'slag- and leach-removable; k_eff small'),
            'B': _imp(10, 50, True, True,
                      'k_eff 0.8 — segregation-RESISTANT; sets the '
                      'p-type base resistivity of a PV wafer'),
            'P': _imp(20, 50, True, True,
                      'k_eff 0.35 — segregation-resistant; '
                      'compensates B, ruins resistivity control'),
            'C': _imp(100, 1000, True, False,
                      'SiC precipitates → shunts in PV; k_eff 0.07'),
            'O': _imp(100, 400, False, False,
                      'k_eff ~1.25 (goes INTO the solid); PV-'
                      'relevant only via B–O LID, semiconductor '
                      'wants controlled Oi from CZ, not feed'),
        }),
        'typical_use': 'Aluminium alloys, silicones; feed to every '
                       'refinement route',
        'openness': 'open-research',
        'openness_reasoning': 'Carbothermic arc-furnace reduction is '
                              '19th-century open metallurgy.',
        'techtree_node': 'silicon-supply',
        'citations': _cite('[CEC12]', '[SAF12]'),
        'notes': 'Typical analyses per [CEC12]; DEFAULT_MG_FEED_PPM '
                 'is the mid-range used by refinement_report.',
    },
    {
        'name': 'umg-si',
        'display_name': 'Upgraded metallurgical Si (UMG-Si)',
        'order': 1, 'purity_min_fraction': 0.9999,
        'purity_n_count': '4N–5N',
        'dominant_impurities_json': json.dumps({
            'B': _imp(1, 5, True, True, 'not moved by slag/leach '
                      'alone; slag treatment gets ×3–10 at best'),
            'P': _imp(1, 5, True, True, 'not moved by slag/leach'),
            'Fe': _imp(1, 10, True, False, 'leach residue at grain '
                       'boundaries'),
            'Al': _imp(1, 10, True, False, 'leach residue'),
            'Ca': _imp(1, 10, False, False, 'leach residue'),
            'C': _imp(20, 50, True, False, 'SiC from the furnace'),
            'O': _imp(20, 50, False, False, 'oxide skins'),
        }),
        'typical_use': 'Compensated PV feedstock after further DS; '
                       'blending stock',
        'openness': 'open-research',
        'openness_reasoning': 'Slag + acid leaching documented in '
                              'open metallurgy [SAF12]; several '
                              'defunct/live companies (Elkem, '
                              'Ferroatlantica) hold process patents '
                              'on specifics, chemistry is open.',
        'techtree_node': 'silicon-supply',
        'citations': _cite('[SAF12]', '[CEC12]'),
        'notes': '',
    },
    {
        'name': 'sog-si', 'display_name': 'Solar-grade Si (SoG-Si)',
        'order': 2, 'purity_min_fraction': 0.999999,
        'purity_n_count': '6N–7N',
        'dominant_impurities_json': json.dumps({
            'B': _imp(0.1, 0.3, True, True, 'THE limiter — sets '
                      'base resistivity ~1 Ω·cm at 0.3 ppmw'),
            'P': _imp(0.3, 1.0, True, True, 'compensation; '
                      'vacuum-evaporable so easier than B'),
            'Fe': _imp(0.01, 0.1, True, False, 'lifetime killer '
                       'above ~0.1 ppmw; DS handles it'),
            'Al': _imp(0.01, 0.1, False, False, ''),
            'Ca': _imp(0.01, 0.1, False, False, ''),
            'C': _imp(1, 10, True, False, 'SiC inclusions'),
            'O': _imp(5, 20, True, False, 'B–O light-induced '
                      'degradation'),
        }),
        'typical_use': 'PV wafers (mc-Si / mono-like DS; CZ mono '
                       'with tighter B/P)',
        'openness': 'open-research',
        'openness_reasoning': 'Both the chemical (Siemens) and the '
                              'metallurgical routes to this grade are '
                              'documented end-to-end in open '
                              'literature [DEL12][SAF12][CEC12]; the '
                              'metallurgical one needs only arc / '
                              'induction furnaces, acids, and vacuum '
                              '— an open-source implementation is '
                              'plausible.',
        'techtree_node': 'silicon-supply-pv-grade',
        'citations': _cite('[DEL12]', '[SAF12]', '[CEC12]', '[SEMI]'),
        'notes': 'Limits per SEMI PV017 tiers (to verify exact tier).',
    },
    {
        'name': 'eg-si',
        'display_name': 'Electronic-grade Si (EG-Si)',
        'order': 3, 'purity_min_fraction': 0.999999999,
        'purity_n_count': '9N–11N',
        'dominant_impurities_json': json.dumps({
            'B': _imp(0.0001, 0.001, True, True, 'ppb: only '
                      'chlorosilane distillation reaches this'),
            'P': _imp(0.0001, 0.001, True, True, 'ppb'),
            'Fe': _imp(0.0001, 0.001, True, True, 'ppb; DS + '
                       'clean handling'),
            'Al': _imp(0.0001, 0.001, False, True, ''),
            'Ca': _imp(0.0001, 0.001, False, True, ''),
            'C': _imp(0.01, 1.0, False, True, 'substitutional Cs '
                      'from the CVD/CZ step, not the feed'),
            'O': _imp(5, 20, False, True, 'interstitial Oi from the '
                      'CZ crucible — a growth quantity'),
        }),
        'typical_use': 'CZ / FZ wafers for ICs; the sifet device '
                       'substrate',
        'openness': 'novel-needed',
        'openness_reasoning': 'The only proven route is Siemens '
                              'chlorosilane distillation + CVD, whose '
                              'chemistry is open but whose 11N '
                              'process control (column design, '
                              'ppb analytics, reactor purity) is '
                              'industrial know-how; NO metallurgical '
                              'route is documented past ~7N in B/P '
                              'because k_eff(B)=0.8 makes '
                              'solidification useless for B. '
                              'Candidate directions live in '
                              'RefinementRoute eg-novel-route as '
                              'PRIOR rows (plan §2 decision 5).',
        'techtree_node': 'silicon-supply-semiconductor-grade',
        'citations': _cite('[CEC12]', '[TRU60]'),
        'notes': '',
    },
]

# ------------------------------------------------------------------
# Seeds — steps
# ------------------------------------------------------------------
#: Equilibrium segregation coefficients k0 (solid/liquid) [TRU60]
#: with confidence labels; k_eff at DS rates is a little larger
#: (BPS [BCF52]) — the DS step uses these as k_eff priors.
SEGREGATION_K = {
    'B': {'k': 0.8, 'confidence': 'high', 'source': '[TRU60]'},
    'P': {'k': 0.35, 'confidence': 'high', 'source': '[TRU60]'},
    'Fe': {'k': 8e-6, 'confidence': 'high', 'source': '[TRU60]'},
    'Al': {'k': 2e-3, 'confidence': 'high', 'source': '[TRU60]'},
    'Ca': {'k': 4e-4, 'confidence': 'low — to verify', 'source': '[HOP85]'},
    'C': {'k': 0.07, 'confidence': 'medium', 'source': '[TRU60]'},
    'O': {'k': 1.25, 'confidence': 'medium (values 0.25–1.25 '
                     'reported; 1.25 = Yatsurugi 1973)',
          'source': '[TRU60]'},
}


def _k_json():
    return {imp: v['k'] for imp, v in SEGREGATION_K.items()}


def _step(name, display_name, order, chemistry, inputs, outputs,
          grade_in, grade_out, t_c, p_pa, e_kwh, e_range, model_kind,
          model_params, openness, why, equipment, cites, notes='',
          confidence='prior'):
    return {
        'name': name, 'display_name': display_name, 'order': order,
        'chemistry': chemistry,
        'inputs_json': json.dumps(inputs),
        'outputs_json': json.dumps(outputs),
        'purity_in_grade': grade_in, 'purity_out_grade': grade_out,
        'temperature_c': t_c, 'pressure_pa': p_pa,
        'energy_kwh_per_kg': e_kwh,
        'energy_range_json': json.dumps(list(e_range)),
        'model_kind': model_kind,
        'model_params_json': json.dumps(model_params),
        'openness': openness, 'openness_reasoning': why,
        'equipment_class': equipment,
        'citations': _cite(*cites), 'notes': notes,
        'confidence': confidence,
    }


SEED_REFINEMENT_STEPS = [
    _step('carbothermic-reduction', 'Carbothermic reduction (arc furnace)',
          0, 'SiO2 + 2 C → Si + 2 CO  (via SiC / SiO intermediates)',
          ['quartz (lumpy, low-B/P)', 'carbon (coal/charcoal/woodchips)'],
          ['MG-Si (98–99 %)', 'CO off-gas', 'silica fume'],
          'quartz', 'mg-si', 1900.0, 101325.0, 12.0, (11.0, 13.0),
          # impurities come FROM the raw materials; modelled as a
          # fixed output vector (the feed of every route)
          'none', {'output_ppm': DEFAULT_MG_FEED_PPM,
                   'note': 'output set by raw-material purity, not '
                           'by a removal model'},
          'open-research', 'Submerged-arc furnace metallurgy is '
          'open and century-old; raw-material selection (low-B '
          'quartz) is the only lever.', 'arc-furnace',
          ('[CEC12]', '[SAF12]'), confidence='high'),
    _step('slag-treatment', 'Slag treatment (CaO–SiO2 slag, B removal)',
          1, '[B]_Si + 3/2 O (slag) → BO1.5 (slag);  L_B = (B)/[B] ~ 2–4',
          ['MG-Si melt', 'CaO–SiO2 (–CaF2) slag, mass ratio ~1:1'],
          ['Si melt (B ×1/2–1/4)', 'spent slag'],
          'mg-si', 'mg-si', 1550.0, 101325.0, 1.5, (1.0, 3.0),
          # partition: C_out = C_in / (1 + L·m_slag/m_si)
          'partition', {'partition_ratio': {'B': 2.5, 'Ca': 5.0,
                                            'Al': 3.0},
                        'slag_to_si_mass_ratio': 1.0,
                        'note': 'L_B 2–4 [SAF12]; one stage'},
          'open-research', 'Slag partition of B is open ladle '
          'metallurgy [SAF12]; the low L_B is why it is a pre-step, '
          'not a route.', 'induction-furnace', ('[SAF12]',),
          confidence='medium'),
    _step('acid-leaching', 'Acid leaching (HCl / HF, crushed Si)',
          2, 'Fe/Al/Ca intermetallics at grain boundaries dissolve; '
          'Si matrix is inert to HCl (HF attacks the oxide skin)',
          ['crushed MG-Si (<0.5 mm)', 'HCl 4–6 M (+ dilute HF)'],
          ['UMG-Si powder', 'metal-chloride liquor'],
          'mg-si', 'umg-si', 60.0, 101325.0, 0.5, (0.3, 1.0),
          # fraction remaining per impurity (segregated-to-GB metals
          # leach; B/P in solid solution do not)
          'fraction-remaining', {'remaining': {'Fe': 0.01, 'Al': 0.02,
                                               'Ca': 0.02, 'B': 1.0,
                                               'P': 1.0, 'C': 0.8,
                                               'O': 0.8}},
          'open-research', 'Documented since the 1970s (Dietl); '
          'removal of 90–99 % metals is routinely reported [SAF12].',
          'leach-tank', ('[SAF12]', '[CEC12]'), confidence='medium'),
    _step('directional-solidification',
          'Directional solidification (Scheil segregation)', 3,
          'C_s = k_eff · C_0 · (1 − f_s)^(k_eff − 1);  crop the last '
          '(1 − fs_cut) of the ingot',
          ['Si melt'], ['DS ingot (product fraction fs_cut)',
                        'impurity-rich top crop'],
          'umg-si', 'sog-si', 1500.0, 101325.0, 10.0, (8.0, 15.0),
          'scheil', {'k_eff': _k_json(),
                     'k_source': SEGREGATION_K,
                     'fs_cut': REFINEMENT_KNOBS['fs_cut']},
          'open-research', 'Scheil/BPS segregation is textbook; DS '
          'furnaces are commodity PV equipment [DEL12].',
          'ds-furnace', ('[SCH42]', '[TRU60]', '[BCF52]', '[DEL12]'),
          notes='k_eff for O > 1 means O ENRICHES the solid — '
                'stated, not hidden.', confidence='high'),
    _step('vacuum-refining', 'Vacuum refining (P evaporation)', 4,
          'P(l, in Si) → P(g) / P2(g) at 1e-1–1 Pa;  first-order: '
          'dC/dt = −(A/V) · k_evap · C',
          ['Si melt'], ['Si melt (P reduced)', 'P-rich condensate'],
          'umg-si', 'sog-si', 1550.0, 0.5, 6.0, (4.0, 10.0),
          'evaporation', {'coefficient_m_per_s': {'P': 1e-4,
                                                  'Al': 1e-5,
                                                  'Ca': 3e-5,
                                                  'B': 0.0, 'Fe': 0.0,
                                                  'C': 0.0, 'O': 5e-5},
                          'floor_ppm': {'P': 0.1, 'O': 5.0},
                          'o_note': 'O leaves as SiO(g) under vacuum '
                                    '(the reason DS ingots carry '
                                    '5–20 ppmw O despite k_eff(O) > '
                                    '1); coefficient PRIOR, floor = '
                                    'crucible re-supply',
                          'note': 'k_evap(P) ~ 1e-5–1e-4 m/s at '
                                  '1550 °C / <1 Pa [ZHE11] (to verify '
                                  'magnitude); floor 0.1 ppmw PRIOR = '
                                  'the lowest P reported, set by '
                                  'Si co-evaporation / back-pressure',
                          'time_s': REFINEMENT_KNOBS['evaporation_time_s'],
                          'area_over_volume_per_m':
                              REFINEMENT_KNOBS['area_over_volume_per_m']},
          'open-research', 'Induction vacuum refining of P is '
          'published with kinetics [ZHE11]; B does NOT evaporate '
          '(vapour pressure too low) — stated.', 'vacuum-induction-furnace',
          ('[ZHE11]', '[SAF12]'), confidence='prior'),
    _step('plasma-refining', 'Plasma refining (H2/H2O plasma, B removal)',
          5, '[B]_Si + H2O(plasma) → HBO(g) / BOH species;  first-order '
          'in [B]', ['Si melt', 'Ar–H2–H2O plasma torch'],
          ['Si melt (B reduced)', 'off-gas'],
          'umg-si', 'sog-si', 1550.0, 101325.0, 8.0, (5.0, 15.0),
          'evaporation', {'coefficient_m_per_s': {'B': 1e-4, 'P': 0.0,
                                                  'Fe': 0.0, 'Al': 0.0,
                                                  'Ca': 0.0, 'C': 5e-6,
                                                  'O': 0.0},
                          'floor_ppm': {'B': 0.1},
                          'note': 'PRIOR: B removal 10 → ~0.1 ppmw in '
                                  '~1–2 h reported for the NEDO '
                                  'steam-plasma process [ALE15]; '
                                  'coefficient back-fitted ((A/V)k t '
                                  '≈ 7 at A/V 10, 2 h), to verify. '
                                  'floor_ppm 0.1 = the reported '
                                  'endpoint (B re-uptake from the '
                                  'refractory / back-reaction) — the '
                                  'unknown that novel direction (c) '
                                  'must measure',
                          'time_s': REFINEMENT_KNOBS['evaporation_time_s'],
                          'area_over_volume_per_m':
                              REFINEMENT_KNOBS['area_over_volume_per_m']},
          'open-research', 'Published chemistry and kinetics; '
          'industrial versions (Kawasaki/NEDO, Photosil) were '
          'proprietary but the papers document the physics enough '
          'for an open torch — needs experimental proof at scale.',
          'plasma-torch-furnace', ('[ALE15]', '[DEL12]'),
          confidence='prior'),
    _step('siemens-tcs', 'Siemens process (TCS distillation + CVD)', 6,
          'Si + 3 HCl → SiHCl3 + H2 (300 °C, FBR);  distillation;  '
          'SiHCl3 + H2 → Si + 3 HCl on hot rods (1100 °C)',
          ['MG-Si', 'HCl', 'H2'], ['polysilicon rods (9N–11N)',
                                  'SiCl4 by-product'],
          'mg-si', 'eg-si', 1100.0, 101325.0, 75.0, (50.0, 100.0),
          # each impurity: fraction passing the distillation train
          'distillation-split', {'split': {'B': 1e-6, 'P': 1e-6,
                                           'Fe': 1e-7, 'Al': 1e-7,
                                           'Ca': 1e-7, 'C': 1e-3,
                                           'O': 1e-3},
                                 'note': 'B (as BCl3, bp 12 °C) and P '
                                         '(PCl3, bp 76 °C) vs TCS bp '
                                         '32 °C — multi-column '
                                         'separation; splits are '
                                         'PRIORS for 11N output'},
          'industrial-proprietary', 'Chemistry is open (1950s '
          'Siemens patents expired) but reaching 11N is column '
          'design, ppb analytics and reactor purity know-how held '
          'by ~10 firms; an open-source 6N–7N Siemens is plausible, '
          '11N is not documented openly.', 'cvd-reactor',
          ('[CEC12]', '[SCH19]'), confidence='medium'),
    _step('fbr-silane', 'Fluidised-bed silane (SiH4) deposition', 7,
          '4 SiHCl3 → SiH4 + 3 SiCl4 (redistribution);  SiH4 → Si + '
          '2 H2 on seed granules (650 °C)',
          ['SiHCl3 / SiH4', 'seed granules'],
          ['granular polysilicon (8N–10N)', 'H2'],
          'mg-si', 'eg-si', 650.0, 101325.0, 20.0, (10.0, 30.0),
          'distillation-split', {'split': {'B': 1e-5, 'P': 1e-5,
                                           'Fe': 1e-6, 'Al': 1e-6,
                                           'Ca': 1e-6, 'C': 1e-3,
                                           'O': 1e-3},
                                 'note': 'PRIOR; granules carry more '
                                         'surface contamination than '
                                         'rods'},
          'industrial-proprietary', 'Same argument as Siemens with '
          'fewer practitioners (REC, GCL); lower energy is the open '
          'part [SCH19].', 'fbr', ('[SCH19]', '[CEC12]'),
          confidence='prior'),
    _step('zone-refining', 'Zone refining (multi-pass, Pfann)', 8,
          'single pass: C(x)/C0 = 1 − (1−k) exp(−k x / l);  N passes '
          'numeric (Pfann)', ['Si rod'], ['Si rod (impurities swept '
                                         'to one end)', 'crop end'],
          'sog-si', 'eg-si', 1420.0, 1e-3, 30.0, (20.0, 60.0),
          'pfann-multipass', {'k_eff': _k_json(),
                              'passes': REFINEMENT_KNOBS['passes'],
                              'zone_fraction':
                                  REFINEMENT_KNOBS['zone_fraction'],
                              'note': 'B with k=0.8: ~N·(1−k)·l/L '
                                      'per pass — hopeless for B'},
          'open-research', 'Pfann zone melting is textbook; an FZ '
          'rig is open hardware in principle — but the model itself '
          'shows it cannot move B.', 'fz-rig', ('[PFA66]', '[TRU60]'),
          confidence='high'),
    _step('czochralski-growth', 'Czochralski growth', 9,
          'Scheil along the pulled boule (k_eff at pull-rate, BPS); '
          'Oi from the quartz crucible', ['poly-Si charge', 'quartz '
                                          'crucible', 'seed'],
          ['CZ boule', 'tang end'],
          'sog-si', 'sog-si', 1420.0, 5000.0, 40.0, (30.0, 60.0),
          'scheil', {'k_eff': _k_json(), 'fs_cut': 0.85,
                     'oxygen_pickup_ppm': 10.0},
          'open-research', 'Textbook; the crucible ADDS O, so it is '
          'a shaping step, not a purification step for O.',
          'cz-puller', ('[BCF52]', '[TRU60]'), confidence='high'),
    _step('float-zone-growth', 'Float-zone growth', 10,
          'Single crucible-free molten-zone pass (Pfann N=1) — no '
          'O pickup', ['poly rod (EG or SoG)', 'seed'],
          ['FZ boule (low O, low C)'],
          'eg-si', 'eg-si', 1420.0, 1e-3, 35.0, (25.0, 60.0),
          'pfann-multipass', {'k_eff': _k_json(), 'passes': 1,
                              'zone_fraction': 0.1},
          'open-research', 'Textbook; RF-heated FZ rigs are '
          'documented in the open (Keck & Golay 1953).', 'fz-rig',
          ('[PFA66]',), confidence='high'),
]

# ------------------------------------------------------------------
# Seeds — routes
# ------------------------------------------------------------------
_NOVEL = [
    {
        'name': 'multipass-fz-on-sog',
        'label': 'PRIOR (a): multi-pass float-zone on SoG feed',
        'what_would_need_proving': 'That N zone passes on a 6N–7N '
        'rod reach ppb B — the bounding equation says NO for B '
        '(k=0.8) unless N ≫ 100; P (k=0.35) and metals do reach '
        'it. Proof = measured B vs N on a real rig.',
        'bounding_equation': 'Pfann single pass C(x)/C0 = 1 − (1−k)'
                             'exp(−k x/l); ultimate distribution '
                             'C(x) = A e^{Bx}, B from k = B l/(e^{Bl}−1)',
        'model_kind': 'pfann-multipass', 'openness': 'novel-needed',
        'verdict_from_model': 'closes P and metals, NOT B',
    },
    {
        'name': 'molten-salt-electrorefining',
        'label': 'PRIOR (b): molten-salt electrorefining (three-layer '
                 'or CaCl2/fluoride)',
        'what_would_need_proving': 'Anodic dissolution of Si with '
        'B/P left in the anode residue or electrolyte at ppb '
        'selectivity; open papers show 4N→6N, not 9N+. Proof = '
        'B/P in cathode deposit vs current density and electrolyte '
        'purity (electrolyte itself must be ppb-clean).',
        'bounding_equation': 'Nernst separation: ΔE = (RT/nF) ln '
                             '(a_B/a_Si); Faradaic selectivity ~ '
                             'exp(nFΔE/RT) — bounded by electrolyte '
                             'impurity background',
        'model_kind': 'none', 'openness': 'novel-needed',
        'verdict_from_model': 'unbounded on paper, unproven past 6N',
    },
    {
        'name': 'plasma-vacuum-fz-hybrid',
        'label': 'PRIOR (c): plasma (B) + vacuum (P) + multi-pass FZ '
                 '(metals) hybrid',
        'what_would_need_proving': 'That first-order plasma B removal '
        'keeps its rate constant down to ppb (it slows as the '
        'back-reaction / B re-uptake from the refractory sets a '
        'floor) — the floor, not the rate, is the unknown. Proof = '
        'B floor vs torch chemistry and crucible material.',
        'bounding_equation': 'C(t) = C_floor + (C0 − C_floor) '
                             'exp(−(A/V) k_evap t); need C_floor ≤ '
                             '1 ppbw',
        'model_kind': 'evaporation', 'openness': 'novel-needed',
        'verdict_from_model': 'reaches the target only if the floor '
                              'is below 1 ppbw — unmeasured',
    },
]

SEED_REFINEMENT_ROUTES = [
    {
        'name': 'pv-open-route',
        'display_name': 'PV (SoG) metallurgical open route',
        'order': 0,
        'steps_json': json.dumps(['carbothermic-reduction',
                                  'slag-treatment', 'acid-leaching',
                                  'directional-solidification',
                                  'directional-solidification',
                                  'vacuum-refining', 'plasma-refining']),
        'feed_grade': 'mg-si', 'target_grade': 'sog-si',
        'openness': 'open-research',
        'reasoning': 'Every step is documented in the open '
                     'literature with kinetics or partition data: '
                     'arc reduction and slag/leach [SAF12], '
                     'directional solidification [DEL12], vacuum P '
                     'evaporation [ZHE11], plasma B removal [ALE15]; '
                     'the complete metallurgical chain to SoG is '
                     'reviewed in [CEC12] and [DEL12]. The vacuum '
                     'and plasma steps are OPTIONAL and carry '
                     'PRIOR coefficients; without them the route '
                     'stalls on B/P at UMG level (the simulation '
                     'shows this — B/P decide).',
        'novel_directions_json': '[]',
        'citations': _cite('[SAF12]', '[CEC12]', '[DEL12]'),
        'notes': 'Steps 4–5: DS twice (second pass on the product '
                 'crop).',
    },
    {
        'name': 'siemens-route',
        'display_name': 'Siemens chemical route (TCS)',
        'order': 1,
        'steps_json': json.dumps(['carbothermic-reduction',
                                  'siemens-tcs', 'czochralski-growth']),
        'feed_grade': 'mg-si', 'target_grade': 'eg-si',
        'openness': 'industrial-proprietary',
        'reasoning': 'Chemistry fully open (patents expired) and '
                     'the energy/throughput figures published '
                     '[SCH19]; the 11N endpoint depends on '
                     'distillation-column design and ppb analytics '
                     'that are practised, not published — an open '
                     'build would plausibly reach SoG, and EG only '
                     'with unknown effort.',
        'novel_directions_json': '[]',
        'citations': _cite('[CEC12]', '[SCH19]'),
        'notes': '',
    },
    {
        'name': 'eg-novel-route',
        'display_name': 'Semiconductor (EG) — open route NOT known',
        'order': 2,
        'steps_json': json.dumps(['carbothermic-reduction',
                                  'slag-treatment', 'acid-leaching',
                                  'directional-solidification',
                                  'vacuum-refining', 'plasma-refining',
                                  'zone-refining', 'float-zone-growth']),
        'feed_grade': 'mg-si', 'target_grade': 'eg-si',
        'openness': 'novel-needed',
        'reasoning': 'No open, documented route reaches 9N+ in B/P. '
                     'Solidification (DS/FZ/CZ) cannot: k_eff(B) = '
                     '0.8 leaves 80 % of B in the solid per pass. '
                     'The candidate directions below are PRIORS — '
                     'none endorsed (plan §2 decision 5 is Dustin\'s).',
        'novel_directions_json': json.dumps(_NOVEL),
        'citations': _cite('[TRU60]', '[PFA66]', '[DEL12]'),
        'notes': 'The steps listed are the best OPEN chain; the '
                 'simulation shows where it stalls.',
    },
]


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
def scheil_pass(c0_ppm, k_eff, fs_grid=None, target_ppm=None,
                fs_cut=None):
    """Scheil profile C_s(f_s) = k C0 (1−f_s)^(k−1) on fs_grid, the
    mean concentration of the product fraction [0, fs_cut], and the
    yield fraction f* below target_ppm (largest f_s with C_s ≤
    target; 0 if none, 1 if all). k > 1 (oxygen) enriches the
    solid and is handled by the same formula."""
    if fs_grid is None:
        fs_grid = [i / 100.0 for i in range(0, 100)]
    fs_cut = REFINEMENT_KNOBS['fs_cut'] if fs_cut is None else fs_cut
    k = max(float(k_eff), 1e-12)
    profile = [(fs, k * c0_ppm * (1.0 - fs) ** (k - 1.0))
               for fs in fs_grid if fs < 1.0]
    # mean over [0, fs_cut]: ∫ k C0 (1−f)^(k−1) df = C0 (1 − (1−fs)^k)
    mean_product = c0_ppm * (1.0 - (1.0 - fs_cut) ** k) / fs_cut
    yield_below = None
    if target_ppm is not None:
        if k >= 1.0:
            yield_below = 1.0 if k * c0_ppm <= target_ppm else 0.0
        elif k * c0_ppm > target_ppm:
            yield_below = 0.0
        else:
            # k C0 (1−f)^(k−1) = target → f = 1 − (target/(k C0))^(1/(k−1))
            yield_below = min(1.0, 1.0 - (target_ppm / (k * c0_ppm))
                              ** (1.0 / (k - 1.0)))
    return {'k_eff': k, 'c0_ppm': c0_ppm, 'fs_cut': fs_cut,
            'profile': profile, 'mean_product_ppm': mean_product,
            'removal_fraction': 1.0 - mean_product / c0_ppm
            if c0_ppm else 0.0,
            'yield_fraction_below_target': yield_below,
            'equation': 'C_s = k_eff C_0 (1 - f_s)^(k_eff - 1)'}


def multipass_zone(c0, k_eff, passes=None, zone_fraction=None,
                   n_cells=200):
    """Numeric Pfann multipass zone refining on a rod of n_cells,
    molten zone = zone_fraction · L. Each pass sweeps the zone from
    x=0 to L; the zone freezes out at concentration k·C_zone per
    cell and swallows the next cell; the last zone length freezes
    by Scheil (normal freezing). Returns the profile after each
    pass, the mean of the product fraction [0, 1 − zone_fraction]
    and whether successive passes are converging."""
    passes = REFINEMENT_KNOBS['passes'] if passes is None else passes
    zf = (REFINEMENT_KNOBS['zone_fraction'] if zone_fraction is None
          else zone_fraction)
    k = max(float(k_eff), 1e-12)
    zl = max(1, int(round(zf * n_cells)))
    rod = [float(c0)] * n_cells
    history = []
    for _ in range(int(passes)):
        zone = sum(rod[:zl])          # solute in the molten zone
        new = []
        for i in range(n_cells - zl):
            cs = k * zone / zl
            new.append(cs)
            zone += rod[i + zl] - cs
        # freeze the last zone by Scheil
        cz = zone / zl
        for j in range(zl):
            fs = j / zl
            new.append(k * cz * (1.0 - fs) ** (k - 1.0)
                       if k < 1 else cz)
        rod = new
        prod = rod[:n_cells - zl]
        history.append(sum(prod) / len(prod))
    converging = (len(history) < 2 or
                  all(history[i + 1] <= history[i] * 1.0001
                      for i in range(len(history) - 1)))
    return {'k_eff': k, 'c0': c0, 'passes': passes,
            'zone_fraction': zf, 'profile': rod,
            'mean_product_per_pass': history,
            'mean_product': history[-1] if history else c0,
            'removal_fraction': (1.0 - history[-1] / c0) if (history
                                                              and c0)
            else 0.0,
            'converging': converging,
            'equation': 'Pfann: C(x)/C0 = 1 - (1-k) exp(-k x / l) '
                        '(single pass), numeric cells for N passes'}


def evaporation_removal(c0, coefficient, time_s, area_over_volume,
                        c_floor=0.0):
    """First-order evaporative (or reactive-gas) removal
    C(t) = C_floor + (C0 − C_floor) exp(−(A/V) k t)."""
    kk = max(0.0, float(coefficient)) * float(area_over_volume)
    c = c_floor + (c0 - c_floor) * math.exp(-kk * time_s)
    return {'c0': c0, 'coefficient': coefficient, 'time_s': time_s,
            'area_over_volume': area_over_volume, 'c_floor': c_floor,
            'c_out': c, 'removal_fraction': (1.0 - c / c0) if c0 else 0.0,
            'equation': 'C(t) = C_floor + (C0 - C_floor) '
                        'exp(-(A/V) k_evap t)'}


# ------------------------------------------------------------------
# Row access + route simulation
# ------------------------------------------------------------------
def _rows(manager, cls):
    tables = getattr(manager, 'objectTables', {}) or {}
    # the live manager keys each table by id (dict) — iterate VALUES
    t = tables.get(cls) or {}
    return list(t.values()) if isinstance(t, dict) else list(t)


def get_row(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', None) == name:
            return r
    return None


def _js(v, default):
    try:
        return json.loads(v) if isinstance(v, str) else (v or default)
    except (TypeError, ValueError):
        return default


def grade_ladder(manager):
    rows = sorted(_rows(manager, 'SiliconGrade'),
                  key=lambda r: getattr(r, 'order', 0))
    return [{'name': r.name, 'display_name': r.display_name,
             'order': r.order, 'purity_n_count': r.purity_n_count,
             'purity_min_fraction': r.purity_min_fraction,
             'limits_ppm': GRADE_LIMITS_PPM.get(r.name, {}),
             'openness': r.openness,
             'techtree_node': getattr(r, 'techtree_node', ''),
             'dominant_impurities':
                 _js(r.dominant_impurities_json, {})}
            for r in rows]


def grade_for(ppm, ladder=None):
    """Highest grade whose EVERY limit is met, plus the impurity
    that blocks the next grade (B and P decide in practice)."""
    order = ['mg-si', 'umg-si', 'sog-si', 'eg-si']
    achieved = None
    blocker = None
    for g in order:
        lim = GRADE_LIMITS_PPM[g]
        fails = {imp: (ppm.get(imp, 0.0), lim[imp]) for imp in lim
                 if ppm.get(imp, 0.0) > lim[imp]}
        if fails:
            # blocker = the worst ratio
            blocker = {'next_grade': g,
                       'impurity': max(fails, key=lambda i: fails[i][0]
                                       / fails[i][1]),
                       'fails': fails}
            break
        achieved = g
    return {'grade': achieved or 'below-mg-si', 'blocker': blocker}


def apply_step(step, ppm_in, knobs):
    """Push an impurity vector through ONE step's model; returns
    {ppm_out, model, prior_flag, detail}."""
    params = _js(step.model_params_json, {})
    kind = step.model_kind
    out = dict(ppm_in)
    detail = {}
    if kind == 'none' and 'output_ppm' in params:
        out = {imp: float(v) for imp, v in params['output_ppm'].items()}
        detail['note'] = params.get('note', '')
    elif kind == 'partition':
        L = params.get('partition_ratio', {})
        m = params.get('slag_to_si_mass_ratio', 1.0)
        for imp in out:
            if imp in L:
                out[imp] = ppm_in[imp] / (1.0 + L[imp] * m)
        detail['equation'] = 'C_out = C_in / (1 + L m_slag/m_si)'
    elif kind == 'fraction-remaining':
        rem = params.get('remaining', {})
        for imp in out:
            out[imp] = ppm_in[imp] * rem.get(imp, 1.0)
    elif kind == 'scheil':
        fs_cut = knobs.get('fs_cut', params.get('fs_cut', 0.9))
        for imp in out:
            k = params.get('k_eff', {}).get(imp)
            if k is None:
                continue
            r = scheil_pass(ppm_in[imp], k, fs_cut=fs_cut)
            out[imp] = r['mean_product_ppm']
            detail[imp] = {'k_eff': k, 'removal': r['removal_fraction']}
        if 'oxygen_pickup_ppm' in params:
            out['O'] = out.get('O', 0.0) + params['oxygen_pickup_ppm']
            detail['O_pickup_ppm'] = params['oxygen_pickup_ppm']
        detail['fs_cut'] = fs_cut
    elif kind == 'pfann-multipass':
        passes = knobs.get('passes', params.get('passes', 3))
        zf = knobs.get('zone_fraction', params.get('zone_fraction', 0.1))
        for imp in out:
            k = params.get('k_eff', {}).get(imp)
            if k is None:
                continue
            r = multipass_zone(ppm_in[imp], k, passes, zf)
            out[imp] = r['mean_product']
            detail[imp] = {'k_eff': k, 'removal': r['removal_fraction']}
        detail.update({'passes': passes, 'zone_fraction': zf})
    elif kind == 'evaporation':
        t = knobs.get('evaporation_time_s', params.get('time_s', 3600.0))
        aov = knobs.get('area_over_volume_per_m',
                        params.get('area_over_volume_per_m', 3.3))
        floors = params.get('floor_ppm', {})
        for imp in out:
            kc = params.get('coefficient_m_per_s', {}).get(imp, 0.0)
            fl = min(floors.get(imp, 0.0), ppm_in[imp])
            r = evaporation_removal(ppm_in[imp], kc, t, aov, c_floor=fl)
            out[imp] = r['c_out']
            detail[imp] = {'coefficient': kc, 'floor_ppm': fl,
                           'removal': r['removal_fraction']}
        detail.update({'time_s': t, 'area_over_volume_per_m': aov})
    elif kind == 'distillation-split':
        split = params.get('split', {})
        for imp in out:
            out[imp] = ppm_in[imp] * split.get(imp, 1.0)
    return {'ppm_out': out, 'model_kind': kind,
            'is_prior': step.confidence in ('prior', 'low'),
            'confidence': step.confidence, 'detail': detail}


def route_openness(steps):
    worst = 'open-research'
    for s in steps:
        if _OPENNESS_RANK.get(s.openness, 0) > _OPENNESS_RANK[worst]:
            worst = s.openness
    return worst


def route_simulation(manager, route_name, feed_ppm_json=None,
                     knobs=None):
    route = get_row(manager, 'RefinementRoute', route_name)
    if route is None:
        return {'ok': False, 'route': route_name,
                'refusal': 'no RefinementRoute row of that name'}
    kn = dict(REFINEMENT_KNOBS)
    kn.update(knobs or {})
    feed = dict(DEFAULT_MG_FEED_PPM)
    if feed_ppm_json:
        feed.update({k: float(v) for k, v in _js(feed_ppm_json, {}).items()})
    names = _js(route.steps_json, [])
    steps = []
    missing = []
    for n in names:
        s = get_row(manager, 'RefinementStep', n)
        (steps if s is not None else missing).append(s or n)
    if missing:
        return {'ok': False, 'route': route_name,
                'refusal': f'missing RefinementStep rows: {missing}'}
    ppm = dict(feed)
    table = []
    energy = 0.0
    priors = []
    for i, s in enumerate(steps):
        r = apply_step(s, ppm, kn)
        energy += float(s.energy_kwh_per_kg)
        if r['is_prior']:
            priors.append(s.name)
        table.append({'index': i, 'step': s.name,
                      'model_kind': s.model_kind,
                      'openness': s.openness,
                      'confidence': s.confidence,
                      'energy_kwh_per_kg': s.energy_kwh_per_kg,
                      'ppm_in': dict(ppm), 'ppm_out': r['ppm_out'],
                      'grade_after': grade_for(r['ppm_out'])['grade'],
                      'detail': r['detail']})
        ppm = r['ppm_out']
    g = grade_for(ppm)
    target = route.target_grade
    reached = (['mg-si', 'umg-si', 'sog-si', 'eg-si'].index(g['grade'])
               >= ['mg-si', 'umg-si', 'sog-si', 'eg-si'].index(target)
               if g['grade'] in GRADE_LIMITS_PPM else False)
    # bottleneck: the impurity with the worst ratio to the TARGET
    tl = GRADE_LIMITS_PPM[target]
    bottleneck = max(tl, key=lambda i: ppm.get(i, 0.0) / tl[i])
    return {
        'ok': True, 'route': route_name, 'target_grade': target,
        'feed_ppm': feed, 'knobs': kn, 'steps': table,
        'final_ppm': ppm, 'grade_achieved': g['grade'],
        'target_reached': reached, 'blocker': g['blocker'],
        'bottleneck_impurity': bottleneck,
        'bottleneck_ratio_to_target': ppm.get(bottleneck, 0.0)
        / tl[bottleneck],
        'energy_total_kwh_per_kg': energy,
        'openness': route_openness(steps),
        'openness_rule': 'route openness = worst step',
        'declared_openness': route.openness,
        # the honest verdict: an all-open chain that does NOT reach
        # its target grade is still a novel-needed problem
        'verdict': (route_openness(steps) if reached
                    else max(route_openness(steps), route.openness,
                             key=lambda o: _OPENNESS_RANK.get(o, 0))),
        'honesty': {'prior_steps': priors,
                    'note': 'steps listed in prior_steps use PRIOR '
                            'coefficients (see each step\'s '
                            'model_params_json.note); the segregation '
                            'k_eff values are cited [TRU60]'},
        'novel_directions': _js(route.novel_directions_json, []),
    }


# ------------------------------------------------------------------
# Graph seeds (cntfet _device_graph shape, source_class
# RefinementRoute) + row builders
# ------------------------------------------------------------------
def _route_graph(kind, description, x_label, y_label, y_type='log',
                 render='lineY'):
    return {
        'name': f'si-refinement-{kind}',
        'description': description + ' — data: /api/sifet/refinement/'
                       '{route}/points?curve=' + kind,
        'source_class': 'RefinementRoute',
        'definition': json.dumps({'graphConfig': {
            'renderStyle': render,
            'xDimension': 'x',
            'yDimensions': ['y'],
            'seriesDimension': 'series',
            'styleDimension': 'style',
            'seriesColors': [],
            'options': {'showLegend': True, 'showGrid': True,
                        'xLabel': x_label, 'yLabel': y_label,
                        'yType': y_type},
            'aggregation': None,
        }}),
    }


SEED_SI_REFINEMENT_GRAPHS = [
    _route_graph('impurity-ladder',
                 'Impurity ppm after each route step (log y), one '
                 'series per impurity, with the SoG and EG boron '
                 'limits as guides — where B/P stall is where the '
                 'grade stalls', 'step', 'ppmw'),
    _route_graph('scheil',
                 'Scheil profile C_s(f_s) per impurity for one '
                 'directional pass from the MG feed — k_eff ≪ 1 '
                 'metals fall off the chart, B (0.8) stays flat',
                 'fraction solidified f_s', 'C_s (ppmw)'),
]


def impurity_ladder_rows(manager, route_name, feed_ppm_json=None,
                         knobs=None):
    sim = route_simulation(manager, route_name, feed_ppm_json, knobs)
    if not sim.get('ok'):
        return sim
    rows = []
    for imp in IMPURITIES:
        rows.append({'x': 'feed', 'y': sim['feed_ppm'].get(imp, 0.0),
                     'series': imp, 'style': 'line'})
        for st in sim['steps']:
            rows.append({'x': f"{st['index']}:{st['step']}",
                         'y': max(st['ppm_out'].get(imp, 0.0), 1e-9),
                         'series': imp, 'style': 'line'})
    for g in ('sog-si', 'eg-si'):
        rows.append({'x': 'feed', 'y': GRADE_LIMITS_PPM[g]['B'],
                     'series': f'B limit {g}', 'style': 'hguide'})
    return {'ok': True, 'route': route_name, 'rows': rows,
            'grade_achieved': sim['grade_achieved']}


def scheil_rows(feed_ppm=None, fs_grid=None):
    feed = dict(DEFAULT_MG_FEED_PPM)
    feed.update(feed_ppm or {})
    rows = []
    for imp in IMPURITIES:
        r = scheil_pass(feed[imp], SEGREGATION_K[imp]['k'], fs_grid)
        rows.extend({'x': fs, 'y': max(c, 1e-9), 'series': imp,
                     'style': 'line'} for fs, c in r['profile'])
    return {'ok': True, 'rows': rows,
            'equation': 'C_s = k_eff C_0 (1 - f_s)^(k_eff - 1)'}


# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------
def refinement_report(manager, knobs=None):
    ladder = grade_ladder(manager)
    steps = [{'name': s.name, 'display_name': s.display_name,
              'order': s.order, 'chemistry': s.chemistry,
              'model_kind': s.model_kind, 'openness': s.openness,
              'equipment_class': s.equipment_class,
              'energy_kwh_per_kg': s.energy_kwh_per_kg,
              'energy_range': _js(s.energy_range_json, []),
              'confidence': s.confidence,
              'purity_in_grade': s.purity_in_grade,
              'purity_out_grade': s.purity_out_grade}
             for s in sorted(_rows(manager, 'RefinementStep'),
                             key=lambda r: r.order)]
    routes = []
    for r in sorted(_rows(manager, 'RefinementRoute'),
                    key=lambda r: r.order):
        sim = route_simulation(manager, r.name, knobs=knobs)
        routes.append({'name': r.name, 'display_name': r.display_name,
                       'target_grade': r.target_grade,
                       'openness': r.openness, 'reasoning': r.reasoning,
                       'steps': _js(r.steps_json, []),
                       'novel_directions': _js(r.novel_directions_json,
                                               []),
                       'simulated': sim})
    pv = next((x['simulated'] for x in routes
               if x['name'] == 'pv-open-route'), None)
    eg = next((x['simulated'] for x in routes
               if x['name'] == 'eg-novel-route'), None)

    def _bp(sim):
        return ({'B': sim['final_ppm'].get('B'),
                 'P': sim['final_ppm'].get('P')} if sim and sim.get('ok')
                else None)
    # one DS pass on B/P alone: the number that explains everything
    ds_b = scheil_pass(DEFAULT_MG_FEED_PPM['B'], 0.8)
    ds_p = scheil_pass(DEFAULT_MG_FEED_PPM['P'], 0.35)
    statement = {
        'pv_grade': {
            'reachable_by_open_route': bool(pv and pv['target_reached']),
            'route': 'pv-open-route',
            'b_p_after_route_ppm': _bp(pv),
            'grade_achieved': pv['grade_achieved'] if pv else None,
            'limiter': 'B (k_eff 0.8): one directional pass removes '
                       f'only {ds_b["removal_fraction"]*100:.0f} % of B '
                       f'vs {ds_p["removal_fraction"]*100:.0f} % of P; '
                       'the plasma step (PRIOR coefficient) is what '
                       'closes B to SoG',
            'openness': pv['openness'] if pv else None,
        },
        'semiconductor_grade': {
            'reachable_by_open_route': bool(eg and eg['target_reached']),
            'route': 'eg-novel-route',
            'b_p_after_best_open_chain_ppm': _bp(eg),
            'grade_achieved': eg['grade_achieved'] if eg else None,
            'why_not': 'B/P segregation is too weak: k_eff(B)=0.8, '
                       'k_eff(P)=0.35 — solidification (DS/FZ/CZ) '
                       'reduces B by ≤ 20 % per pass, so no number '
                       'of open passes reaches ppb; the chlorosilane '
                       'distillation that does is industrial know-how',
            'openness': 'novel-needed',
            'candidate_directions': eg['novel_directions'] if eg else [],
            'decision_for_dustin': 'plan §2 decision 5: which candidate '
                                   'direction to pursue first — none '
                                   'endorsed here',
        },
    }
    return {'ok': True, 'knobs': dict(REFINEMENT_KNOBS, **(knobs or {})),
            'default_feed_ppm': DEFAULT_MG_FEED_PPM,
            'feed_citation': '[CEC12] typical MG-Si analyses',
            'segregation_coefficients': SEGREGATION_K,
            'grade_ladder': ladder, 'steps': steps, 'routes': routes,
            'statement': statement, 'citations': CITATIONS,
            'graphs': [g['name'] for g in SEED_SI_REFINEMENT_GRAPHS],
            'techtree_refs': ['silicon-refinement', 'silicon-supply',
                              'silicon-supply-pv-grade',
                              'silicon-supply-semiconductor-grade',
                              'silicon']}
