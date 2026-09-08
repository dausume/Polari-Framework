"""
@module climate.objects.climate.SymptomOnsetClaim

Row class SymptomOnsetClaim of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import EVIDENCE_GRADES

class SymptomOnsetClaim(treeObject):
    """ONE SOURCE SAYS ONE SYMPTOM APPEARS AT ONE LEVEL.

    This is the join that makes the ladder citable. It is
    deliberately not a field on the threshold row: two sources
    disagree about where a symptom starts, and the object model
    has to be able to hold both claims at once rather than forcing
    a page to pick a winner silently.

    A claim carries its own evidence grade, because the grade
    belongs to the CLAIM and not to the symptom - "headache at
    700 ppm" (epidemiological association) and "headache at 40000
    ppm" (occupational medicine) are not equally certain and are
    not equally severe.
    """

    @treeObjectInit
    def __init__(self, name='', symptom_ref='', ppm_from=0.0,
                 ppm_to=0.0, source_ref='',
                 evidence_grade='expert-judgement', exposure='',
                 onset_note='', population='general',
                 quote='', is_lethal=False, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.symptom_ref = symptom_ref
        #: the band this source attributes the symptom to. ppm_to
        #: of 0 means "and above".
        self.ppm_from = ppm_from
        self.ppm_to = ppm_to
        self.source_ref = source_ref
        self.evidence_grade = (
            evidence_grade if evidence_grade in EVIDENCE_GRADES
            else 'expert-judgement')
        self.exposure = exposure
        self.onset_note = onset_note
        self.population = population
        #: the source's OWN words where they are short enough to
        #: quote. A paraphrase of a health claim is a new claim.
        self.quote = quote
        self.is_lethal = is_lethal
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
