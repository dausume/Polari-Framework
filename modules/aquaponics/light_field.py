"""
@cross-cutting
@module aquaponics.light_field
@tags @xc:bindings

Plant-growth-sim phase 8 (2026-07-15) — the direct/collimated light
field engine. See aquaponics/light_basis.py's module docstring for the
full scope confirmation (direct light now; diffuse scattered light via
the existing FEM diffusion engine, and per-part-SHAPE-specific
incidence — flat leaf blades vs cylindrical stems/roots — are both
explicitly deferred to a later phase, per Dustin's own sequencing).

Three real physics/geometry pieces, each independently testable:

  1. SPECTRUM -> PPFD (spectrum_ppfd): a light source's broadband
     intensity_w_m2, filtered through its spectrum's photosynthetically
     -active fraction, converted to a real PPFD (umol/m^2/s) via
     PHOTON COUNTING — not an approximate energy-to-photon fudge
     constant. For 'blackbody' spectra this reuses electrodevice/
     photo_derive.py's proven numeric quadrature TECHNIQUE
     (E^2/(exp(E/kT)-1)-style integration), adapted from that module's
     eV/bandgap-threshold framing to this module's nm/PAR-band framing.

  2. INCIDENCE (cylinder_incidence_factor): how much of a bone's cross
     -section faces the light. Plant-part bones have no flat face/
     normal today (plant_skeleton.py's own bones are plain tapered
     cylinders) — modeled as sin(angle between the bone's own axis and
     the light direction), the correct projected-area law for a
     CYLINDER (broadside-on intercepts the most light, edge-on almost
     none). A future per-part-SHAPE refinement (a real leaf-blade
     normal, Lambert's cosine law) is explicitly deferred, not hidden
     as if already modeled.

  3. SELF-SHADING (self_shading_factor): a reduced-fidelity check —
     each OTHER bone is treated as a bounding SPHERE at its own
     midpoint (not a true capsule/cylinder occlusion test, another
     documented simplification); if the ray from a target bone toward
     the light source passes through any occluder's sphere, the target
     gets AMBIENT_SHADE_FRACTION rather than a hard 0 — a real shaded
     leaf still receives scattered/indirect light, an honest bridge to
     the future diffuse-light phase rather than an unphysical cliff.

per_part_absorption() combines all three against a planting's REAL,
freshly-generated skeleton (plant_skeleton.generate_skeleton — same
"always live-computed" pattern as water_slice_mesh) into a per-part
absorbed-PPFD value, ready to feed aquaponics.plant_stress's 'light'
stress-type curve as a computed override.

KNOWN LIMITATION, stated plainly rather than silently wrong:
self-shading only checks OTHER BONES as occluders, not SOIL — a root
bone buried underground will show a nonzero computed incidence here
despite being physically shielded by opaque soil. This has no effect
on growth today because no species seeds a 'light' StressResponseCurve
for its 'root' part (roots aren't light-sensitive in the first place —
see plant_stress_seed.py), but the raw per-bone/per-part numbers this
function returns should not be read as physically meaningful for
buried parts. A real soil-occlusion check is future work, same tier
as the diffuse-light and per-part-SHAPE deferrals above.

@consumers
  - aquaponics.plant_growth_normalized.advance_growth (via a local
    import — avoids a module-load-time import cycle through
    plant_skeleton -> plant_growth_normalized)
  - aquaponics.light_field_api (not yet built this pass — diagnostic
    read endpoints, same pattern as plant_growth_normalized_api)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 8
"""

import json
import math

#: Physical constants (SI).
PLANCK_H = 6.62607015e-34       # J*s
SPEED_OF_LIGHT = 2.99792458e8   # m/s
BOLTZMANN_K = 1.380649e-23      # J/K
AVOGADRO_N = 6.02214076e23      # 1/mol
#: Wien's displacement law constant, in nm*K (b = 2.8977719e-3 m*K).
WIEN_B_NM_K = 2.8977719e6

#: Standard PAR (photosynthetically active radiation) band, nm.
PAR_LOW_NM = 400.0
PAR_HIGH_NM = 700.0

#: A shaded bone still receives SOME scattered/indirect light — never
#: a hard 0 (the honest bridge to the future diffuse-light phase; see
#: module docstring point 3).
AMBIENT_SHADE_FRACTION = 0.15


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


# ---------------------------------------------------------------------
# 1. Spectrum -> PPFD (real photon counting)
# ---------------------------------------------------------------------

def _blackbody_energy_shape(wavelength_m, temperature_k):
    """Planck's law numerator only — the leading (2*pi*h*c^2)
    constant is dropped since it cancels in every ratio this module
    computes (PAR fraction, mean photon energy); this is a SHAPE
    function, not an absolute-radiance one."""
    x = (PLANCK_H * SPEED_OF_LIGHT) / (
        wavelength_m * BOLTZMANN_K * temperature_k)
    if x > 700.0:   # exp(700) already exceeds float range — negligible tail.
        return 0.0
    return 1.0 / (wavelength_m ** 5 * (math.exp(x) - 1.0))


def _blackbody_par_stats(temperature_k, points=2000):
    """(parEnergyFraction, meanParPhotonEnergyJ) for a temperature_k
    blackbody — the same numeric-quadrature TECHNIQUE electrodevice/
    photo_derive.py's ultimate_efficiency()/_photon_integral() use
    (E^2/(exp(E/kT)-1)-style integration), adapted from eV/bandgap
    framing to nm/PAR-band framing. parEnergyFraction is PAR-band
    energy ÷ TOTAL energy (across the whole emitted spectrum);
    meanParPhotonEnergyJ is PAR-band energy ÷ PAR-band photon COUNT —
    together these convert a broadband W/m^2 magnitude into a real
    PAR-band photon flux, no fudge constant needed."""
    peak_nm = WIEN_B_NM_K / max(temperature_k, 1.0)
    hi_nm = max(peak_nm * 25.0, 800.0)
    lo_nm = 1.0
    d_nm = (hi_nm - lo_nm) / points
    total_energy = par_energy = par_photon = 0.0
    for i in range(points):
        wl_nm = lo_nm + (i + 0.5) * d_nm
        wl_m = wl_nm * 1e-9
        energy_shape = _blackbody_energy_shape(wl_m, temperature_k)
        total_energy += energy_shape * d_nm
        if PAR_LOW_NM <= wl_nm <= PAR_HIGH_NM:
            photon_energy_j = PLANCK_H * SPEED_OF_LIGHT / wl_m
            photon_shape = energy_shape / photon_energy_j
            par_energy += energy_shape * d_nm
            par_photon += photon_shape * d_nm
    if total_energy <= 0 or par_photon <= 0:
        return 0.0, 0.0
    return par_energy / total_energy, par_energy / par_photon


def spectrum_ppfd(intensity_w_m2, spectrum):
    """A source's broadband intensity_w_m2, filtered through its
    spectrum, as a REAL PPFD (umol/m^2/s) — photon counting, not an
    approximate energy-to-photon constant. Never raises — an
    unsupported spectrum kind is an honest refusal."""
    if spectrum.kind == 'monochromatic':
        lo = spectrum.wavelength_nm - spectrum.bandwidth_nm / 2.0
        hi = spectrum.wavelength_nm + spectrum.bandwidth_nm / 2.0
        band_width = max(hi - lo, 1e-9)
        overlap = max(
            0.0, min(hi, PAR_HIGH_NM) - max(lo, PAR_LOW_NM))
        par_energy_fraction = overlap / band_width
        if par_energy_fraction <= 0 or spectrum.wavelength_nm <= 0:
            return {'ok': True, 'ppfd': 0.0, 'parEnergyFraction': 0.0,
                    'note': 'wavelength falls entirely outside the PAR '
                            f'band ({PAR_LOW_NM:.0f}-{PAR_HIGH_NM:.0f} nm)'}
        photon_energy_j = PLANCK_H * SPEED_OF_LIGHT / (
            spectrum.wavelength_nm * 1e-9)
        par_w_m2 = intensity_w_m2 * par_energy_fraction
        photon_flux_per_s_m2 = par_w_m2 / photon_energy_j
        ppfd = photon_flux_per_s_m2 / AVOGADRO_N * 1e6
        return {'ok': True, 'ppfd': round(ppfd, 4),
                'parEnergyFraction': round(par_energy_fraction, 4),
                'tier': 'monochromatic'}
    if spectrum.kind == 'blackbody':
        par_energy_fraction, mean_par_photon_energy_j = \
            _blackbody_par_stats(spectrum.temperature_k)
        if mean_par_photon_energy_j <= 0:
            return {'ok': True, 'ppfd': 0.0, 'parEnergyFraction': 0.0,
                    'note': 'negligible PAR-band emission at this '
                            'temperature_k'}
        par_w_m2 = intensity_w_m2 * par_energy_fraction
        photon_flux_per_s_m2 = par_w_m2 / mean_par_photon_energy_j
        ppfd = photon_flux_per_s_m2 / AVOGADRO_N * 1e6
        return {'ok': True, 'ppfd': round(ppfd, 4),
                'parEnergyFraction': round(par_energy_fraction, 4),
                'tier': 'blackbody',
                'meanParPhotonEnergyJ': mean_par_photon_energy_j}
    return {'ok': False,
            'error': f"unsupported LightSpectrumDefinition.kind "
                     f"'{spectrum.kind}' (expected 'monochromatic' or "
                     "'blackbody')"}


# ---------------------------------------------------------------------
# 2/3. Direction, incidence, self-shading (pure vector geometry)
# ---------------------------------------------------------------------

def _normalize(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def direction_from_az_el(azimuth_deg, elevation_deg):
    """Unit vector the light TRAVELS along (source -> target), z-up
    frame matching plant_skeleton.py's own convention. azimuth: the
    compass bearing the source sits AT (0=north/+y, 90=east/+x,
    clockwise); elevation: degrees above the horizon (90=straight
    overhead)."""
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    source_direction = (math.sin(az) * math.cos(el),
                        math.cos(az) * math.cos(el),
                        math.sin(el))
    # Light travels the OPPOSITE way from where the source sits.
    return tuple(-c for c in source_direction)


def cylinder_incidence_factor(bone_axis_unit, light_dir_unit):
    """sin(angle between the bone's axis and the light's travel
    direction) — the projected cross-section a CYLINDER presents to a
    collimated beam (see module docstring point 2)."""
    dot = sum(a * d for a, d in zip(bone_axis_unit, light_dir_unit))
    return math.sqrt(max(0.0, 1.0 - dot * dot))


def _point_ray_distance(point, ray_origin, ray_dir_unit):
    """Distance from `point` to the ray {ray_origin + t*ray_dir_unit :
    t >= 0}, and the parameter t of the closest approach. Returns
    (None, None) when the closest approach falls BEHIND the ray
    origin (t < 0 — not a real occluder for a ray traveling forward)."""
    to_point = tuple(p - o for p, o in zip(point, ray_origin))
    t = sum(a * b for a, b in zip(to_point, ray_dir_unit))
    if t < 0:
        return None, None
    closest = tuple(o + t * d for o, d in zip(ray_origin, ray_dir_unit))
    dist = math.sqrt(sum((c - p) ** 2 for c, p in zip(closest, point)))
    return dist, t


def self_shading_factor(bones, target_bone, light_dir_unit):
    """1.0 (unshaded) or AMBIENT_SHADE_FRACTION (occluded by some
    OTHER bone, approximated as a bounding sphere at its midpoint —
    see module docstring point 3)."""
    target_mid = tuple(
        (a + b) / 2.0 for a, b in
        zip(target_bone['startPointMm'], target_bone['endPointMm']))
    toward_source = tuple(-c for c in light_dir_unit)
    for other in bones:
        if other['id'] == target_bone['id']:
            continue
        other_mid = tuple(
            (a + b) / 2.0 for a, b in
            zip(other['startPointMm'], other['endPointMm']))
        radius = max(other['startRadiusMm'], other['endRadiusMm'])
        dist, t = _point_ray_distance(other_mid, target_mid,
                                      toward_source)
        if dist is not None and t > 1e-6 and dist < radius:
            return AMBIENT_SHADE_FRACTION
    return 1.0


# ---------------------------------------------------------------------
# The combined per-part read
# ---------------------------------------------------------------------

def per_part_absorption(manager, planting_name, light_source_name,
                        max_generations=None, max_bones=None):
    """The full pipeline: LightSourceDefinition + LightSpectrumDefinition
    -> real PPFD magnitude; planting's REAL, freshly-generated skeleton
    -> per-bone incidence + self-shading; aggregated PER PART (mean
    across that part's bones — a surface-area-weighted mean is future
    work once per-part SHAPE is modeled, see module docstring)."""
    from aquaponics.plant_skeleton import (
        DEFAULT_MAX_BONES, DEFAULT_MAX_GENERATIONS, generate_skeleton,
    )
    source = _named(manager, 'LightSourceDefinition', light_source_name)
    if source is None:
        return {'ok': False,
                'error': f"no LightSourceDefinition named "
                         f"'{light_source_name}'"}
    spectrum = _named(manager, 'LightSpectrumDefinition',
                      source.spectrum_name)
    if spectrum is None:
        return {'ok': False,
                'error': f"LightSourceDefinition '{light_source_name}' "
                         f"names spectrum '{source.spectrum_name}' but "
                         'no LightSpectrumDefinition with that name '
                         'exists',
                'suggestion': {
                    'knob': 'LightSpectrumDefinition',
                    'action': 'seed a spectrum row, or fix '
                              'LightSourceDefinition.spectrum_name'}}
    ppfd_result = spectrum_ppfd(source.intensity_w_m2, spectrum)
    if not ppfd_result.get('ok'):
        return ppfd_result

    skeleton = generate_skeleton(
        manager, planting_name,
        max_generations=max_generations or DEFAULT_MAX_GENERATIONS,
        max_bones=max_bones or DEFAULT_MAX_BONES)
    if not skeleton.get('ok'):
        return skeleton
    bones = skeleton['bones']
    if not bones:
        return {'ok': True, 'planting': planting_name,
                'partAbsorptionPpfd': {},
                'note': 'no bones generated yet (zero growth) — '
                        'nothing to illuminate.'}

    position_mm = None
    light_dir = None
    if source.source_kind == 'directional':
        light_dir = direction_from_az_el(source.azimuth_deg,
                                         source.elevation_deg)
    elif source.source_kind == 'point':
        try:
            position_mm = tuple(
                json.loads(source.position_mm_json or '[0,0,0]'))
        except Exception:
            position_mm = (0.0, 0.0, 0.0)
    else:
        return {'ok': False,
                'error': f"unsupported LightSourceDefinition.source_kind "
                         f"'{source.source_kind}'"}

    per_bone = {}
    for bone in bones:
        axis = tuple(b - a for a, b in
                     zip(bone['startPointMm'], bone['endPointMm']))
        length = math.sqrt(sum(c * c for c in axis))
        if length < 1e-9:
            continue
        axis_unit = tuple(c / length for c in axis)
        if source.source_kind == 'point':
            mid = tuple((a + b) / 2.0 for a, b in
                       zip(bone['startPointMm'], bone['endPointMm']))
            bone_light_dir = _normalize(
                tuple(m - p for m, p in zip(mid, position_mm)))
        else:
            bone_light_dir = light_dir
        incidence = cylinder_incidence_factor(axis_unit, bone_light_dir)
        shading = self_shading_factor(bones, bone, bone_light_dir)
        per_bone[bone['id']] = {
            'part': bone['part'],
            'incidenceFactor': round(incidence, 4),
            'shadingFactor': shading,
            'absorbedPpfd': round(
                ppfd_result['ppfd'] * incidence * shading, 3),
        }

    part_totals, part_counts = {}, {}
    for info in per_bone.values():
        part_totals[info['part']] = part_totals.get(
            info['part'], 0.0) + info['absorbedPpfd']
        part_counts[info['part']] = part_counts.get(info['part'], 0) + 1
    part_absorption = {
        p: round(part_totals[p] / part_counts[p], 3) for p in part_totals}

    return {
        'ok': True,
        'planting': planting_name,
        'lightSource': light_source_name,
        'spectrum': source.spectrum_name,
        'sourcePpfd': ppfd_result['ppfd'],
        'parEnergyFraction': ppfd_result.get('parEnergyFraction'),
        'partAbsorptionPpfd': part_absorption,
        'perBone': per_bone,
        'boneCount': len(bones),
        'note': 'direct/collimated light only — cylinder-projection '
                'incidence + reduced-fidelity sphere-occlusion self-'
                'shading. Diffuse scattered light and per-part-SHAPE-'
                'specific incidence (flat leaf blades vs cylindrical '
                'stems/roots) are both explicitly deferred, not '
                'modeled here.',
    }
