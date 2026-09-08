"""
@module climate.objects.climate.HealthSymptomDefinition

Row class HealthSymptomDefinition of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class HealthSymptomDefinition(treeObject):
    """One symptom, as a row.

    Symptoms are their own objects because the SAME symptom
    appears at several concentrations from several sources -
    headache is reported at 700 ppm by epidemiology and at 4
    percent by occupational medicine - and a page that restates it
    per threshold cannot show that, nor rank the ladder.

    `is_reversible` matters more here than anywhere: OSHA states
    that low-level CO2 intoxication is "sudden and reversible" and
    dissipates within minutes of leaving the exposure. A ladder
    that lists convulsions next to headache without saying which
    ones undo themselves is frightening rather than informative.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', body_system='',
                 severity_rank=1, is_reversible=True,
                 description='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: 'central-nervous' | 'respiratory' | 'cardiovascular' |
        #: 'metabolic' | 'sensory' | 'general'
        self.body_system = body_system
        #: SYMPTOM_SEVERITY key. Orders the ladder.
        self.severity_rank = severity_rank
        self.is_reversible = is_reversible
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
