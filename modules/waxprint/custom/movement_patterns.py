"""
@cross-cutting
@module waxprint.custom.movement_patterns
@tags @xc:bindings

wp-3 — prove the basic MOVEMENTS a 3D printer relies on are viable under
a given melt+bead condition, and name the limit when they are not
(Dustin 2026-07-17: "prove the basic movements often used by printers are
viable ... test them to determine under these conditions at this height
we can get this resolution").

Each pattern is scored from the wp-2 bead result (spread, solidify time,
warp, exit viscosity) + the condition (speed, layer height, nozzle) with
a physically-motivated criterion, and returns a verdict + the governing
metric + the limiting factor + the knob to turn. Pure functions — the
manager wiring is in movement_analysis.

Patterns (the standard toolpath repertoire):
  perimeter        single thin wall — accuracy = how close the wall is to
                   one nozzle width (viscous spread widens it).
  infill-raster    parallel roads — must set between passes without the
                   turnaround blobbing.
  travel-retract   non-printing hop — low-viscosity wax OOZES/strings if
                   it has not frozen at the tip.
  sharp-corner     the head dwells while decelerating — a slow-freezing
                   melt BLOBS at the vertex.
  small-circle     minimum printable radius ≈ a few voxels.
  bridge           unsupported span — the bead must freeze before it SAGS.
  z-hop / layer    the top layer must be solid before the next lands, or
                   the nozzle smears it.

@consumers
  - waxprint.custom.movement_analysis, waxprint.custom.print_optimizer
  - waxprint.movement_selftest
"""

G = 9.81

# --- tunable thresholds (calibration knobs, flagged priors) ---
WALL_ACCURATE_RATIO = 0.25      # spread/nozzle for a "viable" thin wall
WALL_MARGINAL_RATIO = 0.60
STRING_VISCOSITY_MIN = 0.30     # Pa.s below which retraction strings
CORNER_BLOB_TSOLID_OK = 1.0     # s — freeze faster than this: no blob
CORNER_BLOB_TSOLID_MARGINAL = 3.0
MIN_RADIUS_VOXELS = 1.5         # min circle radius in voxels
BRIDGE_SAG_OK_MM = 0.10         # tolerable mid-span sag
BRIDGE_SPAN_MM = 10.0           # reference unsupported span


def _verdict3(value, ok_max, marginal_max, lower_is_better=True):
    """Three-band verdict from a value against two thresholds."""
    if lower_is_better:
        if value <= ok_max:
            return 'viable'
        if value <= marginal_max:
            return 'marginal'
        return 'fail'
    else:
        if value >= ok_max:
            return 'viable'
        if value >= marginal_max:
            return 'fail'      # not used lower-is-better=False much
        return 'fail'


def perimeter(sim, cond):
    """Thin single-wall accuracy: relative viscous over-width."""
    nozzle = cond['nozzle_d_mm']
    ratio = sim['spread_mm'] / nozzle if nozzle > 0 else float('inf')
    verdict = _verdict3(ratio, WALL_ACCURATE_RATIO, WALL_MARGINAL_RATIO)
    return {
        'pattern': 'perimeter', 'verdict': verdict,
        'governing_metric': 'spread / nozzle width', 'value': ratio,
        'threshold': WALL_ACCURATE_RATIO,
        'min_wall_mm': sim['voxel_xy_mm'],
        'limiting_factor': 'viscous spread widens the wall'
                           if verdict != 'viable' else None,
        'knob': 'faster cooling (fridge/fan), lower hotend, or a finer '
                'nozzle',
        'evidence': f"wall lands {sim['voxel_xy_mm']:.3f} mm vs a "
                    f"{nozzle:.3f} mm nozzle (spread {sim['spread_mm']:.3f} mm)"}


def infill_raster(sim, cond):
    """Parallel roads: they must set between passes, and the raster
    turnaround must not blob. Governed by solidify time vs the turnaround
    dwell."""
    speed = max(1e-6, cond['print_speed_mm_s'])
    turn_dwell = sim['voxel_xy_mm'] / speed          # ~one voxel of decel
    # a road sets fine; the risk is the turnaround where the head reverses
    verdict = 'viable' if sim['froze_in_window'] and \
        sim['t_solidify_s'] <= CORNER_BLOB_TSOLID_MARGINAL else 'marginal'
    if not sim['froze_in_window']:
        verdict = 'fail'
    return {
        'pattern': 'infill-raster', 'verdict': verdict,
        'governing_metric': 'solidify time vs turnaround dwell',
        'value': sim['t_solidify_s'], 'threshold': CORNER_BLOB_TSOLID_MARGINAL,
        'road_spacing_mm': sim['voxel_xy_mm'],
        'limiting_factor': 'roads stay molten and merge / turnaround blobs'
                           if verdict != 'viable' else None,
        'knob': 'slow the print, add cooling, or raise infill spacing',
        'evidence': f"road sets in {sim['t_solidify_s']:.2f} s; turnaround "
                    f"dwell ~{turn_dwell*1000:.0f} ms"}


def travel_retract(sim, feed):
    """Non-printing hop: a low-viscosity, still-molten tip oozes/strings."""
    eta = feed['exit_viscosity_pa_s']
    verdict = 'viable' if eta >= STRING_VISCOSITY_MIN else (
        'marginal' if eta >= 0.5 * STRING_VISCOSITY_MIN else 'fail')
    return {
        'pattern': 'travel-retract', 'verdict': verdict,
        'governing_metric': 'exit viscosity', 'value': eta,
        'threshold': STRING_VISCOSITY_MIN,
        'limiting_factor': 'thin melt oozes/strings on travel'
                           if verdict != 'viable' else None,
        'knob': 'lower the hotend (more viscous), enable retraction, or add '
                'a filler to thicken the melt',
        'evidence': f"exit viscosity {eta:.3f} Pa.s vs stringing floor "
                    f"{STRING_VISCOSITY_MIN:.2f} Pa.s"}


def sharp_corner(sim):
    """Acute vertex: the head decelerates and a slow-freezing melt blobs."""
    ts = sim['t_solidify_s']
    verdict = _verdict3(ts, CORNER_BLOB_TSOLID_OK, CORNER_BLOB_TSOLID_MARGINAL)
    return {
        'pattern': 'sharp-corner', 'verdict': verdict,
        'governing_metric': 'solidify time', 'value': ts,
        'threshold': CORNER_BLOB_TSOLID_OK,
        'limiting_factor': 'slow freeze blobs at the vertex'
                           if verdict != 'viable' else None,
        'knob': 'add cooling (fan/fridge) to freeze the corner faster',
        'evidence': f"bead freezes in {ts:.2f} s (blob-free needs "
                    f"< {CORNER_BLOB_TSOLID_OK:.1f} s)"}


def small_circle(sim):
    """Minimum printable radius ≈ a few voxels."""
    min_r = MIN_RADIUS_VOXELS * sim['voxel_xy_mm']
    return {
        'pattern': 'small-circle', 'verdict': 'viable',
        'governing_metric': 'min radius', 'value': min_r,
        'threshold': None, 'min_radius_mm': min_r,
        'limiting_factor': None,
        'knob': 'finer voxel (finer nozzle / more cooling) for tighter arcs',
        'evidence': f"smallest clean radius ~{min_r:.2f} mm "
                    f"({MIN_RADIUS_VOXELS}× the {sim['voxel_xy_mm']:.3f} mm "
                    f"voxel)"}


def bridge(sim, feed, span_mm=BRIDGE_SPAN_MM):
    """Unsupported span: the bead sags under gravity until it freezes.
    A lumped sag estimate — a beam of molten wax over `span` deflecting
    for the solidify time, resisted by viscosity."""
    eta = max(1e-4, feed['exit_viscosity_pa_s'])
    density = feed['density']
    layer_h_m = sim['voxel_z_mm'] / 1000.0
    span_m = span_mm / 1000.0
    # sag rate ~ ρ g span² / (η) · (h) ; integrated over the freeze time.
    sag_m = (density * G * span_m ** 2 / (12.0 * eta)) * layer_h_m \
        * sim['t_solidify_s']
    sag_mm = sag_m * 1000.0
    verdict = _verdict3(sag_mm, BRIDGE_SAG_OK_MM, 3.0 * BRIDGE_SAG_OK_MM)
    return {
        'pattern': 'bridge', 'verdict': verdict,
        'governing_metric': f'sag over {span_mm:.0f} mm span',
        'value': sag_mm, 'threshold': BRIDGE_SAG_OK_MM,
        'limiting_factor': 'bead sags before it freezes'
                           if verdict != 'viable' else None,
        'knob': 'freeze faster (cooling), more viscous melt, or shorter '
                'unsupported spans',
        'evidence': f"~{sag_mm:.3f} mm mid-span sag (tolerance "
                    f"{BRIDGE_SAG_OK_MM:.2f} mm)"}


def layer_z_hop(sim, cond, nominal_perimeter_mm=80.0):
    """The previous layer must be solid before the next bead lands
    (a z-hop over a still-molten top smears it)."""
    speed = max(1e-6, cond['print_speed_mm_s'])
    layer_time_s = nominal_perimeter_mm / speed
    verdict = 'viable' if sim['t_solidify_s'] <= layer_time_s else (
        'marginal' if sim['t_solidify_s'] <= 2.0 * layer_time_s else 'fail')
    return {
        'pattern': 'z-hop/layer', 'verdict': verdict,
        'governing_metric': 'solidify time vs layer time',
        'value': sim['t_solidify_s'], 'threshold': layer_time_s,
        'limiting_factor': 'top layer still molten when the next lands'
                           if verdict != 'viable' else None,
        'knob': 'slow the print, add cooling, or raise the min layer time',
        'evidence': f"freezes in {sim['t_solidify_s']:.2f} s; a layer takes "
                    f"~{layer_time_s:.2f} s at {speed:.0f} mm/s"}


def evaluate_patterns(sim, cond, feed):
    """Run every pattern. `sim` = a wp-2 voxel dict (voxel_xy_mm,
    voxel_z_mm, spread_mm, t_solidify_s, froze_in_window, warp_index);
    `cond` = {nozzle_d_mm, print_speed_mm_s, layer_height_mm}; `feed` =
    {exit_viscosity_pa_s, density}. Returns the list + an overall verdict
    (worst wins) + a count."""
    results = [
        perimeter(sim, cond),
        infill_raster(sim, cond),
        travel_retract(sim, feed),
        sharp_corner(sim),
        small_circle(sim),
        bridge(sim, feed),
        layer_z_hop(sim, cond),
    ]
    order = {'viable': 0, 'marginal': 1, 'fail': 2}
    worst = max(results, key=lambda r: order[r['verdict']])['verdict']
    n_viable = sum(1 for r in results if r['verdict'] == 'viable')
    return {
        'patterns': results,
        'overall': worst,
        'viable_count': n_viable,
        'total': len(results),
    }
