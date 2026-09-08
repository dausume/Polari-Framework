"""
@module climate.objects.climate.HumanEraDefinition

Row class HumanEraDefinition of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class HumanEraDefinition(treeObject):
    """A named stretch of human history/prehistory, so the CO2
    record can be read as "what did people actually breathe".

    ⚠ The era boundaries are archaeological consensus RANGES, not
    measurements, and life expectancy before vital registration is
    a skeletal-demography ESTIMATE with enormous error bars and a
    known bias (high infant mortality drags the mean far below
    adult lifespan). Both carry `is_prior` and a citation; the
    engines must never regress one against CO2 and call it a
    finding.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', from_year=0.0,
                 to_year=0.0, description='',
                 life_expectancy_at_birth=0.0,
                 life_expectancy_basis='',
                 life_expectancy_is_estimate=True,
                 population_estimate=0.0, citation_text='',
                 doi_or_url='', color='#888888', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: calendar years CE, negative = BCE.
        self.from_year = from_year
        self.to_year = to_year
        self.description = description
        self.life_expectancy_at_birth = life_expectancy_at_birth
        self.life_expectancy_basis = life_expectancy_basis
        self.life_expectancy_is_estimate = life_expectancy_is_estimate
        self.population_estimate = population_estimate
        self.citation_text = citation_text
        self.doi_or_url = doi_or_url
        self.color = color
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
