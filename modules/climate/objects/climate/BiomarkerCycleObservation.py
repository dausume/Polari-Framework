"""
@module climate.objects.climate.BiomarkerCycleObservation

Row class BiomarkerCycleObservation of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BiomarkerCycleObservation(treeObject):
    """One survey cycle's summary statistic for one biomarker."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', cycle='',
                 cycle_start_year=0.0, cycle_end_year=0.0,
                 mean=0.0, std_dev=0.0, median=0.0, n=0,
                 pct_5=0.0, pct_95=0.0, retrieval_ref='',
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        #: 'BIOPRO_D' / '2005-2006'
        self.cycle = cycle
        self.cycle_start_year = cycle_start_year
        self.cycle_end_year = cycle_end_year
        self.mean = mean
        self.std_dev = std_dev
        self.median = median
        self.n = n
        self.pct_5 = pct_5
        self.pct_95 = pct_95
        self.retrieval_ref = retrieval_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
