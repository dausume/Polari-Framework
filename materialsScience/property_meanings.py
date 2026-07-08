"""
@cross-cutting
@module materialsScience.property_meanings
@tags @xc:bindings

Material property MEANINGS — what each property IS, its units, and how
it changes per scenario — as editable rows (object-coherence: the
explanation a page shows is configurable AT an object, not hardcoded
frontend text).

PROPERTY_MEANING_VOCAB below is the one vocabulary home; the seed
stamps rows idempotent-by-name, so an admin edit is never overwritten.
Aliases map the many key spellings live data uses (engine result keys
like 'effectiveK', formulation keys like 'ShoreHardness') onto one
meaning row.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.material_detail (attaches meanings to values)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialPropertyMeaning(treeObject):
    """One property concept: meaning, units, scenario behavior."""

    @treeObjectInit
    def __init__(
        self,
        # Canonical key, camelCase ('thermalConductivity').
        name: str = '',
        display_name: str = '',
        units: str = '',
        # Plain-language: what the property IS.
        meaning: str = '',
        # How the value MOVES per scenario (temperature, loading,
        # blending, printing…) — the context half of the detail view.
        scenario_context: str = '',
        # Other key spellings that mean this property (JSON list) —
        # engine result keys, formulation keys, legacy names.
        aliases_json: str = '[]',
        # Scale levels where the property typically appears (JSON list).
        scale_levels_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.units = units
        self.meaning = meaning
        self.scenario_context = scenario_context
        self.aliases_json = aliases_json
        self.scale_levels_json = scale_levels_json
        self.provenance_id = provenance_id
        self.notes = notes


#: The one vocabulary home. Keys = canonical property names; every
#: entry becomes a seeded (editable, never re-overwritten) row.
PROPERTY_MEANING_VOCAB = {
    'thermalConductivity': {
        'display_name': 'Thermal conductivity',
        'units': 'W/m·K',
        'meaning': 'How readily heat flows through the material — the '
                   'k in Fourier conduction. Higher k spreads heat '
                   'faster and evens out temperature gradients.',
        'scenario_context': 'For a composite, the effective k rises '
                            'with conductive-filler loading between the '
                            'Reuss and Voigt mixing bounds (the FEM '
                            'homogenization computes where). In printing '
                            'it sets how fast a deposited bead sheds '
                            'heat into the part.',
        'aliases': ['effectiveK', 'matrixK', 'inclusionK', 'k',
                    'k_eff', 'thermal_conductivity'],
        'scale_levels': [0, 1],
    },
    'effectivePermeability': {
        'display_name': 'Effective magnetic permeability',
        'units': 'relative (µ/µ0)',
        'meaning': 'How strongly the material concentrates magnetic '
                   'flux relative to vacuum. µ=1 is non-magnetic; '
                   'ferrite-loaded composites sit above it.',
        'scenario_context': 'Rises with magnetic-filler volume fraction '
                            '(computed via the k↔µ Laplace analogy; '
                            'linear magnetostatics only — hysteresis and '
                            'remanence are out of scope). Particle '
                            'chaining/microstructure can push a real '
                            'part off the isotropic prediction.',
        'aliases': ['effectiveMu', 'mu_eff', 'muEff'],
        'scale_levels': [1],
    },
    'electricalConductivity': {
        'display_name': 'Electrical conductivity',
        'units': 'S/m',
        'meaning': 'How readily the material carries electrical '
                   'current.',
        'scenario_context': 'In conductive-filler composites this is '
                            'DOMINATED by percolation: below the '
                            'threshold the matrix insulates; just above '
                            'it conductivity jumps by many orders of '
                            'magnitude and quickly converges to the '
                            'filler-network value regardless of matrix.',
        'aliases': ['effectiveSigma', 'sigma_eff', 'sigmaEff'],
        'scale_levels': [1],
    },
    'percolationThreshold': {
        'display_name': 'Percolation threshold',
        'units': 'volume fraction',
        'meaning': 'The filler volume fraction at which a connected '
                   'conductive network first spans the material.',
        'scenario_context': 'Falls as filler aspect ratio rises (long '
                            'rods connect at far lower loading — '
                            'slender-rod limit ~0.7/aspect). Current '
                            'CNT models take 0.005 as a literature '
                            'assumption; a mesoscale engine deriving it '
                            'is planned.',
        'aliases': ['vf_c', 'vfC'],
        'scale_levels': [1, 2],
    },
    'totalEnergy': {
        'display_name': 'Total electronic energy',
        'units': 'Ha (also reported in eV)',
        'meaning': 'The DFT ground-state total energy of the computed '
                   'structure/fragment. Differences between systems are '
                   'the physically meaningful quantity, not the '
                   'absolute value.',
        'scenario_context': 'Comparing doped vs pristine fragments '
                            '(e.g. pyridine vs benzene) gives doping '
                            'energetics; fragment results carry the '
                            'fragment-vs-real-material caveat.',
        'aliases': ['totalEnergyHa', 'totalEnergyEv', 'energy',
                    'energyHa'],
        'scale_levels': [4],
    },
    'homoEnergy': {
        'display_name': 'HOMO energy',
        'units': 'eV',
        'meaning': 'Highest occupied molecular-orbital energy — how '
                   'tightly the most loosely-bound electrons are held. '
                   'A raised HOMO marks an electron DONOR (n-type '
                   'character).',
        'scenario_context': 'N-doping raises it (pyridine −6.53 vs '
                            'benzene −6.77 eV in the live p/i/n series). '
                            'Kohn-Sham orbital energies approximate the '
                            'true levels.',
        'aliases': ['homoEv'],
        'scale_levels': [4],
    },
    'lumoEnergy': {
        'display_name': 'LUMO energy',
        'units': 'eV',
        'meaning': 'Lowest unoccupied molecular-orbital energy — how '
                   'eagerly the system accepts an extra electron. A '
                   'lowered LUMO marks an electron ACCEPTOR (p-type '
                   'character).',
        'scenario_context': 'B-doping drops it (borabenzene −2.74 vs '
                            'benzene +0.12 eV in the live series).',
        'aliases': ['lumoEv'],
        'scale_levels': [4],
    },
    'homoLumoGap': {
        'display_name': 'HOMO–LUMO gap',
        'units': 'eV',
        'meaning': 'The frontier-orbital energy gap — the molecular '
                   'analogue of a band gap. Smaller gap = easier '
                   'electronic excitation / more semiconductor-like.',
        'scenario_context': 'Doping narrows it (benzene 6.89 → pyridine '
                            '5.70 → borabenzene 3.24 eV live). Kohn-Sham '
                            'gaps systematically underestimate true '
                            'gaps.',
        'aliases': ['gapEv'],
        'scale_levels': [4],
    },
    'shrinkageRate': {
        'display_name': 'Shrinkage rate',
        'units': '% (linear, melt → solid)',
        'meaning': 'How much the material contracts as it cools and '
                   'solidifies. High shrinkage warps printed parts and '
                   'pulls molded features off-dimension.',
        'scenario_context': 'Worsens with faster cooling and thicker '
                            'sections; filler loading (grog) reduces it '
                            'roughly in proportion to loading. The '
                            'formulation search treats it as a '
                            'minimize-target.',
        'aliases': ['ShrinkageRate'],
        'scale_levels': [0],
    },
    'shoreHardness': {
        'display_name': 'Shore hardness',
        'units': 'Shore A',
        'meaning': 'Resistance to surface indentation — the standard '
                   'quick measure of how hard/soft a wax or elastomer '
                   'feels.',
        'scenario_context': 'Drops sharply as temperature approaches '
                            'the melt onset; hard waxes (carnauba) and '
                            'rosin raise a blend\'s hardness per wt% '
                            '(quantified in the additive effects).',
        'aliases': ['ShoreHardness'],
        'scale_levels': [0],
    },
    'layerAdhesionStrength': {
        'display_name': 'Layer adhesion strength',
        'units': 'MPa',
        'meaning': 'How strongly one deposited print layer bonds to '
                   'the previous one — the weak direction of any '
                   'layered part.',
        'scenario_context': 'Improves with hotter deposition (more '
                            'remelt of the layer below) and tackifiers '
                            '(rosin); falls if the bead solidifies '
                            'before wetting the surface. Currently '
                            'UNPREDICTED in searches — no quantified '
                            'effect moves it (the standing rig-metrics '
                            'data ask).',
        'aliases': ['LayerAdhesionStrength'],
        'scale_levels': [0],
    },
    'flexuralModulus': {
        'display_name': 'Flexural modulus',
        'units': 'MPa',
        'meaning': 'Stiffness in bending — how much the material '
                   'resists flexing under load.',
        'scenario_context': 'Rises with hard-phase/filler loading, '
                            'falls with temperature; near the melt '
                            'window it collapses (why printed walls '
                            'need cooling before the next layer).',
        'aliases': ['FlexuralModulus'],
        'scale_levels': [0],
    },
    'viscosity': {
        'display_name': 'Melt viscosity',
        'units': 'Pa·s (melt, shear-dependent)',
        'meaning': 'The melt\'s resistance to flow — what the extruder '
                   'pushes against and what sets bead spreading after '
                   'deposition.',
        'scenario_context': 'Falls steeply with temperature above the '
                            'melt range; rises with filler loading. Too '
                            'low = beads slump; too high = extrusion '
                            'pressure spikes (ExtrusionPressure is the '
                            'other unpredicted rig metric).',
        'aliases': ['Viscosity'],
        'scale_levels': [0],
    },
    'meltRange': {
        'display_name': 'Melt range',
        'units': '°C',
        'meaning': 'The temperature span over which the material goes '
                   'solid → fully molten (waxes melt over a range, not '
                   'a point).',
        'scenario_context': 'Sets the processing window floor: the '
                            'whole blend must be molten to extrude. '
                            'Blend melt ranges are treated as priors '
                            '(~90–120 °C, no eutectics assumed) until '
                            'measured.',
        'aliases': ['meltLowC', 'meltHighC', 'MeltingPoint'],
        'scale_levels': [0],
    },
    'smokePoint': {
        'display_name': 'Smoking point',
        'units': '°C',
        'meaning': 'Where the material starts to degrade and give off '
                   'volatiles. The hard ceiling of any processing '
                   'window.',
        'scenario_context': 'The thermal gate enforces the no-volatiles '
                            'rule: NO component may reach its smoking '
                            'point inside the blend\'s melt window '
                            '(margin 20 °C by default).',
        'aliases': ['smokeLowC', 'smokeHighC', 'SmokingPoint'],
        'scale_levels': [0],
    },
}

_VOCAB_PROVENANCE = (
    'msci property vocabulary: formulation keys from the '
    'MISSING_MATERIALS_DATA worksheet; engine keys from ENGINE_REGISTRY '
    'result contracts; scenario notes from the live msci-0..24 studies.'
)

SEED_PROPERTY_MEANINGS = [
    {
        'name': key,
        'display_name': entry['display_name'],
        'units': entry['units'],
        'meaning': entry['meaning'],
        'scenario_context': entry['scenario_context'],
        'aliases_json': json.dumps(entry['aliases']),
        'scale_levels_json': json.dumps(entry['scale_levels']),
        'provenance_id': _VOCAB_PROVENANCE,
    }
    for key, entry in PROPERTY_MEANING_VOCAB.items()
]


def meaning_summary(row):
    """The page-facing view of one meaning row."""
    def loads(attr, fallback):
        try:
            return json.loads(getattr(row, attr, '') or fallback)
        except Exception:
            return json.loads(fallback)
    return {
        'key': getattr(row, 'name', ''),
        'label': getattr(row, 'display_name', ''),
        'units': getattr(row, 'units', ''),
        'meaning': getattr(row, 'meaning', ''),
        'scenarioContext': getattr(row, 'scenario_context', ''),
        'aliases': loads('aliases_json', '[]'),
        'scaleLevels': loads('scale_levels_json', '[]'),
    }


def meaning_index(manager):
    """{lowercased key/alias: meaning summary} over the live rows —
    the one lookup material_detail uses to attach meanings to values."""
    table = (manager.objectTables or {}).get(
        'MaterialPropertyMeaning', {})
    rows = table.values() if isinstance(table, dict) else table
    index = {}
    for row in rows:
        summary = meaning_summary(row)
        for key in [summary['key']] + summary['aliases']:
            if key:
                index[str(key).lower()] = summary
    return index
