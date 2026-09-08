"""
@module climate.objects.climate.ExposureProjection

Row class ExposureProjection of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ExposureProjection(treeObject):
    """A computed crossing — STORED, not just returned, so the next
    ingest's answer can be compared against this one and the page
    can show its own answers moving."""

    @treeObjectInit
    def __init__(self, name='', threshold_ref='', space_ref='',
                 series_ref='', fit_ref='', method='quadratic',
                 crossing_year=0.0, crossing_year_low=0.0,
                 crossing_year_high=0.0, already_crossed=False,
                 outdoor_ppm_at_crossing=0.0, indoor_offset_ppm=0.0,
                 ventilation_knob_note='', refused=False,
                 refusal='', computed_at='', is_prior=False,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.threshold_ref = threshold_ref
        #: '' means the OUTDOOR crossing (no room).
        self.space_ref = space_ref
        self.series_ref = series_ref
        self.fit_ref = fit_ref
        self.method = method
        self.crossing_year = crossing_year
        #: the linear/quadratic bracket. One number with no band is
        #: the failure mode here (plan §7.5).
        self.crossing_year_low = crossing_year_low
        self.crossing_year_high = crossing_year_high
        self.already_crossed = already_crossed
        self.outdoor_ppm_at_crossing = outdoor_ppm_at_crossing
        self.indoor_offset_ppm = indoor_offset_ppm
        self.ventilation_knob_note = ventilation_knob_note
        self.refused = refused
        self.refusal = refusal
        self.computed_at = computed_at
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
