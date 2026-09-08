"""
@module pspp.ceramics_ladder_basis

mtt-2 ceramics: the THERMAL ESCALATION LADDER — the bootstrapping
spine where each furnace is built from the output of the previous one,
climbing from a simple geopolymer oven up to a steelmaking-grade
furnace that can make bio-galvanized steel. This is the "thermal
strain of material refinement" (Dustin) — modeled as DATA (rungs the
maker climbs), the backing for the manufacturing-tools / furnace tech
tree nodes.

Each rung declares the furnace temperature it reaches, the ceramic
LINING it needs (with a LOCAL option and, where it matters, a non-local
OLIVINE/carbon-negative option), the rung it depends on, and what it
unlocks. `validate_ladder` proves the bootstrapping is physically
consistent: every rung's lining must be FIREABLE at the previous
rung's temperature AND WITHSTAND this rung's temperature — you can only
build a furnace from a material your current furnace can already make.

The CNT rung is deliberately honest: catalytic-CVD nanotube growth is
only ~700-1100 C (reachable mid-ladder), but its real gate is a
CONTROLLED ATMOSPHERE + catalyst reactor, NOT heat — so it branches
off as a specialized-refinement capability, not just a hotter furnace.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (/api/pspp/ceramics/ladder)
  - pspp.ceramics_ladder_selftest
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class LadderRung(treeObject):
    """One rung of the furnace escalation ladder."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        order: int = 0,
        # Furnace temperature this rung reaches, Celsius.
        max_temp_c: float = 0.0,
        heat_source: str = '',
        # JSON list of {sample, track, role} — the lining options
        # (CeramicSample names; track local|non-local). '' sample = a
        # non-ceramic lining (e.g. the geopolymer oven itself).
        lining_options_json: str = '[]',
        # The rung whose OUTPUT builds this furnace ('' = start).
        prerequisite_rung: str = '',
        # JSON list of {kind, ref, note} unlocked here — kind is
        # 'material' | 'capability'.
        unlocks_json: str = '[]',
        # The manufacturing-tools furnace TechNode this backs.
        tech_node: str = '',
        # 'thermal' (temperature is the gate) | 'atmosphere'
        # (controlled-atmosphere/catalyst is the real gate, not heat).
        gate_kind: str = 'thermal',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.max_temp_c = max_temp_c
        self.heat_source = heat_source
        self.lining_options_json = lining_options_json
        self.prerequisite_rung = prerequisite_rung
        self.unlocks_json = unlocks_json
        self.tech_node = tech_node
        self.gate_kind = gate_kind
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


_LAD_PROV = ('mtt-2 escalation-ladder seed 2026-07-26 — the '
             'furnace-bootstrapping path; temperatures are '
             'literature-approximate targets, not measured.')

_MTREE = 'manufacturing-tools'


def _lining(*opts):
    return json.dumps([{'sample': s, 'track': t, 'role': r}
                       for s, t, r in opts])


def _unlocks(*items):
    return json.dumps([{'kind': k, 'ref': r, 'note': n}
                       for k, r, n in items])


SEED_LADDER_RUNGS = [
    {'name': 'geopolymer-oven',
     'display_name': 'Geopolymer oven',
     'order': 0, 'max_temp_c': 700.0,
     'heat_source': 'wood/biomass fire in an ambient-cured geopolymer '
                    'body — NO prior kiln needed',
     'lining_options_json': _lining(
         ('', 'local', 'geopolymer body (pspp geopolymer, not a fired '
                       'ceramic — cured at room temperature)')),
     'prerequisite_rung': '',
     'unlocks_json': _unlocks(
         ('capability', 'dry-and-bisque', 'dry + low-fire bisque of '
          'clay ware'),
         ('material', 'earthenware-terracotta', 'first fired vessels')),
     'tech_node': f'{_MTREE}/geopolymer-oven', 'gate_kind': 'thermal',
     'source_reference': 'Geopolymers are ambient-cured + fire-'
                         'resistant (Davidovits) — the entry oven that '
                         'needs no pre-existing furnace.',
     'notes': 'The ladder START: makeable with no kiln, from '
              'alkali-activated aluminosilicate.'},
    {'name': 'earthenware-kiln',
     'display_name': 'Earthenware / wood kiln',
     'order': 1, 'max_temp_c': 1050.0,
     'heat_source': 'wood or charcoal, natural draft',
     'lining_options_json': _lining(
         ('fireclay-firebrick', 'local', 'refractory walls — built '
          'GREEN from raw fireclay and hardened in the first firings '
          '(no pre-fired brick needed)')),
     'prerequisite_rung': 'geopolymer-oven',
     'unlocks_json': _unlocks(
         ('material', 'earthenware-terracotta', 'first fired vessels '
          '(~1000 C)'),
         ('material', 'fireclay-firebrick', 'refractory brick for the '
          'next furnace — green-built here, fully hardens hotter')),
     'tech_node': f'{_MTREE}/earthenware-kiln', 'gate_kind': 'thermal',
     'source_reference': 'Wood/charcoal kilns reach ~1000-1050 C '
                         '(traditional pottery); refractory walls are '
                         'built from raw clay and fire in place.'},
    {'name': 'firebrick-furnace',
     'display_name': 'Firebrick furnace (forced air)',
     'order': 2, 'max_temp_c': 1350.0,
     'heat_source': 'charcoal/coke with forced air (bellows or blower)',
     'lining_options_json': _lining(
         ('fireclay-firebrick', 'local', 'refractory wall lining')),
     'prerequisite_rung': 'earthenware-kiln',
     'unlocks_json': _unlocks(
         ('material', 'stoneware', 'denser watertight ware (~1200 C)'),
         ('material', 'cordierite', 'thermal-shock kiln furniture'),
         ('material', 'mullite', 'begin high refractory (with alumina)'),
         ('capability', 'cnt-atmosphere', 'temperature for catalytic '
          'CVD is reached here — but the gate is atmosphere, see the '
          'CNT reactor rung')),
     'tech_node': f'{_MTREE}/firebrick-furnace', 'gate_kind': 'thermal',
     'source_reference': 'Fireclay-lined forced-air furnaces reach '
                         '~1300-1400 C (forge/foundry practice).'},
    {'name': 'refractory-furnace',
     'display_name': 'High-refractory furnace',
     'order': 3, 'max_temp_c': 1700.0,
     'heat_source': 'forced air + regenerative preheat, or SiC '
                    'heating elements',
     'lining_options_json': _lining(
         ('mullite', 'local', 'structural high-temp lining'),
         ('alumina', 'local', 'crucible / contact refractory'),
         ('forsterite-olivine', 'non-local', 'basic + carbon-negative '
          'option')),
     'prerequisite_rung': 'firebrick-furnace',
     'unlocks_json': _unlocks(
         ('material', 'alumina', 'crucibles + linings to ~1750 C'),
         ('material', 'forsterite-olivine', 'basic carbon-negative '
          'refractory (from mined olivine)'),
         ('capability', 'consistent-high-temp', 'stable ~1700 C')),
     'tech_node': f'{_MTREE}/refractory-furnace', 'gate_kind': 'thermal',
     'source_reference': 'Mullite/alumina-lined furnaces sustain '
                         '~1700 C (refractory practice).'},
    {'name': 'steelmaking-furnace',
     'display_name': 'Steelmaking furnace (basic lining)',
     'order': 4, 'max_temp_c': 1650.0,
     'heat_source': 'forced air / arc — the LINING chemistry, not peak '
                    'temperature, is the gate here',
     'lining_options_json': _lining(
         ('dolomitic-basic-refractory', 'local', 'LOCAL basic lining '
          '(dolomite; carbon-positive)'),
         ('forsterite-olivine', 'non-local', 'OPTIMIZED basic lining '
          '(olivine; carbon-negative)')),
     'prerequisite_rung': 'refractory-furnace',
     'unlocks_json': _unlocks(
         ('capability', 'bio-galvanized-steel', 'melt + refine iron in '
          'a BASIC-lined furnace, then bio-phosphate + bio-zinc coat '
          '(the galvanized-bio-steel goal)')),
     'tech_node': f'{_MTREE}/steelmaking-furnace', 'gate_kind': 'thermal',
     'source_reference': 'Steelmaking (~1600 C melt + refine) needs a '
                         'BASIC refractory to survive basic slags '
                         '(refractory handbooks) — acidic mullite/'
                         'silica linings are attacked.',
     'notes': 'Two linings converge here: LOCAL dolomitic (available '
              'but carbon-positive from calcining) vs NON-LOCAL '
              'olivine forsterite (mined but carbon-negative). Both '
              'are BASIC — the requirement steel imposes.'},
    # -- branch: CNT via CVD — reachable temperature, specialized gate.
    {'name': 'cnt-cvd-reactor',
     'display_name': 'CNT CVD reactor (controlled atmosphere)',
     'order': 3, 'max_temp_c': 1100.0,
     'heat_source': 'moderate heat (~700-1100 C) — TRIVIAL for the '
                    'ladder; the reactor, not the furnace, is the work',
     'lining_options_json': _lining(
         ('mullite', 'local', 'tube furnace refractory'),
         ('alumina', 'local', 'process tube')),
     'prerequisite_rung': 'firebrick-furnace',
     'unlocks_json': _unlocks(
         ('material', 'carbon-nanotubes', 'catalytic CVD growth')),
     'tech_node': f'{_MTREE}/cnt-cvd-reactor',
     'gate_kind': 'atmosphere',
     'source_reference': 'Catalytic CVD nanotube growth is ~700-1100 C '
                         '(CNT literature); arc/laser routes need '
                         '~3000 C+ and are NOT on the thermal ladder.',
     'notes': 'HONEST: temperature is reachable by the firebrick '
              'furnace, but CNT growth needs a CONTROLLED-ATMOSPHERE '
              'catalytic reactor (inert gas + hydrocarbon + catalyst) '
              '— a specialized refinement axis, not just a hotter '
              'furnace. That is why it branches instead of sitting on '
              'the main thermal climb.'},
]

for _row in SEED_LADDER_RUNGS:
    _row.setdefault('provenance_id', _LAD_PROV)
    _row.setdefault('notes', '')


def _get(row, key, default=None):
    return (row.get(key, default) if isinstance(row, dict)
            else getattr(row, key, default))


def _loads(row, key):
    raw = _get(row, key, '[]') or '[]'
    try:
        return raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        return []


def rung_dict(row):
    return {
        'name': _get(row, 'name', ''),
        'displayName': _get(row, 'display_name', ''),
        'order': _get(row, 'order', 0),
        'maxTempC': _get(row, 'max_temp_c', 0.0),
        'heatSource': _get(row, 'heat_source', ''),
        'liningOptions': _loads(row, 'lining_options_json'),
        'prerequisiteRung': _get(row, 'prerequisite_rung', ''),
        'unlocks': _loads(row, 'unlocks_json'),
        'techNode': _get(row, 'tech_node', ''),
        'gateKind': _get(row, 'gate_kind', 'thermal'),
        'source': _get(row, 'source_reference', ''),
        'notes': _get(row, 'notes', ''),
    }


def ladder_path(rungs=None):
    """The rungs in climb order (the main thermal spine + branches),
    sorted by order then name."""
    rows = rungs if rungs is not None else SEED_LADDER_RUNGS
    return sorted((rung_dict(r) for r in rows),
                  key=lambda r: (r['order'], r['name']))


def rung_unlocking(capability, rungs=None):
    """Which rung unlocks a named capability/material (e.g.
    'bio-galvanized-steel')."""
    for r in ladder_path(rungs):
        for u in r['unlocks']:
            if u.get('ref') == capability:
                return {'ok': True, 'rung': r['name'], 'unlock': u,
                        'maxTempC': r['maxTempC']}
    return {'ok': False,
            'refusal': f'no rung unlocks {capability!r}',
            'suggestion': 'check the capability name against '
                          'GET /api/pspp/ceramics/ladder'}


def validate_ladder(rungs=None, samples=None):
    """Prove the bootstrapping is physically consistent: each rung's
    ceramic lining must be FIREABLE at the prerequisite rung's
    temperature AND WITHSTAND this rung's temperature. Non-ceramic
    linings (the geopolymer oven) and atmosphere-gated rungs are noted,
    not temperature-checked. Returns evidence-bearing findings."""
    from pspp.ceramics_samples_basis import SEED_CERAMIC_SAMPLES, sample_dict
    rows = rungs if rungs is not None else SEED_LADDER_RUNGS
    sample_rows = samples if samples is not None else SEED_CERAMIC_SAMPLES
    by_name = {s['name']: s for s in (sample_dict(x)
                                      for x in sample_rows)}
    path = {r['name']: r for r in ladder_path(rows)}
    findings = []
    for rung in path.values():
        prereq = path.get(rung['prerequisiteRung'])
        prev_temp = prereq['maxTempC'] if prereq else None
        for opt in rung['liningOptions']:
            sample_name = opt.get('sample', '')
            if not sample_name:
                continue  # non-ceramic lining (geopolymer oven)
            sample = by_name.get(sample_name)
            if sample is None:
                findings.append({
                    'severity': 'error', 'rung': rung['name'],
                    'lining': sample_name,
                    'issue': f'lining {sample_name!r} is not a known '
                             'CeramicSample'})
                continue
            # Withstand THIS rung's temperature.
            if sample['maxServiceTempC'] < rung['maxTempC']:
                findings.append({
                    'severity': 'error', 'rung': rung['name'],
                    'lining': sample_name,
                    'issue': f'lining service temp '
                             f'{sample["maxServiceTempC"]} C < rung '
                             f'temperature {rung["maxTempC"]} C — it '
                             'would fail in this furnace'})
            # Fireable with the PREVIOUS furnace.
            if prev_temp is not None and \
                    sample['peakFiringTempC'] > prev_temp:
                findings.append({
                    'severity': 'warn', 'rung': rung['name'],
                    'lining': sample_name,
                    'issue': f'lining needs firing at '
                             f'{sample["peakFiringTempC"]} C but the '
                             f'prerequisite furnace '
                             f'{rung["prerequisiteRung"]!r} only '
                             f'reaches {prev_temp} C — source this '
                             'lining or add an intermediate rung'})
    return {
        'ok': not [f for f in findings if f['severity'] == 'error'],
        'findings': findings,
        'note': 'bootstrapping check: a rung is only reachable if its '
                'lining can be MADE by the furnace below it and can '
                'SURVIVE this furnace — temperatures are literature-'
                'approximate, so warns are prompts to confirm, not '
                'hard failures',
    }
