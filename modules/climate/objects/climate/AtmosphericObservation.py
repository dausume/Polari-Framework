"""
@module climate.objects.climate.AtmosphericObservation

Row class AtmosphericObservation of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AtmosphericObservation(treeObject):
    """One (series, year, value) point, with its span and its
    uncertainty. The actual data — queryable, re-ingestible."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', span_ref='',
                 year=0.0, value=0.0, uncertainty=0.0,
                 sample_count=0, revision='', retrieval_ref='',
                 # compressed aggregates only (climate_compress):
                 # how far the bin's raw values swung above/below
                 # the stored mean — so averaging can never hide
                 # the size of an excursion.
                 deviation_up=0.0, deviation_down=0.0,
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        #: the SourceCoverageSpan this point came from — so any
        #: single point can name its instrument and archive.
        self.span_ref = span_ref
        #: calendar year CE as a float (ice-core points are not
        #: integers; -803719.4 is a real x value).
        self.year = year
        self.value = value
        self.uncertainty = uncertainty
        self.sample_count = sample_count
        self.revision = revision
        self.deviation_up = deviation_up
        self.deviation_down = deviation_down
        #: SourceRetrieval.name — when WE copied it.
        self.retrieval_ref = retrieval_ref
        #: observations are MEASUREMENTS, never priors — the seed
        #: pass must not invent them.
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
