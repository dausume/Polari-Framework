"""
@module climate.objects.climate.CarbonSinkSeries

Row class CarbonSinkSeries of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import SERIES_STATUS

class CarbonSinkSeries(treeObject):
    """Land/ocean sink capacity and the sink FRACTION over time."""

    @treeObjectInit
    def __init__(self, name='', display_name='', sink_kind='land',
                 unit='GtC/yr', source_ref='', endpoint_ref='',
                 status='prior', description='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: 'land' | 'ocean' | 'atmospheric-fraction'
        self.sink_kind = sink_kind
        self.unit = unit
        self.source_ref = source_ref
        self.endpoint_ref = endpoint_ref
        self.status = (status if status in SERIES_STATUS
                       else 'prior')
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
