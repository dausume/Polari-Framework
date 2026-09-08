"""
@module pspp.custom.structure_validation

gsp-5 (GEOPOLYMER_STRUCTURE_SAMPLING_PLAN): does a sampled cluster
LOOK amorphous the way real geopolymer gels do? Simulated powder
diffraction via the Debye scattering equation — the correct tool for
a FINITE, aperiodic cluster (the pymatgen periodic-XRD path on the
msci-engines worker requires a unit cell an amorphous sample honestly
does not have).

    I(q) = sum_ij f_i f_j sinc(q r_ij),  q = 4 pi sin(theta) / lambda

Honesty:
- atomic form factors are approximated as f_i = Z_i, q-independent —
  peak POSITIONS are trustworthy, relative intensities are first-order
  only (recorded in every payload's assumptions).
- the verdict band for the geopolymer gel halo (d ~ 3.0-3.3 A, i.e.
  ~27-30 deg 2-theta CuKa) is the widely reported range; treated as a
  sanity band, not a citation-grade overlay until the book figure is
  photographed as a DigitizedDataset.

@consumers
  - pspp.pspp_api (/api/pspp/structure/xrd)
  - pspp.structure_validation_selftest
"""

import numpy as np

WAVELENGTHS_A = {'CuKa': 1.5406, 'MoKa': 0.7107}

#: geopolymer gel amorphous-halo sanity band (2-theta deg, CuKa)
HALO_BAND_CUKA = (26.0, 30.5)

_F_APPROX_NOTE = ('atomic form factors approximated as f=Z '
                  '(q-independent) — halo POSITION is meaningful, '
                  'relative intensities first-order only')


def simulated_halo(sample, wavelength='CuKa', two_theta_max=60.0,
                   points=240):
    """Debye-equation powder pattern of one sampled cluster ->
    {ok, curve, halo, assumptions} | refusal."""
    if wavelength not in WAVELENGTHS_A:
        return {'ok': False,
                'refusal': f'unknown wavelength {wavelength!r}',
                'suggestion': f'available: {sorted(WAVELENGTHS_A)}'}
    lam = WAVELENGTHS_A[wavelength]
    atoms = sample.get('atoms') or []
    if len(atoms) < 4:
        return {'ok': False,
                'refusal': f'{len(atoms)} atoms is too few for a '
                           'meaningful pattern',
                'suggestion': 'sample more tetrahedra (nTetrahedra)'}
    from ase.data import atomic_numbers
    positions = np.array([a['position'] for a in atoms], float)
    z = np.array([atomic_numbers[a['element']] for a in atoms], float)

    two_theta = np.linspace(2.0, float(two_theta_max), int(points))
    q = 4.0 * np.pi * np.sin(np.radians(two_theta / 2.0)) / lam

    delta = positions[None, :, :] - positions[:, None, :]
    r = np.linalg.norm(delta, axis=-1)
    iu = np.triu_indices(len(atoms), k=1)
    r_pairs = r[iu]
    ff_pairs = (z[:, None] * z[None, :])[iu]

    qr = np.outer(q, r_pairs)
    with np.errstate(invalid='ignore', divide='ignore'):
        sinc = np.where(qr > 1e-12, np.sin(qr) / qr, 1.0)
    intensity = (z ** 2).sum() + 2.0 * (sinc * ff_pairs).sum(axis=1)
    intensity = np.maximum(intensity, 0.0)
    peak = float(intensity.max()) or 1.0
    intensity /= peak

    # A finite cluster's pattern is dominated by its small-angle
    # size envelope (monotone decay) — the structural halo is the
    # strongest RESIDUAL bump above a wide moving-average baseline.
    width = max(int(points) // 8, 5)
    kernel = np.ones(width) / width
    padded = np.concatenate([np.full(width, intensity[0]),
                             intensity,
                             np.full(width, intensity[-1])])
    baseline = np.convolve(padded, kernel, mode='same')[
        width:width + len(intensity)]
    residual = intensity - baseline

    peak_indices = [
        i for i in range(1, len(residual) - 1)
        if residual[i] > 0
        and residual[i] >= residual[i - 1]
        and residual[i] >= residual[i + 1]]
    if not peak_indices:
        return {'ok': False,
                'refusal': 'no residual peaks — the size envelope '
                           'is all there is at this cluster size',
                'suggestion': 'sample more tetrahedra (structure '
                              'sharpens with N) or widen '
                              'twoThetaMax/points',
                'counts': {'atoms': len(atoms)}}
    peaks = []
    for i in sorted(peak_indices, key=lambda i: -residual[i])[:6]:
        position = float(two_theta[i])
        peaks.append({
            'position2Theta': round(position, 2),
            'dSpacingA': round(
                lam / (2.0 * np.sin(np.radians(position / 2.0))), 3),
            'height': round(float(residual[i]), 6),
        })
    band = HALO_BAND_CUKA if wavelength == 'CuKa' else None
    in_band = (any(band[0] <= p['position2Theta'] <= band[1]
                   for p in peaks) if band else None)
    halo = dict(peaks[0])
    halo.update({'band': list(band) if band else None,
                 'anyPeakInBand': in_band})
    return {
        'ok': True, 'wavelength': wavelength,
        'curve': {
            'twoTheta': [round(float(v), 3) for v in two_theta],
            'intensity': [round(float(v), 5) for v in intensity],
            'residual': [round(float(v), 6) for v in residual],
        },
        'halo': halo,
        'peaks': peaks,
        'assumptions': [
            _F_APPROX_NOTE,
            'finite-cluster Debye pattern: no instrument broadening, '
            'no thermal factors',
            'small-angle size envelope removed by moving-average '
            'baseline — halo read from the residual',
            'halo band is the widely reported gel range (d~3.0-3.3 A)'
            ' — sanity band, not a digitized citation yet',
        ],
        'counts': {'atoms': len(atoms),
                   'pairs': int(len(r_pairs)),
                   'points': int(points)},
    }
