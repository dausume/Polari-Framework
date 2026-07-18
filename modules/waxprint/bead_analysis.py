"""
@cross-cutting
@module waxprint.bead_analysis

Manager-facing layer for wp-2: resolve an assembly + feedstock + condition
by name, run the wp-1 two-zone melt to get the nozzle EXIT temperature and
whether the melt is even printable, then compute the achievable print
VOXEL and the resolution-at-height profile. Physics is in bead_cooling /
voxel_resolution; HTTP is in waxprint_api.

@consumers
  - waxprint.waxprint_api (/api/waxprint/voxel, /resolution-profile)
  - waxprint.print_optimizer
  - waxprint.selftest_bead_voxel
"""

from waxprint import melt_analysis, voxel_resolution
from waxprint.bead_cooling import wind_speed_from_vector
from waxprint.waxprint_basis import CONVECTION_PRESETS


def _f(obj, attr, default=0.0):
    try:
        return float(getattr(obj, attr, default))
    except (TypeError, ValueError):
        return default


def _feed_props(feedstock):
    return {
        'density': _f(feedstock, 'density_kg_m3', 950.0),
        'cp': _f(feedstock, 'specific_heat_j_kgk', 2100.0),
        'latent': _f(feedstock, 'latent_heat_fusion_j_kg', 180000.0),
        'melt_point_c': _f(feedstock, 'melt_point_c', 82.0),
        'eta_ref': _f(feedstock, 'viscosity_ref_pa_s', 5.0),
        'eta_ref_temp': _f(feedstock, 'viscosity_ref_temp_c', 100.0),
        'eta_act': _f(feedstock, 'viscosity_activation_k', 6000.0),
    }


def _env(manager, assembly, condition):
    """Environment payload for the bead: convection baseline from the
    preset, forced-convection wind speed from the fan vector, bed
    conductivity from the bed material row."""
    preset = getattr(condition, 'convection_preset', 'still-air')
    still_air_h = CONVECTION_PRESETS.get(preset, 8.0)
    wind = wind_speed_from_vector(
        _f(condition, 'fan_wind_vx_mm_s'), _f(condition, 'fan_wind_vy_mm_s'),
        _f(condition, 'fan_wind_vz_mm_s'))
    bed_name = getattr(assembly, 'bed_material_ref', '') or ''
    bed = melt_analysis.find_row(manager, 'DeviceMaterialDefinition', bed_name)
    k_bed = _f(bed, 'thermal_conductivity_w_mk', 1.1) if bed else 1.1
    return {
        'ambient_c': _f(condition, 'ambient_temp_c', 22.0),
        'bed_temp_c': _f(condition, 'bed_temp_c', 22.0),
        'still_air_h': still_air_h,
        'wind_speed': wind,
        'k_bed': k_bed,
        'substrate_is_bed': True,
        'bed_material': bed_name,
    }


def voxel_for_condition(manager, assembly, feedstock, condition,
                        height_mm=None):
    """Rows-based core: melt (with safety) + achievable voxel, optionally
    at a build height (warmer substrate). Returns (melt_result, voxel,
    env). Used by run_voxel and the optimizer (ephemeral conditions)."""
    melt_result, _ = melt_analysis.evaluate_melt(
        manager, assembly, feedstock, condition)
    exit_temp_c = melt_result['exit_temp_c']
    nozzle_d_mm = melt_result['nozzle_diameter_mm']
    layer_h_mm = _f(condition, 'layer_height_mm', 0.2)
    feed = _feed_props(feedstock)
    env = _env(manager, assembly, condition)
    if height_mm is not None and height_mm > layer_h_mm * 1.5:
        sub_c = voxel_resolution.substrate_temp_at_height(
            height_mm, env['bed_temp_c'], env['ambient_c'],
            feed['melt_point_c'])
        env = dict(env, substrate_is_bed=False, substrate_temp_c=sub_c)
    voxel = voxel_resolution.achievable_voxel(
        exit_temp_c, nozzle_d_mm, layer_h_mm, feed, env)
    return melt_result, voxel, env


def run_voxel(manager, assembly_name, feedstock_name, condition_name):
    """Full wp-2 result: the melt (with its safety verdict) + the layer-1
    achievable voxel. Returns ok/error like run_melt."""
    rows = _resolve(manager, assembly_name, feedstock_name, condition_name)
    if 'error' in rows:
        return rows
    melt_result, voxel, env = voxel_for_condition(
        manager, rows['assembly'], rows['feedstock'], rows['condition'])
    return {
        'ok': True,
        'assembly': assembly_name,
        'feedstock': feedstock_name,
        'condition': condition_name,
        'printable': melt_result['printable'],
        'thermally_safe': melt_result['thermally_safe'],
        'exit_temp_c': melt_result['exit_temp_c'],
        'bed_material': env['bed_material'],
        'voxel': voxel,
        'melt_findings': melt_result['findings'],
    }


def _resolve(manager, assembly_name, feedstock_name, condition_name):
    """Resolve the three named rows or return an error dict naming misses."""
    a = melt_analysis.find_row(manager, 'PrinterAssemblyDefinition',
                               assembly_name)
    f = melt_analysis.find_row(manager, 'WaxFeedstockDefinition',
                               feedstock_name)
    c = melt_analysis.find_row(manager, 'PrintConditionDefinition',
                               condition_name)
    missing = []
    if a is None:
        missing.append(f'PrinterAssemblyDefinition:{assembly_name}')
    if f is None:
        missing.append(f'WaxFeedstockDefinition:{feedstock_name}')
    if c is None:
        missing.append(f'PrintConditionDefinition:{condition_name}')
    if missing:
        return {'ok': False, 'error': 'row(s) not found', 'missing': missing}
    return {'assembly': a, 'feedstock': f, 'condition': c}


def run_resolution_profile(manager, assembly_name, feedstock_name,
                           condition_name, heights_mm=None):
    """The resolution-at-height table for one condition."""
    melt = melt_analysis.run_melt(manager, assembly_name, feedstock_name,
                                  condition_name)
    if not melt.get('ok'):
        return melt
    assembly = melt_analysis.find_row(manager, 'PrinterAssemblyDefinition',
                                      assembly_name)
    feedstock = melt_analysis.find_row(manager, 'WaxFeedstockDefinition',
                                       feedstock_name)
    condition = melt_analysis.find_row(manager, 'PrintConditionDefinition',
                                       condition_name)
    exit_temp_c = melt['result']['exit_temp_c']
    nozzle_d_mm = melt['result']['nozzle_diameter_mm']
    layer_h_mm = _f(condition, 'layer_height_mm', 0.2)
    feed = _feed_props(feedstock)
    env = _env(manager, assembly, condition)

    kwargs = {}
    if heights_mm:
        kwargs['heights_mm'] = tuple(heights_mm)
    profile = voxel_resolution.resolution_profile(
        exit_temp_c, nozzle_d_mm, layer_h_mm, feed, env, **kwargs)
    return {
        'ok': True,
        'assembly': assembly_name,
        'feedstock': feedstock_name,
        'condition': condition_name,
        'printable': melt['result']['printable'],
        'exit_temp_c': exit_temp_c,
        'profile': profile,
    }
