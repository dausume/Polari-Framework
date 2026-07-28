"""
@module supplychain.sourcing_basis

Material/product SOURCING as data (Dustin 2026-07-28): who can supply
a thing, what they charge (dated, cited price observations), and a
DEFINABLE preference ladder over source categories.

Category flags are independent booleans precisely so sources can
OVERLAP definitions (a supplier can be local AND commercial AND
eco-friendly at once); the preference policy ranks by predicate over
those flags, first-match-wins.

A source can also be a CUSTOMER: demands_json lists what the business
behind it would buy (e.g. a hydroponics farm supplies wax-source
biomass and wants geopolymer self-watering pots + shelves) — the
mutual-supply loops the OSEB thesis is about.

@consumers polariServer seed_pairs, supplychain.sourcing_analysis
"""

from objectTreeDecorators import treeObject, treeObjectInit

SOURCE_AVAILABILITY = ('available', 'potential', 'defunct')


class SupplySourceProfile(treeObject):
    """One source of one-or-more items, with overlap-capable
    category flags and an availability state ('potential' = a
    business model that COULD supply this, not one that does)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', supplier_name='',
                 url='', is_open_source=False, is_commercial=False,
                 is_local=False, is_polari=False,
                 is_eco_friendly=False, availability='available',
                 supplies_json='[]', demands_json='[]',
                 business_model_ref='', locality_note='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.supplier_name = supplier_name
        self.url = url
        self.is_open_source = is_open_source
        self.is_commercial = is_commercial
        self.is_local = is_local
        self.is_polari = is_polari
        self.is_eco_friendly = is_eco_friendly
        self.availability = (availability
                             if availability in SOURCE_AVAILABILITY
                             else 'available')
        #: JSON list of item_refs this source supplies.
        self.supplies_json = supplies_json
        #: JSON list of item_refs the business behind this source
        #: would BUY (demand side of the loop).
        self.demands_json = demands_json
        #: BusinessModelDefinition.name (economy tree) when the
        #: source IS a modeled business (alternate-source-as-model).
        self.business_model_ref = business_model_ref
        self.locality_note = locality_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class PriceCitation(treeObject):
    """One dated, cited price observation — never a bare number.
    is_estimate=True whenever the figure is inferred (a range, a
    'from' price) rather than a listed exact price."""

    @treeObjectInit
    def __init__(self, name='', source_ref='', item_ref='',
                 price=0.0, currency='USD', amount=0.0,
                 amount_unit='kg', observed_at='', citation_url='',
                 citation_note='', is_estimate=False, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.source_ref = source_ref
        self.item_ref = item_ref
        #: Price for `amount` of `amount_unit` (e.g. 109.0 for
        #: 50 lb) — normalization happens in analysis, the citation
        #: stays exactly as observed.
        self.price = price
        self.currency = currency
        self.amount = amount
        self.amount_unit = amount_unit
        #: ISO date-time of the observation.
        self.observed_at = observed_at
        self.citation_url = citation_url
        self.citation_note = citation_note
        self.is_estimate = is_estimate
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ProductInputRequirement(treeObject):
    """THE FULL required-input map for one product: every role the
    product needs filled, with fraction ranges and ALL candidate
    item_refs per role — cited or not (uncited candidates are the
    research gaps, listed not hidden). This is what lets a formula
    search know its complete feedstock space."""

    @treeObjectInit
    def __init__(self, name='', display_name='', product_item_ref='',
                 roles_json='[]', substitutes_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.product_item_ref = product_item_ref
        #: JSON list of {role, purpose, min_fraction, max_fraction,
        #: candidates: [item_ref, ...]} — fractions by mass.
        self.roles_json = roles_json
        #: JSON list of {item_ref, caveats: [...], notes} — WHOLE-
        #: product substitutes (not role candidates): things that can
        #: stand in for the finished product, caveats stated as data
        #: (e.g. contains plastics / fume emission) so cost
        #: comparisons never hide what the cheaper option costs you.
        self.substitutes_json = substitutes_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ProductFormula(treeObject):
    """One CONCRETE blend of a product: component item_refs with
    mass fractions, each filling a requirement role. Costing turns
    this into USD/kg via the citations — the material-cost-per-kg
    scoring term for simulation results."""

    @treeObjectInit
    def __init__(self, name='', display_name='', product_item_ref='',
                 components_json='[]', status='candidate',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.product_item_ref = product_item_ref
        #: JSON list of {item_ref, role, fraction} — mass fractions
        #: that must satisfy the product's ProductInputRequirement.
        self.components_json = components_json
        self.status = status
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class SourcePreferencePolicy(treeObject):
    """The DEFINABLE ladder: ordered rules, each a predicate over the
    source flags; first match wins; unmatched sources get
    default_rank. Policies are rows — edit the ladder, not code."""

    @treeObjectInit
    def __init__(self, name='', display_name='', rules_json='[]',
                 default_rank=99, is_active=True, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: JSON list of {rank, label, require: {flag: bool, ...},
        #: availability?: [...]} — evaluated in order.
        self.rules_json = rules_json
        self.default_rank = default_rank
        self.is_active = is_active
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
