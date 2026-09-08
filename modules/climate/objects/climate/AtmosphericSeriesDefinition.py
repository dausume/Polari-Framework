"""
@module climate.objects.climate.AtmosphericSeriesDefinition

Row class AtmosphericSeriesDefinition of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import MEASURE_KINDS, SERIES_STATUS

class AtmosphericSeriesDefinition(treeObject):
    """One named measured series. A simulation binds THIS, not a
    chart — the chart is a view over it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', measure='other',
                 unit='ppm', cadence='annual', location='',
                 source_ref='', endpoint_ref='', status='prior',
                 first_year=0.0, last_year=0.0, value_field='value',
                 uncertainty_unit='', description='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.measure = (measure if measure in MEASURE_KINDS
                        else 'other')
        self.unit = unit
        self.cadence = cadence
        #: 'Mauna Loa', 'global marine surface', 'Antarctica
        #: (composite)', 'United States' …
        self.location = location
        #: GovSource.name that publishes it.
        self.source_ref = source_ref
        #: APIEndpoint.name that fetches it (polariApiProfiler).
        self.endpoint_ref = endpoint_ref
        #: SERIES_STATUS — engines gate on this.
        self.status = (status if status in SERIES_STATUS
                       else 'prior')
        #: Calendar years (negative = BCE). Derived on ingest, not
        #: asserted — a seeded range that disagrees with the rows
        #: is exactly the drift this project guards against.
        self.first_year = first_year
        self.last_year = last_year
        self.value_field = value_field
        self.uncertainty_unit = uncertainty_unit
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
