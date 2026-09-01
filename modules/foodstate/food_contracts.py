"""
@module foodstate.food_contracts

fsp-0 — the property-domain CONTRACTS as data (the fam-1 shell
pattern): what a fully-described FoodState must be able to answer,
per domain, with the provenance rung each quantity is expected to
arrive by (the transform honesty ladder, plan §3):

  measured > mass-balance calculation > cited mechanistic model >
  USDA retention factor > REFUSE naming the gap.

Domains follow Dustin's ratified decomposition verbatim: composition
≠ structure ≠ physical ≠ chemical ≠ physiological — "two foods could
contain essentially the same grams of starch and water while behaving
very differently because one has gelatinized starch and the other has
intact granules." The final domain is named PHYSIOLOGICAL / FUNCTIONAL
PERFORMANCE (D8, ratified) and is DOWNSTREAM of the other four —
never baked into the food definition.

These are contracts, not schemas: quantities land as pspp
PropertyClaim rows on '<material>#<state>' subjects (claims-not-
values), so no new per-quantity class exists and none should.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - foodstate.food_api (GET /api/foodstate/contracts)
  - foodstate.selftest_foodstate
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = 'fsp-0 (FOOD_STATE_PSPP_PLAN.md §0/§3, ratified 2026-08-31)'


class FoodDomainContract(treeObject):
    """One property domain's contract: the quantities a FoodState
    answers there, each with its expected provenance rung and why it
    matters. Revisable data — the deliberate alternative to freezing
    per-quantity schemas before the physics basis exists."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # 'composition' | 'structure' | 'physical' | 'chemical' |
        # 'physiological-functional-performance'
        domain: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list of {quantity, unit, expected_provenance, why}.
        contract_json: str = '[]',
        # Which pspp EvidenceMethod rows quantities here may cite.
        evidence_methods_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.domain = domain
        self.display_name = display_name
        self.description = description
        self.contract_json = contract_json
        self.evidence_methods_json = evidence_methods_json
        self.provenance_id = provenance_id
        self.notes = notes


def _q(quantity, unit, expected_provenance, why):
    return {'quantity': quantity, 'unit': unit,
            'expected_provenance': expected_provenance, 'why': why}


SEED_FOOD_DOMAIN_CONTRACTS = [
    {'name': 'food-composition', 'domain': 'composition',
     'display_name': 'Food composition',
     'description': 'What the state IS, in constituent amounts — the '
                    'quantities transforms conserve or move; never '
                    'headline labels.',
     'contract_json': json.dumps([
         _q('water', 'g/100g', 'measured|mass-balance',
            'the constituent most transforms move (evaporation, '
            'concentration) — first-class, not a remainder'),
         _q('protein', 'g/100g', 'measured|retention-factor',
            'amount is conserved by cooking; STATE (denaturation) '
            'lives in the structure domain — the split that keeps '
            'cooking from writing "protein = lower"'),
         _q('lipids', 'g/100g', 'measured|mass-balance',
            'rendered fat leaves by mass balance, oxidation state is '
            'chemistry'),
         _q('carbohydrates-total', 'g/100g', 'measured',
            'roll-up of starch + sugars + fiber'),
         _q('starch', 'g/100g', 'measured|mass-balance',
            'grams here; gelatinization FRACTION is structure — same '
            'grams behave differently gelatinized vs intact'),
         _q('sugars', 'g/100g', 'measured|mass-balance',
            'free sugars incl. hydrolysis products'),
         _q('fiber', 'g/100g', 'measured|retention-factor',
            'ties to the nmp tolerance table doses'),
         _q('organic-acids', 'g/100g per species '
            '(citric|malic|acetic|lactic)', 'measured|mass-balance',
            'the acid arc backbone: concentration follows water loss '
            'by mass balance; speciation is chemistry (D4 scope)'),
         _q('amino-acids', 'g/100g per species',
            'measured|literature',
            'protein quality; v1 optional, contract names it'),
         _q('minerals', 'mg/100g per DietaryNutrient',
            'measured|retention-factor',
            'retention factors are THE cited bulk transform (nmp-3)'),
         _q('vitamins', 'per DietaryNutrient unit',
            'measured|retention-factor',
            'heat-labile — retention factor per cooking method'),
         _q('caffeine', 'mg/100g', 'measured|literature',
            'D4 scope stimulant example'),
         _q('capsaicinoids', 'mg/100g', 'measured|literature',
            'D4 scope; gastric-relevant'),
     ]),
     'evidence_methods_json': json.dumps(
         ['measured', 'literature', 'mass-balance',
          'retention-factor']),
     'notes': 'FDC (CC0) is the raw-state backbone (fsp-1).'},
    {'name': 'food-structure', 'domain': 'structure',
     'display_name': 'Food structure',
     'description': 'What arrangement the constituents are in — the '
                    'domain that makes identical compositions behave '
                    'differently.',
     'contract_json': json.dumps([
         _q('particle-size', 'm', 'measured|model',
            'chop/grind change THIS, not composition'),
         _q('porosity', 'fraction', 'measured|model', 'texture + '
            'digestion surface area'),
         _q('cell-integrity', 'fraction', 'model',
            'cell-wall breakdown under heat — drives nutrient '
            'accessibility'),
         _q('starch-gelatinization-fraction', 'fraction', 'model',
            'THE glycemic-kinetics driver; cited model behind an '
            'I5-style interface (fsp-2), refuses until calibrated'),
         _q('protein-denaturation-fraction', 'fraction', 'model',
            'digestibility driver; same I5 discipline'),
         _q('emulsion-state', 'label', 'measured|estimated',
            'fat delivery form'),
         _q('crystallinity', 'fraction', 'model|measured',
            'starch retrogradation, sugar states'),
         _q('viscosity', 'Pa·s', 'measured|model',
            'gastric-emptying relevant'),
         _q('water-activity', 'aw (0-1)', 'measured|model',
            'storage stability + microbial safety'),
     ]),
     'evidence_methods_json': json.dumps(
         ['measured', 'ml-prediction', 'estimated', 'literature']),
     'notes': 'structure fractions are PREDICTED-by-cited-model or '
              'refused — never asserted by the cooking step itself.'},
    {'name': 'food-physical', 'domain': 'physical',
     'display_name': 'Physical properties',
     'description': 'Bulk physical state.',
     'contract_json': json.dumps([
         _q('mass', 'g', 'measured|mass-balance',
            'the conservation anchor every transform is audited '
            'against'),
         _q('density', 'g/cm3', 'measured|mass-balance', ''),
         _q('temperature', 'C', 'measured',
            'transform input, also a claim on the state'),
         _q('volume', 'cm3', 'measured|mass-balance', ''),
     ]),
     'evidence_methods_json': json.dumps(
         ['measured', 'mass-balance']),
     'notes': ''},
    {'name': 'food-chemical', 'domain': 'chemical',
     'display_name': 'Chemical properties',
     'description': 'Solution chemistry of the state — the acid-'
                    'management backbone.',
     'contract_json': json.dumps([
         _q('pH', 'pH', 'measured|model',
            'measured where published; Henderson-Hasselbalch '
            'speciation CALCULATED only where pKa values are cited '
            '(fsp-3); else refuse'),
         _q('titratable-acidity', 'g/100g as dominant acid '
            '(or meq/100g)', 'measured|mass-balance',
            'follows organic-acid amounts + concentration'),
         _q('buffer-capacity', 'mmol/(pH·100g)', 'measured|model',
            'what the stomach actually works against — pH alone '
            'misleads'),
         _q('organic-acid-speciation', 'fraction per species',
            'model', 'pKa-based, cited constants only'),
         _q('redox-state', 'label|mV', 'measured|estimated',
            'lipid oxidation marker'),
         _q('ionic-strength', 'mol/L', 'model|estimated', ''),
     ]),
     'evidence_methods_json': json.dumps(
         ['measured', 'literature', 'mass-balance', 'estimated']),
     'notes': 'the tomato→sauce chain (fsp-3 acceptance) exercises '
              'every rung here.'},
    {'name': 'food-physiological',
     'domain': 'physiological-functional-performance',
     'display_name': 'Physiological / Functional Performance',
     'description': 'DOWNSTREAM of the other four domains (never '
                    'baked into the food): digestion, gastric '
                    'response, availability, satiety, stability, '
                    'meal-planning suitability. General-population '
                    'comfort framing — NOT medical advice, restated '
                    'on every payload (plan §6).',
     'contract_json': json.dumps([
         _q('digestibility-class', 'label', 'model|literature',
            'derived from structure (denaturation, cell integrity)'),
         _q('available-carb-kinetics-class', 'label',
            'model|literature',
            'gelatinization fraction + particle size → kinetics '
            'CLASS; feeds the nmp decision-9 glycemic-load gate '
            'honestly'),
         _q('glycemic-load-contribution', 'GL per serving',
            'literature|model',
            'published GI papers only (Sydney DB is proprietary — '
            'plan §6)'),
         _q('gastric-acid-response', 'direction + conditions',
            'conditional-prediction',
            'DIRECTION only with conditions (meal size, protein/fat '
            'load) + confidence — D6: no magnitude claims'),
         _q('satiety-class', 'label', 'literature|estimated',
            'labeled heuristic'),
         _q('storage-stability', 'label + days', 'literature|model',
            'water activity + chemistry driven'),
         _q('meal-planning-suitability', 'flags',
            'derived-from-the-above',
            'what nmp consumes from a terminal PreparedFoodState '
            '(fsp-6)'),
     ]),
     'evidence_methods_json': json.dumps(
         ['literature', 'conditional-prediction', 'estimated',
          'ml-prediction']),
     'notes': 'comfort heuristics for healthy adults; conditions '
              'and confidence ride every conditional prediction.'},
]

for _row in SEED_FOOD_DOMAIN_CONTRACTS:
    _row.setdefault('provenance_id', _PROV)


def contracts_report(manager):
    """Every domain contract with its quantities — the fsp-0 read
    surface; refusals for engines that do not exist yet are stated
    per quantity by the expected_provenance rung."""
    tables = getattr(manager, 'objectTables', None) or {}
    out = []
    for row in sorted((tables.get('FoodDomainContract')
                       or {}).values(),
                      key=lambda r: getattr(r, 'name', '')):
        out.append({
            'name': getattr(row, 'name', ''),
            'domain': getattr(row, 'domain', ''),
            'displayName': getattr(row, 'display_name', ''),
            'description': getattr(row, 'description', ''),
            'contract': json.loads(
                getattr(row, 'contract_json', '[]') or '[]'),
            'evidenceMethods': json.loads(
                getattr(row, 'evidence_methods_json', '[]') or '[]'),
            'notes': getattr(row, 'notes', ''),
        })
    return {'ok': True, 'schema': 'food-contracts/1',
            'contracts': out,
            'ladder': ('transform honesty ladder: measured > '
                       'mass-balance > cited model (I5 interface) > '
                       'USDA retention factor > REFUSE naming the '
                       'gap'),
            'principle': ('food rides the pspp core: states are '
                          'MaterialState rows, quantities are '
                          'PropertyClaim rows on '
                          "'<material>#<state>' subjects — cooking "
                          'writes underlying quantities, never '
                          'headline labels'),
            'boundary': ('physiological outputs are general-'
                         'population comfort heuristics, not '
                         'medical advice')}
