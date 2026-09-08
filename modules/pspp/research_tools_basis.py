"""
@module pspp.research_tools_basis

mtt-2 RESEARCH TOOLS — the instruments a community builds to SEE what
its materials, food, water and soil are doing. The measurement half of
the open-source economy: manufacturing tools MAKE, research tools
MEASURE. Each is a ResearchTool row a maker can build, with its parts
(reusing the accessibility tiers), difficulty, safety and the plain
reason it matters.

Seeded from Dustin's asks (open-source FTIR, a red-cabbage pH detector,
a fruit/vegetable sugar test) plus the highest-leverage additions for
this project's domains (materials / food / water / carbon):
  - a VISIBLE spectrometer (DVD grating + webcam) — the accessible
    cousin of FTIR that turns any colour assay quantitative;
  - an EC/TDS meter — dissolved minerals in water + soil (hydroponics);
  - a colorimeter — single-wavelength assays (nitrate, phosphate…);
  - a thermocouple logger — measures furnace temperature, the tool
    that lets you actually CLIMB the manufacturing furnace ladder;
  - a turbidity meter + a DIY microscope.

Honesty: difficulty + safety are cited-approximate judgements; where a
tool only CORRELATES with what a user wants (Brix vs "nutrient
density"), the row says so — a correlation, never a proof.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (/api/pspp/research-tools)
  - pspp.research_tools_selftest
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.solgel_sourcing_basis import ACCESSIBILITY_TIERS, _tier_rank

#: How hard to build (not how hazardous) — trivial < low < moderate <
#: high. Ordered for the "start easy" sort.
BUILD_DIFFICULTY = ('trivial', 'low', 'moderate', 'high')

#: The domains a tool serves (navigation).
TOOL_DOMAINS = ('materials', 'food', 'water', 'soil', 'carbon',
                'general')


class ResearchTool(treeObject):
    """One buildable open-source research instrument."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        measures: str = '',
        # Plain-language: how it works + how you build it.
        how_plain: str = '',
        # JSON list of {part, tier, note} — the key components.
        parts_json: str = '[]',
        # Rollup accessibility (worst part tier) — ACCESSIBILITY_TIERS.
        accessibility_tier: str = 'common-industrial',
        # BUILD_DIFFICULTY entry.
        difficulty: str = 'moderate',
        # Plain safety note.
        safety: str = '',
        # JSON list of TOOL_DOMAINS it serves.
        domains_json: str = '[]',
        # What the reading DIRECTLY is vs what it only correlates with
        # ('' = it measures its quantity directly).
        correlation_caveat: str = '',
        # The tech-tree research node this backs.
        tech_node: str = '',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.measures = measures
        self.how_plain = how_plain
        self.parts_json = parts_json
        self.accessibility_tier = accessibility_tier
        self.difficulty = difficulty
        self.safety = safety
        self.domains_json = domains_json
        self.correlation_caveat = correlation_caveat
        self.tech_node = tech_node
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


_RT_PROV = ('mtt-2 research-tools seed 2026-07-27 — open-source '
            'instrument designs; difficulty/safety are cited-'
            'approximate judgements, not tested build guides.')

_RT = 'research-tools'


def _parts(*items):
    return json.dumps([{'part': p, 'tier': t, 'note': n}
                       for p, t, n in items])


SEED_RESEARCH_TOOLS = [
    {'name': 'red-cabbage-ph-detector',
     'display_name': 'Red-cabbage pH detector',
     'measures': 'pH (acidity/alkalinity) by colour',
     'how_plain': 'Red cabbage contains anthocyanin, a dye that '
                  'changes colour with pH: red/pink in acid, purple '
                  'near neutral, blue-green to yellow in base. Boil '
                  'shredded cabbage, keep the purple water, add a few '
                  'drops to your sample and read the colour against a '
                  'chart. Pair it with the visible spectrometer to '
                  'turn the colour into a NUMBER.',
     'parts_json': _parts(
         ('red cabbage', 'household', 'the anthocyanin source'),
         ('hot water + a jar', 'household', 'to extract the dye'),
         ('a reference colour chart', 'household',
          'calibrate against known-pH samples: lemon juice, water, '
          'baking-soda solution')),
     'accessibility_tier': 'household', 'difficulty': 'trivial',
     'safety': 'completely safe — it is food.',
     'domains_json': json.dumps(['water', 'soil', 'food', 'general']),
     'tech_node': f'{_RT}/red-cabbage-ph',
     'source_reference': 'Classic anthocyanin pH-indicator chemistry.'},
    {'name': 'brix-refractometer',
     'display_name': 'Brix refractometer (sugar / sap density)',
     'measures': 'dissolved solids (mostly sugars) in a juice, as '
                 'degrees Brix',
     'how_plain': 'Light bends more as it passes through a denser, '
                  'sweeter juice. A refractometer reads that bend and '
                  'shows Brix (roughly % dissolved solids). Squeeze a '
                  'drop of fruit/vegetable sap onto the prism and '
                  'read. Higher Brix usually means more sugar and, in '
                  'regenerative-agriculture practice, often tracks a '
                  'more mineral-dense, healthier plant.',
     'parts_json': _parts(
         ('handheld refractometer (or DIY critical-angle prism)',
          'common-industrial', 'cheap to buy; DIY is a moderate build'),
         ('garlic press / cloth', 'household', 'to extract sap')),
     'accessibility_tier': 'common-industrial', 'difficulty': 'low',
     'safety': 'safe.',
     'domains_json': json.dumps(['food', 'soil']),
     'correlation_caveat': 'Brix measures DISSOLVED SOLIDS (mainly '
                           'sugar) directly. It only CORRELATES with '
                           '"mineral content / plant health" — a '
                           'useful field proxy (regenerative-ag '
                           'practice), NOT a proof of nutrient '
                           'density. Confirm minerals with EC or a '
                           'lab test.',
     'tech_node': f'{_RT}/brix-refractometer',
     'source_reference': 'Refractometry; Brix-as-plant-health is a '
                         'field correlation (Reams / regenerative-ag), '
                         'not a validated nutrient assay.'},
    {'name': 'visible-spectrometer',
     'display_name': 'Visible-light spectrometer (DVD + webcam)',
     'measures': 'the visible spectrum a sample absorbs/emits — turns '
                 'any colour assay into a number',
     'how_plain': 'A slice of a DVD is a diffraction grating: it '
                  'spreads light into a rainbow. Point a webcam at the '
                  'rainbow from a narrow slit and software reads how '
                  'much of each colour is present. This is the '
                  'WORKHORSE research tool — it makes the red-cabbage '
                  'pH, nitrate, phosphate and chlorophyll assays '
                  'QUANTITATIVE, and it is the accessible cousin of '
                  'FTIR (visible, not infrared).',
     'parts_json': _parts(
         ('a DVD (grating)', 'household', 'the rainbow-maker'),
         ('a webcam', 'household', 'the detector'),
         ('a dark box + a slit', 'household', 'cardboard + a razor cut'),
         ('open-source software (Theremino / SpectralWorkbench)',
          'household', 'reads the spectrum from the image')),
     'accessibility_tier': 'household', 'difficulty': 'low',
     'safety': 'safe.',
     'domains_json': json.dumps(
         ['materials', 'food', 'water', 'general']),
     'tech_node': f'{_RT}/visible-spectrometer',
     'source_reference': 'Public Lab DIY spectrometer; a standard '
                         'grating+camera design.'},
    {'name': 'open-source-ftir',
     'display_name': 'Open-source FTIR spectrometer',
     'measures': 'molecular bonds (Si-O-Si/Al, O-H, carbonate) via '
                 'infrared absorption — see pspp.characterization_seed',
     'how_plain': 'Infrared light makes bonds vibrate; the material '
                  'absorbs the infrared "colours" that match its '
                  'bonds. A true FTIR splits an infrared beam, '
                  'recombines it through a moving mirror '
                  '(interferometer) and computes the spectrum. It '
                  'reads AMORPHOUS materials (geopolymers, gels) that '
                  'XRD cannot, and it DETECTS CARBONATE — the honest '
                  'way to verify carbon-negative sequestration.',
     'parts_json': _parts(
         ('broadband IR source (nichrome / globar)',
          'common-industrial', 'a hot element'),
         ('interferometer or monochromator', 'lab-reagent',
          'a moving-mirror beamsplitter — the hard, precise part'),
         ('pyroelectric / thermopile IR detector',
          'common-industrial', 'senses the infrared'),
         ('microcontroller + ADC', 'household', 'digitizes + FFTs')),
     'accessibility_tier': 'lab-reagent', 'difficulty': 'high',
     'safety': 'SAFE — infrared is non-ionizing. The precision of the '
               'interferometer is the challenge, not any hazard.',
     'domains_json': json.dumps(['materials', 'carbon']),
     'tech_node': f'{_RT}/open-source-ftir',
     'source_reference': 'FTIR instrumentation; a reach-goal build — '
                         'the visible spectrometer is the accessible '
                         'first step.',
     'notes': 'Highest-difficulty tool. Build the visible spectrometer '
              'first; escalate to FTIR when the interferometer part is '
              'within reach.'},
    {'name': 'ec-tds-meter',
     'display_name': 'EC / TDS meter (dissolved minerals)',
     'measures': 'electrical conductivity of water/soil-water -> total '
                 'dissolved salts (minerals)',
     'how_plain': 'Dissolved minerals make water conduct electricity; '
                  'the more salts, the higher the conductivity. Two '
                  'electrodes driven by a small AC signal read it, and '
                  'a microcontroller converts it to TDS. This is the '
                  'direct MINERAL-content measure for water, nutrient '
                  'solution and soil extract — the honest partner to '
                  'the Brix "health" proxy.',
     'parts_json': _parts(
         ('two electrodes (graphite / stainless)', 'household',
          'the probe'),
         ('microcontroller + a few resistors', 'household',
          'AC drive + read'),
         ('a known calibration solution', 'common-industrial',
          'to convert conductivity to TDS')),
     'accessibility_tier': 'common-industrial', 'difficulty': 'moderate',
     'safety': 'safe (low-voltage).',
     'domains_json': json.dumps(['water', 'soil', 'food']),
     'tech_node': f'{_RT}/ec-tds-meter',
     'source_reference': 'Standard conductivity metering.'},
    {'name': 'colorimeter',
     'display_name': 'LED colorimeter (single-wavelength assays)',
     'measures': 'how much a coloured solution absorbs one colour of '
                 'light -> concentration of a target (nitrate, '
                 'phosphate, chlorine…)',
     'how_plain': 'Shine one colour of LED through a vial of solution '
                  'onto a light sensor. The more of the target '
                  'chemical (after a colour-forming reagent), the more '
                  'light is absorbed. Calibrate against known '
                  'concentrations and read the rest. Simpler than the '
                  'spectrometer when you only need one wavelength.',
     'parts_json': _parts(
         ('an LED (chosen colour)', 'household', 'the source'),
         ('a photodiode / LDR', 'household', 'the detector'),
         ('a clear vial (cuvette)', 'household', 'holds the sample'),
         ('microcontroller', 'household', 'reads + calibrates')),
     'accessibility_tier': 'household', 'difficulty': 'low',
     'safety': 'safe (reagents vary — follow the assay).',
     'domains_json': json.dumps(['water', 'soil', 'food']),
     'tech_node': f'{_RT}/colorimeter',
     'source_reference': 'DIY colorimetry (standard).'},
    {'name': 'thermocouple-logger',
     'display_name': 'Thermocouple furnace logger',
     'measures': 'high temperature (to ~1300 C type-K, higher with '
                 'type-S) inside a kiln/furnace',
     'how_plain': 'Two different metals joined at a tip produce a tiny '
                  'voltage that grows with temperature. A chip '
                  '(MAX6675/31855) reads it and a microcontroller '
                  'logs it. This is the tool that lets you actually '
                  'CLIMB the manufacturing furnace ladder — you cannot '
                  'hit 1200 C for a leucite ceramic if you cannot '
                  'MEASURE 1200 C.',
     'parts_json': _parts(
         ('type-K thermocouple probe', 'common-industrial',
          'the high-temp sensor'),
         ('MAX6675/MAX31855 amplifier', 'common-industrial',
          'reads the thermocouple'),
         ('microcontroller + display', 'household', 'logs + shows')),
     'accessibility_tier': 'common-industrial', 'difficulty': 'low',
     'safety': 'safe (the FURNACE is the hazard, not the logger).',
     'domains_json': json.dumps(['materials', 'general']),
     'tech_node': f'{_RT}/thermocouple-logger',
     'source_reference': 'Standard thermocouple instrumentation.',
     'notes': 'Bridges research <-> manufacturing: the furnace ladder '
              'rungs are only reachable if their temperature is '
              'measurable.'},
    {'name': 'turbidity-meter',
     'display_name': 'Turbidity meter (water clarity)',
     'measures': 'suspended-particle cloudiness of water',
     'how_plain': 'Shine an LED into water and measure the light '
                  'scattered sideways by suspended particles — cloudier '
                  'water scatters more. A cheap check on water quality '
                  'and on settling/filtration.',
     'parts_json': _parts(
         ('LED + photodiode at 90 degrees', 'household', 'source + '
          'scatter sensor'),
         ('microcontroller', 'household', 'reads')),
     'accessibility_tier': 'household', 'difficulty': 'low',
     'safety': 'safe.',
     'domains_json': json.dumps(['water']),
     'tech_node': f'{_RT}/turbidity-meter',
     'source_reference': 'Nephelometry (standard).'},
    {'name': 'diy-microscope',
     'display_name': 'DIY microscope (morphology / biology)',
     'measures': 'micro-structure + biology you cannot see by eye',
     'how_plain': 'A single tiny lens (or a reversed phone-camera '
                  'lens, or a laser-pointer lens) held close to a '
                  'sample magnifies it onto a phone camera. Enough to '
                  'see crystals, fibres, cells, soil life.',
     'parts_json': _parts(
         ('a small lens (salvaged / laser-pointer)', 'household',
          'the objective'),
         ('a phone camera', 'household', 'the eyepiece + recorder'),
         ('a simple stand + light', 'household', 'to hold + illuminate')),
     'accessibility_tier': 'household', 'difficulty': 'low',
     'safety': 'safe.',
     'domains_json': json.dumps(['materials', 'food', 'soil',
                                 'general']),
     'tech_node': f'{_RT}/diy-microscope',
     'source_reference': 'DIY / smartphone microscopy (standard).'},
]

for _row in SEED_RESEARCH_TOOLS:
    _row.setdefault('provenance_id', _RT_PROV)
    _row.setdefault('correlation_caveat', '')
    _row.setdefault('notes', '')


def tool_dict(row):
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
        'measures': get('measures', ''),
        'howPlain': get('how_plain', ''),
        'parts': loads('parts_json', '[]'),
        'accessibilityTier': get('accessibility_tier', ''),
        'difficulty': get('difficulty', ''),
        'safety': get('safety', ''),
        'domains': loads('domains_json', '[]'),
        'correlationCaveat': get('correlation_caveat', ''),
        'source': get('source_reference', ''),
        'notes': get('notes', ''),
    }


def research_tools(domain=None, samples=None):
    """The buildable-instrument catalog, easiest first. Optional
    domain filter (materials/food/water/soil/carbon)."""
    rows = samples if samples is not None else SEED_RESEARCH_TOOLS
    tools = [tool_dict(r) for r in rows]
    if domain:
        tools = [t for t in tools if domain in t['domains']]
    tools.sort(key=lambda t: (BUILD_DIFFICULTY.index(t['difficulty'])
                              if t['difficulty'] in BUILD_DIFFICULTY
                              else 99,
                              _tier_rank(t['accessibilityTier'])))
    return {'ok': True, 'domain': domain or 'all', 'tools': tools}


def validate_tools(samples=None):
    """Structural honesty: known tiers/difficulties/domains, and the
    stored accessibility tier equals the worst part tier."""
    rows = samples if samples is not None else SEED_RESEARCH_TOOLS
    findings = []
    for r in rows:
        t = tool_dict(r)
        if t['accessibilityTier'] not in ACCESSIBILITY_TIERS:
            findings.append({'tool': t['name'],
                             'issue': f'unknown tier '
                                      f'{t["accessibilityTier"]!r}'})
        if t['difficulty'] not in BUILD_DIFFICULTY:
            findings.append({'tool': t['name'],
                             'issue': f'unknown difficulty '
                                      f'{t["difficulty"]!r}'})
        if any(d not in TOOL_DOMAINS for d in t['domains']):
            findings.append({'tool': t['name'],
                             'issue': 'unknown domain in '
                                      f'{t["domains"]}'})
        worst = max((_tier_rank(p.get('tier', '')) for p in t['parts']),
                    default=0)
        if _tier_rank(t['accessibilityTier']) < worst:
            findings.append({
                'tool': t['name'],
                'issue': 'stored tier is more accessible than its '
                         'hardest part'})
    return {'ok': not findings, 'findings': findings}
