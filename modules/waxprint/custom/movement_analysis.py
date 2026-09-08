"""
@cross-cutting
@module waxprint.custom.movement_analysis

Manager-facing wp-3: resolve the rows, run the wp-1 melt (for exit
viscosity + safety) and the wp-2 voxel (for spread + solidify time),
then score every movement pattern. Optionally evaluate AT A BUILD HEIGHT
(the substrate is warmer up high → the voxel coarsens → some movements
that pass low may go marginal), realizing Dustin's "at this height, these
movements, this resolution".

@consumers
  - waxprint.waxprint_api (/api/waxprint/movements)
  - waxprint.custom.print_optimizer
  - waxprint.movement_selftest
"""

from waxprint.custom import melt_analysis
from waxprint.custom import bead_analysis
from waxprint.custom import voxel_resolution
from waxprint.custom import movement_patterns
from waxprint.custom.bead_analysis import _feed_props, _env, _f


def movements_for_condition(manager, assembly, feedstock, condition,
                            height_mm=None):
    """Rows-based core: melt + voxel (optionally at height) + the movement
    verdicts. Returns (melt_result, voxel, movements). Used by the
    optimizer with ephemeral trial conditions."""
    melt_result, sim, _env_used = bead_analysis.voxel_for_condition(
        manager, assembly, feedstock, condition, height_mm=height_mm)
    cond = {
        'nozzle_d_mm': melt_result['nozzle_diameter_mm'],
        'print_speed_mm_s': _f(condition, 'print_speed_mm_s', 30.0),
        'layer_height_mm': _f(condition, 'layer_height_mm', 0.2),
    }
    feed_move = {
        'exit_viscosity_pa_s': melt_result['exit_viscosity_pa_s'],
        'density': _f(feedstock, 'density_kg_m3', 950.0),
    }
    movements = movement_patterns.evaluate_patterns(sim, cond, feed_move)
    return melt_result, sim, movements


def run_movements(manager, assembly_name, feedstock_name, condition_name,
                  height_mm=None):
    rows = bead_analysis._resolve(manager, assembly_name, feedstock_name,
                                  condition_name)
    if 'error' in rows:
        return rows
    melt_result, sim, movements = movements_for_condition(
        manager, rows['assembly'], rows['feedstock'], rows['condition'],
        height_mm=height_mm)
    return {
        'ok': True,
        'assembly': assembly_name,
        'feedstock': feedstock_name,
        'condition': condition_name,
        'height_mm': height_mm,
        'printable': melt_result['printable'],
        'thermally_safe': melt_result['thermally_safe'],
        'exit_temp_c': melt_result['exit_temp_c'],
        'voxel': sim,
        'movements': movements,
    }
