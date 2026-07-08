"""
@module materialsScience.engines.transport_engine

Classical percolation theory for conductive-filler composites — the
regime continuum homogenization honestly CANNOT see (msci-23).

Physics: below the percolation threshold vf_c the conductive filler
sits as isolated islands and the composite conducts like the matrix
(the FEM homogenization at extreme contrast confirms this: sigma_eff
~= sigma_matrix). AT vf_c the filler forms a connected network and
conductivity jumps by orders of magnitude, following the classical
power law above threshold:

    sigma_eff = sigma_f * ((vf - vf_c) / (1 - vf_c)) ** t

with t the transport exponent (t ~= 1.3 in 2D, ~2.0 in 3D networks;
CNT/polymer literature t ~= 1.3-3, vf_c ~= 0.0005-0.01 for
high-aspect-ratio tubes).

Pure python, no dependencies, always available. Returns honest regime
labels + validity notes — the power law is an idealization; interface
resistance, tube waviness, and dispersion quality all shift real
measurements.
"""

from typing import Any, Dict


def capability() -> Dict[str, Any]:
    return {'available': True, 'library': 'analytic (pure python)',
            'model': 'classical percolation power law + dilute '
                     'Maxwell-Garnett below threshold'}


def percolation_conductivity(matrix_sigma: float, filler_sigma: float,
                             volume_fraction: float,
                             percolation_threshold: float = 0.005,
                             transport_exponent: float = 2.0
                             ) -> Dict[str, Any]:
    """Effective electrical conductivity of a conductive-filler
    composite across the percolation transition. All conductivities in
    S/m; volume_fraction and percolation_threshold as fractions."""
    if matrix_sigma <= 0 or filler_sigma <= 0:
        return {'ok': False,
                'error': 'conductivities must be positive (S/m)',
                'suggestion': {'knob': 'materials.*.electrical'
                                       'Conductivity',
                               'action': 'set both phases'}}
    if not (0 < volume_fraction < 1):
        return {'ok': False,
                'error': 'volumeFraction must be in (0, 1)'}
    if not (0 < percolation_threshold < 1):
        return {'ok': False,
                'error': 'percolationThreshold must be in (0, 1)'}
    if filler_sigma <= matrix_sigma:
        return {'ok': False,
                'error': 'percolation applies to CONDUCTIVE filler in '
                         'a less-conductive matrix (filler <= matrix '
                         'given)',
                'suggestion': {'knob': 'physics choice',
                               'action': 'use fem.effective-'
                                         'conductivity for comparable-'
                                         'phase composites'}}

    vf = volume_fraction
    vf_c = percolation_threshold
    if vf <= vf_c:
        # Dilute isolated inclusions: Maxwell-Garnett-order enhancement
        # of the MATRIX conductivity (the FEM homogenizer's regime).
        sigma = matrix_sigma * (1.0 + 3.0 * vf / (1.0 - vf))
        regime = 'below-threshold'
        note = ('isolated filler islands — the composite conducts '
                'like the matrix (dilute enhancement only); the FEM '
                'homogenization bound agrees in this regime')
    else:
        sigma = filler_sigma * (
            ((vf - vf_c) / (1.0 - vf_c)) ** transport_exponent)
        # The percolating network cannot conduct WORSE than the
        # non-percolating matrix path.
        sigma = max(sigma, matrix_sigma)
        regime = 'above-threshold'
        note = ('connected filler network — classical power law; real '
                'values shift with interface resistance, tube '
                'waviness, and dispersion quality')
    onset_margin = vf - vf_c
    return {
        'ok': True,
        'effectiveSigma': sigma,
        'regime': regime,
        'percolationThreshold': vf_c,
        'onsetMargin': onset_margin,
        'transportExponent': transport_exponent,
        'matrixSigma': matrix_sigma,
        'fillerSigma': filler_sigma,
        'conductivityGain': sigma / matrix_sigma,
        'note': note,
        'validity': 'idealized classical percolation — treat as an '
                    'order-of-magnitude ANALYSIS, not a measurement',
    }
