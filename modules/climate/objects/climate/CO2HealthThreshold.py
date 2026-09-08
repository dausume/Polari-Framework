"""
@module climate.objects.climate.CO2HealthThreshold

Row class CO2HealthThreshold of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import EVIDENCE_GRADES

class CO2HealthThreshold(treeObject):
    """One CO2 level at which something is claimed to happen to a
    person — WITH the grade of the evidence behind the claim.

    The grading IS the honesty (plan §5). A ventilation standard's
    1000 ppm and a controlled-exposure study's 1000 ppm are not the
    same kind of number and must never be averaged or drawn as one
    band.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', ppm=0.0,
                 unit='ppm', effect='', population='general',
                 exposure='chronic', evidence_grade='expert-judgement',
                 source_ref='', citation_text='', doi_or_url='',
                 is_differential=False, differential_over='',
                 contested_by='', color='#888888',
                 replaces_with='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.ppm = ppm
        self.unit = unit
        self.effect = effect
        #: 'general' | 'occupational' | 'sensitive' | 'children'
        self.population = population
        #: 'acute' | 'hours' | 'chronic'
        self.exposure = exposure
        self.evidence_grade = (
            evidence_grade if evidence_grade in EVIDENCE_GRADES
            else 'expert-judgement')
        self.source_ref = source_ref
        self.citation_text = citation_text
        self.doi_or_url = doi_or_url
        #: 🔑 ASHRAE's criterion is "700 ppm ABOVE OUTDOOR" — a
        #: DIFFERENTIAL, not an absolute. A differential threshold
        #: rises with outdoor CO2, which is why a fully compliant
        #: room can cross an absolute line without anything about
        #: the room changing. Engines must not mix the two.
        self.is_differential = is_differential
        self.differential_over = differential_over
        #: the studies that FAILED to replicate this one. A page
        #: that lists only supporting citations is advocacy.
        self.contested_by = contested_by
        self.color = color
        self.replaces_with = replaces_with
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
