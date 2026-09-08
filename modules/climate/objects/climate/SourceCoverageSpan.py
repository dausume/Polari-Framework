"""
@module climate.objects.climate.SourceCoverageSpan

Row class SourceCoverageSpan of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import MEASUREMENT_KINDS

class SourceCoverageSpan(treeObject):
    """WHICH source covered WHICH stretch of a series' x-axis.

    The ice-core-vs-direct-measure seam, as data. One series may
    have many spans; a renderer colours/segments by span, a
    citation list is built from the spans a plotted window actually
    touches, and an overlap between two spans is a CROSS-CHECK
    opportunity, not a conflict to hide.
    """

    @treeObjectInit
    def __init__(self, name='', series_ref='', display_name='',
                 measurement_kind='direct-instrument',
                 from_year=0.0, to_year=0.0, source_ref='',
                 endpoint_ref='', archive_name='', instrument='',
                 resolution_years=0.0, citation_text='',
                 doi_or_url='', color='#888888',
                 typical_uncertainty=0.0, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.series_ref = series_ref
        self.display_name = display_name
        self.measurement_kind = (
            measurement_kind if measurement_kind in MEASUREMENT_KINDS
            else 'direct-instrument')
        #: calendar years CE; negative = BCE. An ice core span runs
        #: from -803719 to 1950-ish; Mauna Loa from 1959.
        self.from_year = from_year
        self.to_year = to_year
        self.source_ref = source_ref
        self.endpoint_ref = endpoint_ref
        #: 'EPICA Dome C', 'Law Dome DE08', 'Mauna Loa Observatory'
        self.archive_name = archive_name
        self.instrument = instrument
        #: mean spacing between samples — an 800 kyr ice core is
        #: NOT annual data, and a chart that implies it is lying.
        self.resolution_years = resolution_years
        self.citation_text = citation_text
        self.doi_or_url = doi_or_url
        self.color = color
        self.typical_uncertainty = typical_uncertainty
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
