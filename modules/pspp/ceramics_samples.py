"""
@module pspp.ceramics_samples

mtt-2 ceramics: concrete CERAMIC SAMPLES for real use cases, arranged
as a "gradual escalating temperature resistance" ladder — from
locally-fired earthenware up to steelmaking-grade refractories — with
TWO parallel top-of-ladder tracks:

  LOCAL track (pure locally-producible): clay bodies -> fireclay
    firebrick -> mullite/alumina -> dolomitic BASIC refractory. Every
    feedstock is household or common-industrial.
  OLIVINE track (non-local but optimized, CARBON-NEGATIVE): forsterite
    (from mined olivine) — a basic refractory whose olivine feedstock
    carbonates CO2 (Mg2SiO4 + 2CO2 -> 2MgCO3 + SiO2), the critical
    carbon-negative pathway. Flagged mined-nonlocal, honestly.

Each sample records its feedstocks + accessibility tier, an
APPROXIMATE-literature service/softening temperature (claim_status
says so; a datasheet refines it — no false precision), thermal-shock
behaviour (the "gradual escalating" tolerance), refractory class
(acidic/basic/neutral — basic resists steelmaking slags), a carbon
profile, and the use cases it serves.

Honesty: temperatures are textbook-approximate CITED claims, not
measured for a specific body; carbon-negative sequestration NUMBERS
refuse until the olivine-carbonation dataset is digitized (only the
stoichiometry is exact).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.ceramics_ladder (linings the escalation rungs require)
  - pspp.pspp_api (/api/pspp/ceramics/samples)
  - pspp.selftest_ceramics_samples
"""

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.solgel_sourcing import ACCESSIBILITY_TIERS, _tier_rank

#: How a body tolerates being taken UP in temperature (thermal-shock /
#: gradual-escalation behaviour) — the "gradual escalating temperature
#: resistant" axis Dustin named.
THERMAL_SHOCK = ('poor', 'moderate', 'good', 'excellent')

#: Refractory chemistry — which slags it survives. BASIC refractories
#: resist the basic slags of steelmaking; ACIDIC (silica-rich) get
#: eaten by them.
REFRACTORY_CLASSES = ('acidic', 'neutral', 'basic', 'not-refractory')

CARBON_PROFILES = ('neutral', 'carbon-positive', 'carbon-negative-capable')

TEMP_CLAIM = 'literature-approximate'


class CeramicSample(treeObject):
    """One usable ceramic body + its temperature/sourcing/carbon
    profile. A row is a SAMPLE a maker can target, not a measured
    datasheet — temp_claim_status says how firm each number is."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # earthenware | stoneware | fireclay | cordierite | mullite |
        # alumina | silicon-carbide | dolomitic-basic | forsterite |
        # zirconia (free string — extensible).
        family: str = '',
        # JSON list of {material, tier, note} — the feedstocks.
        feedstocks_json: str = '[]',
        # Rollup accessibility (worst feedstock tier) — one of
        # ACCESSIBILITY_TIERS.
        accessibility_tier: str = 'common-industrial',
        # Peak temperature to MAKE it (fire/sinter), Celsius.
        peak_firing_temp_c: float = 0.0,
        # Max continuous SERVICE temperature, Celsius (approximate).
        max_service_temp_c: float = 0.0,
        # Softening/melting onset, Celsius (approximate; 0 = unknown).
        softening_temp_c: float = 0.0,
        temp_claim_status: str = TEMP_CLAIM,
        # THERMAL_SHOCK entry.
        thermal_shock: str = 'moderate',
        # REFRACTORY_CLASSES entry.
        refractory_class: str = 'not-refractory',
        # CARBON_PROFILES entry.
        carbon_profile: str = 'neutral',
        # JSON list of use-case strings.
        use_cases_json: str = '[]',
        # 'vessel' | 'kiln-furniture' | 'refractory-brick' |
        # 'furnace-lining' | 'crucible' | 'heating-element' — its role
        # in the escalation ladder ('' = end product only).
        ladder_role: str = '',
        # 'local' | 'non-local' — which track it belongs to.
        track: str = 'local',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.family = family
        self.feedstocks_json = feedstocks_json
        self.accessibility_tier = accessibility_tier
        self.peak_firing_temp_c = peak_firing_temp_c
        self.max_service_temp_c = max_service_temp_c
        self.softening_temp_c = softening_temp_c
        self.temp_claim_status = temp_claim_status
        self.thermal_shock = thermal_shock
        self.refractory_class = refractory_class
        self.carbon_profile = carbon_profile
        self.use_cases_json = use_cases_json
        self.ladder_role = ladder_role
        self.track = track
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


import json

_CER_PROV = ('mtt-2 ceramics-samples seed 2026-07-26 — temperatures '
             'are textbook-approximate cited claims (Ceramics '
             'literature: Kingery, Introduction to Ceramics; '
             'refractory handbooks). Datasheet values refine them; '
             'carbon-negative NUMBERS refuse until the olivine-'
             'carbonation dataset is digitized.')


def _fs(*items):
    return json.dumps([{'material': m, 'tier': t, 'note': n}
                       for m, t, n in items])


SEED_CERAMIC_SAMPLES = [
    # -- LOCAL track, ascending service temperature --
    {'name': 'earthenware-terracotta',
     'display_name': 'Earthenware / terracotta',
     'family': 'earthenware', 'track': 'local',
     'feedstocks_json': _fs(
         ('local earthenware clay', 'household',
          'dug + levigated; iron-rich red-firing clay')),
     'accessibility_tier': 'household',
     'peak_firing_temp_c': 1000.0, 'max_service_temp_c': 1000.0,
     'softening_temp_c': 1100.0, 'thermal_shock': 'moderate',
     'refractory_class': 'not-refractory', 'carbon_profile': 'neutral',
     'use_cases_json': json.dumps([
         'pots + cookware', 'low-fire bricks', 'the FIRST fired '
         'vessels — needs only a wood/geopolymer oven']),
     'ladder_role': 'vessel',
     'source_reference': 'Standard ceramics literature (earthenware '
                         'matures ~1000 C).'},
    {'name': 'stoneware',
     'display_name': 'Stoneware',
     'family': 'stoneware', 'track': 'local',
     'feedstocks_json': _fs(
         ('local stoneware clay', 'household',
          'plastic clay maturing higher than earthenware')),
     'accessibility_tier': 'household',
     'peak_firing_temp_c': 1200.0, 'max_service_temp_c': 1200.0,
     'softening_temp_c': 1300.0, 'thermal_shock': 'moderate',
     'refractory_class': 'not-refractory', 'carbon_profile': 'neutral',
     'use_cases_json': json.dumps([
         'watertight durable ware', 'kiln furniture (low)',
         'the vessel body that survives a hotter kiln']),
     'ladder_role': 'vessel',
     'source_reference': 'Stoneware matures ~1200-1300 C (ceramics '
                         'literature).'},
    {'name': 'fireclay-firebrick',
     'display_name': 'Fireclay firebrick (refractory)',
     'family': 'fireclay', 'track': 'local',
     'feedstocks_json': _fs(
         ('kaolinitic fireclay', 'household',
          'refractory clay, low flux'),
         ('grog (crushed fired clay)', 'household',
          'pre-fired temper — controls shrinkage + thermal shock')),
     'accessibility_tier': 'household',
     'peak_firing_temp_c': 1300.0, 'max_service_temp_c': 1500.0,
     'softening_temp_c': 1600.0, 'thermal_shock': 'moderate',
     'refractory_class': 'acidic', 'carbon_profile': 'neutral',
     'use_cases_json': json.dumps([
         'THE refractory brick you line a hotter furnace with',
         'kiln + forge walls', 'bootstraps the next rung']),
     'ladder_role': 'refractory-brick',
     'source_reference': 'Fireclay refractories service ~1500-1600 C '
                         '(refractory handbooks); acidic (silica-'
                         'alumina) so basic slags attack it.',
     'notes': 'The keystone LOCAL refractory — makeable from common '
              'clay, and it is what raises the achievable furnace '
              'temperature.'},
    {'name': 'cordierite',
     'display_name': 'Cordierite (thermal-shock refractory)',
     'family': 'cordierite', 'track': 'local',
     'feedstocks_json': _fs(
         ('talc', 'common-industrial', 'Mg source'),
         ('kaolin', 'household', 'Al-Si source'),
         ('alumina', 'common-industrial', 'balances the 2:2:5')),
     'accessibility_tier': 'common-industrial',
     'peak_firing_temp_c': 1350.0, 'max_service_temp_c': 1250.0,
     'softening_temp_c': 1450.0, 'thermal_shock': 'excellent',
     'refractory_class': 'neutral', 'carbon_profile': 'neutral',
     'use_cases_json': json.dumps([
         'kiln shelves + setters (survive repeated cycling)',
         'burner + heat-exchanger parts',
         'anything taken up + down in temperature often']),
     'ladder_role': 'kiln-furniture',
     'source_reference': 'Cordierite (2MgO.2Al2O3.5SiO2) has a very '
                         'low thermal-expansion coefficient -> '
                         'excellent thermal-shock resistance (Kingery).',
     'notes': 'The "gradual escalating temperature resistant" '
              'champion: not the highest service temp, but it tolerates '
              'rapid/repeated temperature swings without cracking.'},
    {'name': 'mullite',
     'display_name': 'Mullite (high refractory)',
     'family': 'mullite', 'track': 'local',
     'feedstocks_json': _fs(
         ('kaolin / fireclay', 'household', 'Al-Si source'),
         ('alumina', 'common-industrial',
          'shifts composition to 3Al2O3.2SiO2')),
     'accessibility_tier': 'common-industrial',
     'peak_firing_temp_c': 1600.0, 'max_service_temp_c': 1700.0,
     'softening_temp_c': 1830.0, 'thermal_shock': 'good',
     'refractory_class': 'neutral', 'carbon_profile': 'neutral',
     'use_cases_json': json.dumps([
         'high-temperature furnace lining + tubes',
         'crucibles up to ~1700 C',
         'the structural refractory of a steelmaking furnace']),
     'ladder_role': 'furnace-lining',
     'source_reference': 'Mullite (3Al2O3.2SiO2) is stable to ~1830 C '
                         'incongruent melting; service ~1700 C '
                         '(Kingery).'},
    {'name': 'alumina',
     'display_name': 'Alumina (Al2O3)',
     'family': 'alumina', 'track': 'local',
     'feedstocks_json': _fs(
         ('refined alumina (from bauxite)', 'common-industrial',
          'calcined Al2O3 powder — refining is the harder step')),
     'accessibility_tier': 'common-industrial',
     'peak_firing_temp_c': 1650.0, 'max_service_temp_c': 1750.0,
     'softening_temp_c': 2050.0, 'thermal_shock': 'moderate',
     'refractory_class': 'neutral', 'carbon_profile': 'neutral',
     'use_cases_json': json.dumps([
         'crucibles + high-temp linings',
         'wear + electrical-insulator parts',
         'contact refractory for melting metals']),
     'ladder_role': 'crucible',
     'source_reference': 'Sintered alumina melts ~2050 C; service to '
                         '~1750 C (Kingery). Moderate thermal shock '
                         '(needs gradual heating in thick sections).',
     'notes': 'Needs REFINED alumina — the alumina refining step '
              '(Bayer or a local reduction) is the real accessibility '
              'gate, not the firing.'},
    {'name': 'silicon-carbide',
     'display_name': 'Silicon carbide (SiC)',
     'family': 'silicon-carbide', 'track': 'local',
     'feedstocks_json': _fs(
         ('silica sand', 'household', 'SiO2'),
         ('carbon (coke/charcoal)', 'household', 'reductant'),
         ('very-high-temp synthesis (~2500 C, Acheson)',
          'mined-nonlocal',
          'the SYNTHESIS temperature, not the feedstock, is the gate')),
     'accessibility_tier': 'mined-nonlocal',
     'peak_firing_temp_c': 2500.0, 'max_service_temp_c': 1600.0,
     'softening_temp_c': 2700.0, 'thermal_shock': 'excellent',
     'refractory_class': 'neutral', 'carbon_profile': 'carbon-positive',
     'use_cases_json': json.dumps([
         'electric heating elements (self-heating furnace)',
         'high-temp + high-thermal-shock kiln furniture',
         'abrasives']),
     'ladder_role': 'heating-element',
     'source_reference': 'SiC (Acheson process ~2500 C) — excellent '
                         'thermal shock + oxidation-protected to '
                         '~1600 C in air.',
     'notes': 'Feedstocks are trivial (sand + carbon) but the '
              'SYNTHESIS temperature is a chicken-and-egg gate — you '
              'need a very hot furnace to make the material that '
              'builds very hot furnaces. Carbon-positive (uses coke).'},
    {'name': 'dolomitic-basic-refractory',
     'display_name': 'Dolomitic (doloma) basic refractory',
     'family': 'dolomitic-basic', 'track': 'local',
     'feedstocks_json': _fs(
         ('dolomite (CaMg(CO3)2)', 'common-industrial',
          'common carbonate rock; calcine to doloma (CaO.MgO)')),
     'accessibility_tier': 'common-industrial',
     'peak_firing_temp_c': 1650.0, 'max_service_temp_c': 1800.0,
     'softening_temp_c': 2300.0, 'thermal_shock': 'poor',
     'refractory_class': 'basic', 'carbon_profile': 'carbon-positive',
     'use_cases_json': json.dumps([
         'BASIC lining for steelmaking (resists basic slags)',
         'the LOCAL path to a steel-capable furnace contact refractory']),
     'ladder_role': 'furnace-lining',
     'source_reference': 'Doloma/dolomite refractories are standard '
                         'BASIC steelmaking linings (refractory '
                         'handbooks); service ~1800 C.',
     'notes': 'The LOCALLY-producible BASIC refractory for steel — '
              'calcining dolomite RELEASES CO2 (carbon-positive), so '
              'it trades carbon cost for local availability. The '
              'olivine track is the carbon-negative alternative.'},
    # -- OLIVINE track: non-local but optimized + CARBON-NEGATIVE --
    {'name': 'forsterite-olivine',
     'display_name': 'Forsterite (olivine) basic refractory',
     'family': 'forsterite', 'track': 'non-local',
     'feedstocks_json': _fs(
         ('olivine (Mg2SiO4, mined)', 'mined-nonlocal',
          'mantle-derived rock (dunite); not locally producible, '
          'though theoretically deep-sourced')),
     'accessibility_tier': 'mined-nonlocal',
     'peak_firing_temp_c': 1600.0, 'max_service_temp_c': 1800.0,
     'softening_temp_c': 1890.0, 'thermal_shock': 'moderate',
     'refractory_class': 'basic',
     'carbon_profile': 'carbon-negative-capable',
     'use_cases_json': json.dumps([
         'BASIC steelmaking refractory (slag-resistant)',
         'the OPTIMIZED + carbon-negative top-of-ladder lining',
         'foundry sand + refractory']),
     'ladder_role': 'furnace-lining',
     'source_reference': 'Forsterite (Mg2SiO4) refractories, mp ~1890 '
                         'C, basic (Kingery). Carbon-negative pathway: '
                         'olivine carbonation Mg2SiO4 + 2CO2 -> 2MgCO3 '
                         '+ SiO2 sequesters CO2 (enhanced weathering / '
                         'mineral carbonation literature).',
     'notes': 'Non-local (mined olivine) but the KEY carbon-negative '
              'ceramic: its feedstock sequesters CO2. Basic refractory '
              '-> genuinely better than acidic mullite/alumina for '
              'steelmaking slag resistance. Sequestration NUMBERS '
              'refuse until the olivine-carbonation dataset is '
              'digitized; the stoichiometry above is exact.'},
]

for _row in SEED_CERAMIC_SAMPLES:
    _row.setdefault('provenance_id', _CER_PROV)
    _row.setdefault('notes', '')
    _row.setdefault('temp_claim_status', TEMP_CLAIM)


#: The olivine carbon-negative pathway as a provisional, REFUSING
#: dataset — the stoichiometry Mg2SiO4 + 2CO2 -> 2MgCO3 + SiO2 is
#: exact, but the sequestered-CO2-per-kg and reaction-rate NUMBERS
#: refuse until a real carbonation study is digitized.
SEED_CERAMICS_DATASETS = [
    {
        'name': 'olivine-carbonation-sequestration',
        'source_reference': 'Mineral carbonation / enhanced-weathering '
                            'literature (e.g. Gerdemann et al. 2007; '
                            'olivine CO2 sequestration) — specific '
                            'figures PENDING digitization',
        'status': 'provisional-low-confidence',
        'independent_variables_json':
            '["temperature_C", "particle_size_um"]',
        'dependent_variables_json':
            '["co2_sequestered_kg_per_kg", "conversion_percent"]',
        'units_json': json.dumps({
            'temperature_C': 'C', 'particle_size_um': 'um',
            'co2_sequestered_kg_per_kg': 'kg CO2 / kg olivine',
            'conversion_percent': '%'}),
        'source_conditions_json': json.dumps({
            'system': 'olivine (forsterite) aqueous/gas carbonation',
            'reaction': 'Mg2SiO4 + 2CO2 -> 2MgCO3 + SiO2 (EXACT '
                        'stoichiometry — ~1.1 kg CO2 per kg pure '
                        'forsterite by mass, but real conversion is '
                        'kinetically limited and site-specific)',
            'note': 'the carbon-negative claim rests on this; the '
                    'stoichiometric ceiling is exact, the ACHIEVED '
                    'sequestration is what refuses'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — stoichiometry known, '
                               'kinetics/yield await a study',
        'points_json': '[]',
        'qualitative_shape':
            'CO2 uptake rises with temperature and finer grinding (more '
            'surface), toward the stoichiometric ceiling ~1.1 kg CO2 '
            'per kg forsterite; real conversions are partial and slow '
            'without activation. Finer + hotter + longer = more '
            'sequestration, with diminishing returns.',
        'notes': 'DATA ASK: digitize an olivine-carbonation study '
                 '(CO2 sequestered + conversion vs temperature + '
                 'particle size) to turn the exact stoichiometry into '
                 'an ACHIEVED carbon-negative figure. Until then the '
                 'forsterite-olivine sample is carbon-negative-CAPABLE '
                 'with the number refusing.',
        'provenance_id': _CER_PROV,
    },
]


def sample_dict(row):
    get = (row.get if isinstance(row, dict)
           else lambda k, d=None: getattr(row, k, d))

    def loads(key, fallback):
        raw = get(key, fallback)
        try:
            return raw if isinstance(raw, list) else json.loads(
                raw or fallback)
        except Exception:
            return json.loads(fallback)
    return {
        'name': get('name', ''),
        'displayName': get('display_name', ''),
        'family': get('family', ''),
        'track': get('track', 'local'),
        'feedstocks': loads('feedstocks_json', '[]'),
        'accessibilityTier': get('accessibility_tier', ''),
        'peakFiringTempC': get('peak_firing_temp_c', 0.0),
        'maxServiceTempC': get('max_service_temp_c', 0.0),
        'softeningTempC': get('softening_temp_c', 0.0),
        'tempClaimStatus': get('temp_claim_status', TEMP_CLAIM),
        'thermalShock': get('thermal_shock', ''),
        'refractoryClass': get('refractory_class', ''),
        'carbonProfile': get('carbon_profile', ''),
        'useCases': loads('use_cases_json', '[]'),
        'ladderRole': get('ladder_role', ''),
        'source': get('source_reference', ''),
        'notes': get('notes', ''),
    }


def temperature_ladder(samples=None):
    """All samples sorted by ascending max service temperature — the
    'gradual escalating temperature resistance' ladder, each tagged
    with its accessibility + carbon profile so the local vs olivine
    tracks are visible side by side."""
    rows = samples if samples is not None else SEED_CERAMIC_SAMPLES
    dicts = [sample_dict(r) for r in rows]
    dicts.sort(key=lambda s: (s['maxServiceTempC'], s['name']))
    return dicts


def samples_meeting_temp(target_c, samples=None, local_only=False,
                         carbon_negative_only=False):
    """Samples whose max service temperature meets a target (e.g. the
    ~1600 C of steelmaking), optionally restricted to the LOCAL track
    or the carbon-negative pathway. Returns the honest set + why the
    filters matter."""
    rows = samples if samples is not None else SEED_CERAMIC_SAMPLES
    out = []
    for s in (sample_dict(r) for r in rows):
        if s['maxServiceTempC'] < float(target_c):
            continue
        if local_only and _tier_rank(s['accessibilityTier']) \
                >= _tier_rank('mined-nonlocal'):
            continue
        if carbon_negative_only and \
                s['carbonProfile'] != 'carbon-negative-capable':
            continue
        out.append(s)
    out.sort(key=lambda s: s['maxServiceTempC'])
    return {
        'ok': True,
        'targetC': float(target_c),
        'localOnly': bool(local_only),
        'carbonNegativeOnly': bool(carbon_negative_only),
        'samples': out,
        'note': 'max service temperatures are literature-approximate '
                '(temp_claim_status) — confirm against a datasheet '
                'before committing a furnace lining',
    }


def validate_samples(samples=None):
    """Honest structural checks: known tiers/classes/shock vocab, and
    the stored accessibility tier equals the worst feedstock tier."""
    rows = samples if samples is not None else SEED_CERAMIC_SAMPLES
    findings = []
    for r in rows:
        s = sample_dict(r)
        if s['accessibilityTier'] not in ACCESSIBILITY_TIERS:
            findings.append({'sample': s['name'],
                             'issue': f'unknown accessibility tier '
                                      f'{s["accessibilityTier"]!r}'})
        if s['thermalShock'] not in THERMAL_SHOCK:
            findings.append({'sample': s['name'],
                             'issue': f'unknown thermal_shock '
                                      f'{s["thermalShock"]!r}'})
        if s['refractoryClass'] not in REFRACTORY_CLASSES:
            findings.append({'sample': s['name'],
                             'issue': f'unknown refractory_class '
                                      f'{s["refractoryClass"]!r}'})
        if s['carbonProfile'] not in CARBON_PROFILES:
            findings.append({'sample': s['name'],
                             'issue': f'unknown carbon_profile '
                                      f'{s["carbonProfile"]!r}'})
        feed_worst = max((_tier_rank(f.get('tier', ''))
                          for f in s['feedstocks']), default=0)
        if _tier_rank(s['accessibilityTier']) < feed_worst:
            findings.append({
                'sample': s['name'],
                'issue': 'stored accessibility tier is more accessible '
                         'than its worst feedstock — a body is only as '
                         'accessible as its hardest input'})
    return {'ok': not findings, 'findings': findings}
