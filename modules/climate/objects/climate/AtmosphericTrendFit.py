"""
@module climate.objects.climate.AtmosphericTrendFit

Row class AtmosphericTrendFit of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AtmosphericTrendFit(treeObject):
    """A fit over a series: a CLAIM with a method, stored so a
    later fit can disagree with it."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', method='quadratic',
                 window_from_year=0.0, window_to_year=0.0,
                 level=0.0, velocity=0.0, acceleration=0.0,
                 velocity_stderr=0.0, acceleration_stderr=0.0,
                 residual_rms=0.0, n_points=0, unit='ppm',
                 fitted_at='', horizon_year=0.0,
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        #: 'linear' | 'quadratic' | 'source-growth-rate'
        self.method = method
        self.window_from_year = window_from_year
        self.window_to_year = window_to_year
        #: value at the window's END (the projection's C0).
        self.level = level
        self.velocity = velocity
        self.acceleration = acceleration
        self.velocity_stderr = velocity_stderr
        self.acceleration_stderr = acceleration_stderr
        self.residual_rms = residual_rms
        self.n_points = n_points
        self.unit = unit
        self.fitted_at = fitted_at
        #: beyond this year the fit refuses to print a number.
        self.horizon_year = horizon_year
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
