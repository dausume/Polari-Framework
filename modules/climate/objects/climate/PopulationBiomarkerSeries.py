"""
@module climate.objects.climate.PopulationBiomarkerSeries

Row class PopulationBiomarkerSeries of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import SERIES_STATUS

class PopulationBiomarkerSeries(treeObject):
    """An NHANES-style biomarker/symptom series by survey cycle.

    Separate from AtmosphericSeriesDefinition because a survey
    cycle is not a year: it is a 2-year window with a sample
    design, and pretending otherwise is how a correlation becomes
    a fabrication.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', biomarker='',
                 unit='', source_ref='', endpoint_ref='',
                 xpt_column='', codebook_url='', status='prior',
                 population_note='', assay_note='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.biomarker = biomarker
        self.unit = unit
        self.source_ref = source_ref
        self.endpoint_ref = endpoint_ref
        #: 🔑 the opaque NHANES column ('LBXSC3SI'). The reader
        #: NEVER guesses what a column means — the mapping lives
        #: here, in a row, with the codebook that defines it.
        self.xpt_column = xpt_column
        self.codebook_url = codebook_url
        self.status = (status if status in SERIES_STATUS
                       else 'prior')
        self.population_note = population_note
        #: assay methods change between cycles; an unremarked
        #: method change looks exactly like a population trend.
        self.assay_note = assay_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
