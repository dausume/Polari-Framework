"""
@module climate.objects.climate.ObservedLevelReference

Row class ObservedLevelReference of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import SETTING_KINDS

class ObservedLevelReference(treeObject):
    """A MEASURED typical range for a kind of place - the reality
    check the modelled numbers are scored against.

    The coupled model computes what a room SHOULD sit at from
    volume, occupancy and air changes. This class holds what
    people have actually MEASURED in rooms like it. When the two
    disagree the model is wrong, and without these rows there is
    nothing to notice that with.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', setting='indoor',
                 locality='', space_kind='', ppm_low=0.0,
                 ppm_high=0.0, ppm_typical=0.0, source_ref='',
                 citation_text='', measurement_note='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.setting = (setting if setting in SETTING_KINDS
                        else 'indoor')
        self.locality = locality
        #: 'bedroom' | 'classroom' | 'office' | 'car-cabin' | ...
        self.space_kind = space_kind
        self.ppm_low = ppm_low
        self.ppm_high = ppm_high
        self.ppm_typical = ppm_typical
        self.source_ref = source_ref
        self.citation_text = citation_text
        self.measurement_note = measurement_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
