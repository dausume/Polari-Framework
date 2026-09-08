"""
@cross-cutting
@module waxprint.custom.voxel_resolution
@tags @xc:bindings

Print VOXELS — the whole sim is expressed in them (Dustin 2026-07-17:
"we do want to define things in terms of print voxels ... later melt
voxels using lasers"). A print voxel is the smallest REPEATABLE volume
element the machine can place under a given condition:

    voxel_xy = the deposited bead width (nozzle + viscous spread)
    voxel_z  = the layer height
    margin   = the trial-to-trial REPEATABILITY band, computed from the
               bead's sensitivity to a realistic ±3°C temperature-control
               wobble — "repeatable with smaller margins of error" made
               a number.

And the answer to "under these conditions AT THIS HEIGHT what resolution
can we get?": as a part grows, deposited heat accumulates and the
substrate the next bead lands on is warmer, so it cools slower and
spreads more — resolution degrades with height. resolution_profile()
returns that table.

Pure functions (explicit scalars in, dicts out) — the manager wiring is
in bead_analysis. This is also where the future MELT voxel (laser
ablation resolution) will attach; the seam is noted below.

@consumers
  - waxprint.custom.bead_analysis, waxprint.custom.print_optimizer
  - waxprint.bead_voxel_selftest
"""

from waxprint.custom import bead_cooling

MM = 1000.0                 # m → mm

#: In-plane resolution classes by voxel_xy (mm).
RESOLUTION_CLASSES = (
    (0.20, 'ultra-fine'),
    (0.35, 'fine'),
    (0.60, 'standard'),
    (float('inf'), 'coarse'),
)

#: Heights (mm) the resolution profile samples by default.
DEFAULT_PROFILE_HEIGHTS_MM = (0.2, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0)


def resolution_class(voxel_xy_mm):
    for ceiling, label in RESOLUTION_CLASSES:
        if voxel_xy_mm <= ceiling:
            return label
    return 'coarse'


def bead_width_m(nozzle_d_mm, flow_multiplier=1.1):
    """Nominal deposited road width before spread — the nozzle orifice
    times a small over-extrusion multiplier (standard FDM road model)."""
    return (nozzle_d_mm / MM) * flow_multiplier


def _spread_for_exit(exit_temp_c, width0_m, layer_h_m, feed, env, k_spread):
    r = bead_cooling.cool_bead(
        exit_temp_c=exit_temp_c, width_m=width0_m, layer_height_m=layer_h_m,
        density=feed['density'], cp=feed['cp'], latent_j_kg=feed['latent'],
        melt_point_c=feed['melt_point_c'],
        eta_ref_pa_s=feed['eta_ref'],
        viscosity_ref_temp_c=feed['eta_ref_temp'],
        viscosity_activation_k=feed['eta_act'],
        ambient_c=env['ambient_c'], bed_temp_c=env['bed_temp_c'],
        still_air_h=env['still_air_h'], wind_speed_m_s=env['wind_speed'],
        k_bed_w_mk=env['k_bed'], substrate_is_bed=env['substrate_is_bed'],
        substrate_temp_c=env.get('substrate_temp_c'), k_spread=k_spread)
    return r


def achievable_voxel(exit_temp_c, nozzle_d_mm, layer_height_mm, feed, env,
                     flow_multiplier=1.1, k_spread=0.3, control_band_c=3.0):
    """The print voxel achievable at one condition + substrate state.
    `feed` = {density, cp, latent, melt_point_c, eta_ref, eta_ref_temp,
    eta_act}; `env` = {ambient_c, bed_temp_c, still_air_h, wind_speed,
    k_bed, substrate_is_bed, substrate_temp_c?}."""
    width0 = bead_width_m(nozzle_d_mm, flow_multiplier)
    layer_h = layer_height_mm / MM

    r = _spread_for_exit(exit_temp_c, width0, layer_h, feed, env, k_spread)
    voxel_xy_mm = r['final_width_m'] * MM
    spread_mm = r['spread_m'] * MM

    # Repeatability margin: half the voxel-width swing across a realistic
    # ±control_band temperature wobble. Smaller = more repeatable.
    hi = _spread_for_exit(exit_temp_c + control_band_c, width0, layer_h,
                          feed, env, k_spread)['final_width_m'] * MM
    lo = _spread_for_exit(exit_temp_c - control_band_c, width0, layer_h,
                          feed, env, k_spread)['final_width_m'] * MM
    margin_mm = 0.5 * abs(hi - lo)

    width_error_mm = voxel_xy_mm - nozzle_d_mm    # systematic over-spread
    return {
        'voxel_xy_mm': voxel_xy_mm,
        'voxel_z_mm': layer_height_mm,
        'voxel_volume_mm3': voxel_xy_mm * voxel_xy_mm * layer_height_mm,
        'spread_mm': spread_mm,
        'width_error_mm': width_error_mm,
        'margin_mm': margin_mm,
        't_solidify_s': r['t_solidify_s'],
        'froze_in_window': r['froze_in_window'],
        'warp_index': r['warp_index'],
        'h_air_w_m2k': r['h_air_w_m2k'],
        'h_forced_w_m2k': r['h_forced_w_m2k'],
        'reynolds': r['reynolds'],
        'resolution_class': resolution_class(voxel_xy_mm),
    }


def substrate_temp_at_height(height_mm, bed_temp_c, ambient_c, melt_point_c,
                             bed_influence_mm=4.0, retained_fraction=0.55):
    """Substrate temperature the next bead lands on at a given build
    height. Near the bed it is the (cold) bed; higher up, accumulated
    deposition heat raises the local substrate toward a retained bulk
    temperature (a fraction of the way from ambient to the melt point).
    A monotone saturating model — the mechanism behind resolution loss
    with height."""
    bulk_max = ambient_c + retained_fraction * (melt_point_c - ambient_c)
    import math
    warmth = 1.0 - math.exp(-height_mm / max(1e-6, bed_influence_mm))
    base = bed_temp_c + (ambient_c - bed_temp_c) * warmth   # bed → ambient
    return base + (bulk_max - ambient_c) * warmth            # + heat build-up


def resolution_profile(exit_temp_c, nozzle_d_mm, layer_height_mm, feed, env,
                       heights_mm=DEFAULT_PROFILE_HEIGHTS_MM,
                       flow_multiplier=1.1, k_spread=0.3):
    """The "resolution at this height" table: for each build height,
    recompute the voxel against the warmer substrate at that height. Layer
    1 (bottom) sits on the cold bed; higher rows sit on warm wax."""
    rows = []
    for z in heights_mm:
        sub_c = substrate_temp_at_height(
            z, env['bed_temp_c'], env['ambient_c'], feed['melt_point_c'])
        env_z = dict(env)
        env_z['substrate_is_bed'] = z <= layer_height_mm * 1.5
        env_z['substrate_temp_c'] = sub_c
        v = achievable_voxel(exit_temp_c, nozzle_d_mm, layer_height_mm,
                             feed, env_z, flow_multiplier, k_spread)
        rows.append({
            'height_mm': z,
            'substrate_temp_c': sub_c,
            'voxel_xy_mm': v['voxel_xy_mm'],
            'voxel_z_mm': v['voxel_z_mm'],
            'spread_mm': v['spread_mm'],
            'margin_mm': v['margin_mm'],
            't_solidify_s': v['t_solidify_s'],
            'resolution_class': v['resolution_class'],
        })
    finest = min(rows, key=lambda r: r['voxel_xy_mm'])
    coarsest = max(rows, key=lambda r: r['voxel_xy_mm'])
    return {
        'rows': rows,
        'finest_voxel_xy_mm': finest['voxel_xy_mm'],
        'coarsest_voxel_xy_mm': coarsest['voxel_xy_mm'],
        'degradation_mm': coarsest['voxel_xy_mm'] - finest['voxel_xy_mm'],
    }

# NOTE (future — melt voxels): laser wax-ablation resolution will attach
# here as a sibling `melt_voxel()` — same voxel vocabulary (a removed
# volume element instead of a placed one), so the two processes share one
# resolution language. Not built this phase.
