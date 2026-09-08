"""
@module climate.objects.climate_compress.SeriesCompressionRecord

Row class SeriesCompressionRecord of the climate module — one class per file (design §7), split
from climate_compress_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SeriesCompressionRecord(treeObject):
    """How one series was compressed — method, counts, per-span
    breakdown, and the re-ingest path back to the originals."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', method='',
                 target_points=0, original_points=0,
                 compressed_points=0, bin_width_years=0.0,
                 first_year=0.0, last_year=0.0,
                 # the deviation story: the largest swing any bin
                 # absorbed (up/down from its mean), the norm it was
                 # judged against, and how many bins were EXPANDED
                 # (raw points kept) for exceeding it.
                 max_deviation_up=0.0, max_deviation_down=0.0,
                 deviation_norm=0.0, expanded_bin_count=0,
                 spans_json='[]', reingest_note='',
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        self.method = method
        self.target_points = target_points
        self.original_points = original_points
        self.compressed_points = compressed_points
        self.bin_width_years = bin_width_years
        self.first_year = first_year
        self.last_year = last_year
        self.max_deviation_up = max_deviation_up
        self.max_deviation_down = max_deviation_down
        self.deviation_norm = deviation_norm
        self.expanded_bin_count = expanded_bin_count
        self.spans_json = spans_json
        self.reingest_note = reingest_note
        #: a record of an act performed on data — never a prior.
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
