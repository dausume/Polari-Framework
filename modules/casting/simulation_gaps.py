"""
@cross-cutting
@module casting.simulation_gaps
@tags @xc:bindings

Gap audit (Dustin 2026-08-05: "account for all possible gaps in
simulation before moving forward"). Every known gap in the casting
simulation chain, as a MAINTAINED REGISTRY — data, not prose
scattered through docstrings. Three statuses:

  modelled        closed — the entry says where and with what model
  named-absence   real, unmodelled, REPORTED in results — the entry
                  says the consequence and the closure path
  planned-phase   owned by a later cast-N phase in the plan

The selftest pins registry integrity (every entry complete, every
area covered) so a new gap cannot be added half-described, and a
closed gap cannot silently keep 'named-absence' status.

@consumers casting selftest, /casting page (cast-9), reviewers
@see /WAX_MOLD_NESTING_PLAN.md
"""

GAP_STATUSES = ('modelled', 'named-absence', 'planned-phase')
GAP_AREAS = ('geometry', 'structural', 'thermal', 'process',
             'materials-data')


def _gap(gid, area, status, gap, consequence, closure):
    return {'id': gid, 'area': area, 'status': status, 'gap': gap,
            'consequence': consequence, 'closure': closure}


SIMULATION_GAPS = [
    # ---------------- geometry ----------------
    _gap('geo-shrink-scale-origin', 'geometry', 'named-absence',
         'uniform shrink scales about the ORIGIN, not the part '
         'centroid',
         'an off-center part translates as it scales',
         'derive_mold emits a finding when the part center is off '
         'origin by >10% of its extent; closure = affine '
         'scale-about-centroid (translate·scale·translate on Q)'),
    _gap('geo-anisotropic-shrink', 'geometry', 'named-absence',
         'shrink is a uniform scalar; FDM prints and drying clay '
         'shrink anisotropically (z ≠ xy)',
         'compensated parts still off in one axis',
         'per-axis measured shrink on the two-pass loop; needs a '
         'diagonal scale matrix (same algebra, 3 knobs)'),
    _gap('geo-grid-resolution', 'geometry', 'modelled',
         'occupancy grids quantize volume/connectivity',
         'few-% volume error; sub-cell channels invisible',
         'MODELLED: tolerance carried on every cross-check '
         '(0.06 field / 0.08 mesh); thin channels < 2 cells become '
         'refused-regions in cast-5'),
    _gap('geo-mesh-watertight', 'geometry', 'modelled',
         'ray-parity voxelization assumes a closed mesh',
         'a holed mesh misclassifies every column past the hole',
         'MODELLED: manifold edge check in mesh_voxelize (every '
         'edge shared by exactly 2 triangles) — non-watertight '
         'REFUSES with the boundary-edge count'),
    _gap('geo-mesh-self-intersect', 'geometry', 'named-absence',
         'self-intersecting meshes double-count parity crossings',
         'phantom voids inside overlapping shells',
         'triangle-triangle intersection sweep (expensive; run on '
         'import, cache the verdict)'),
    _gap('geo-import-units', 'geometry', 'named-absence',
         'STL/STEP carry no units — cm is ASSUMED',
         'a mm-modelled part imports 10× too large',
         'named in every mesh_grid result; closure = bbox sanity '
         'prompt on import (cad_import owns it)'),
    _gap('geo-draft-undercut', 'geometry', 'modelled',
         'undercuts vs the pull direction',
         'a derivable mold may still be un-demoldable',
         'MODELLED: cast-7 directional column sweeps (one-piece all '
         '6 directions + two-part parting-plane search); draft '
         'ANGLE margin still named — the sweep is binary'),
    # ---------------- structural ----------------
    _gap('str-wall-plate-model', 'structural', 'modelled',
         'mold walls are idealized as simply-supported rectangular '
         'plates',
         'real panels with openings/corners differ',
         'MODELLED: aspect-aware Roark factors (0.287 square → '
         '0.75 strip), peak pressure everywhere = conservative; '
         'openings interact with cast-4 sprues (still named there)'),
    _gap('str-pour-impact', 'structural', 'modelled',
         'a falling pour stream carries momentum',
         'local pressure spike the static head misses',
         'MODELLED: dynamic head ρ·g·h_drop via the '
         'pour_drop_height_cm knob (default 0 = gentle ladle, '
         'stated in the result)'),
    _gap('str-master-buoyancy', 'structural', 'modelled',
         'a wax master INVESTED in dense slurry floats '
         '(ρ_wax ≈ 997 < ρ_geopolymer ≈ 2200)',
         'the master rises mid-pour and the cavity is wrong — a '
         'silently ruined investment',
         'MODELLED: anchor force (ρ_cast − ρ_master)·V·g computed '
         'in pour_loading whenever the master would float'),
    _gap('str-sloshing', 'structural', 'named-absence',
         'sloshing/vibration during handling of a filled mold',
         'transient wall loads above the static estimate',
         'measure on the bench; static model stays the gate'),
    _gap('str-creep', 'structural', 'named-absence',
         'wax creeps under sustained load at cure temperature',
         'a mold that passes the instantaneous check can still sag '
         'over a 210-minute cure',
         'cure DURATION is now computed and the creep exposure '
         'named per report; closure = a measured creep curve per '
         'feedstock'),
    _gap('str-buckling', 'structural', 'named-absence',
         'tall slender masters can buckle (Euler), not just crush',
         'a thin pillar master fails below the crush stress',
         'needs elastic modulus per feedstock — absent for all '
         'waxes; measure E, then σ_cr = π²E(r/L)²'),
    _gap('str-print-overhangs', 'structural', 'named-absence',
         'overhang support during printing not checked here',
         'a printable-by-volume mold may need supports',
         'waxprint movement patterns own toolpath physics; bind '
         'in cast-4 when sprue geometry lands'),
    # ---------------- thermal ----------------
    _gap('thm-exotherm-section-size', 'thermal', 'named-absence',
         'the measured exotherm points are BULK-sample; thick '
         'sections peak HIGHER',
         'the 2°C carnauba margin at cure 40°C can vanish in a '
         'massive pour — the check is NOT conservative for size',
         'named in every exotherm result; closure = instrument the '
         'first large pour (thermocouple in the riser)'),
    _gap('thm-steam-firing', 'thermal', 'modelled',
         'fired geopolymer releases bound water as steam',
         'fast ramps crack the mold (and the part with it)',
         'MODELLED as an automatic finding on every firing stage '
         'with a geopolymer mold: slow ramp / pre-dry named'),
    _gap('thm-thermal-shock', 'thermal', 'modelled',
         'ramp tolerance of the target ceramic',
         'quench/ramp cracking after a technically-survivable peak',
         'MODELLED: CeramicSample.thermal_shock surfaced on every '
         'conversion stage record'),
    _gap('thm-expansion-mismatch', 'thermal', 'named-absence',
         'differential expansion/shrink-lock (clay shrinks ONTO '
         'convex mold features during firing)',
         'cracking around internal cores even when temps are fine',
         'geometric shrink-lock detection needs the cast-7 '
         'undercut sweep; CTE data per material after that'),
    _gap('thm-burnout-residue', 'thermal', 'planned-phase',
         'wax/PLA removal completeness from blind features',
         'trapped residue ruins the first firing',
         'cast-4 vents + cast-5 connectivity (a blind cavity with '
         'no rising path is exactly a flood-fill question)'),
    # ---------------- process ----------------
    _gap('prc-fill-air', 'process', 'modelled',
         'air entrapment during fill',
         'voids in the cast part',
         'MODELLED: cast-5 gravity fill (trapped pockets with vent '
         'suggestions, unfed chambers, counterflow findings); gas '
         'back-pressure magnitude still a named absence'),
    _gap('prc-demold-damage', 'process', 'modelled',
         'demolding damage',
         'a perfect cast broken on extraction',
         'MODELLED (coarse): cast-7 sweeps + brittle-vs-undercut '
         'gate + thermal gates on sacrificial routes; adhesion '
         'coefficients remain a named absence'),
    _gap('prc-mold-reuse-wear', 'process', 'planned-phase',
         'mold degradation across casting cycles',
         'cycle-life economics unbound to the chain',
         'cast-8 binds mold_analysis priors + MoldLifecycleRecord'),
    _gap('prc-warp', 'process', 'named-absence',
         'warp/distortion during cure and firing',
         'a dimensionally-correct-on-average part that is bent',
         'measure warp on the first-pass article (the two-pass '
         'loop names this); anisotropy data unlocks modelling'),
    _gap('prc-waxprint-fidelity', 'process', 'named-absence',
         'the wax master is assumed geometrically perfect',
         'print artifacts transfer to every stage downstream',
         'DELIBERATE seam (the handoff): swap in WaxPrintSimState '
         'when the chains meet the waxprint sim'),
    # ---------------- materials data ----------------
    _gap('mat-metal-thermal', 'materials-data', 'named-absence',
         'no metal solidus/liquidus/pour temperatures exist',
         'the steel chain stage REFUSES (correctly) rather than '
         'simulating',
         'cast-3b: CastingMaterialThermalProfile rows, '
         'literature-approximate with claim status'),
    _gap('mat-strength-floors', 'materials-data', 'named-absence',
         'wax/feedstock strengths are conservative literature '
         'FLOORS, not measurements',
         'over-conservative refusals possible; never unsafe passes',
         'crush a puck per feedstock; measured value replaces the '
         'prior (is_prior machinery ready)'),
    _gap('mat-slurry-density', 'materials-data', 'named-absence',
         'fresh-mix densities are conservative-HIGH priors',
         'loading over-estimated (safe direction, but imprecise)',
         'weigh a liter of the real mix; density_override knob '
         'already accepts it'),
    _gap('mat-envelope', 'materials-data', 'named-absence',
         'no printer/CNC build-envelope or cutter data',
         'a feasible mold may not fit the machine',
         'declare envelopes on assembly rows; CNC needs cutter '
         'geometry (cast-4 interaction)'),
]


def gap_register(area=None, status=None):
    """The audited gap list, filterable; counts by status so a
    report can say '7 modelled / 14 named / 5 planned' honestly."""
    rows = [g for g in SIMULATION_GAPS
            if (area is None or g['area'] == area)
            and (status is None or g['status'] == status)]
    counts = {}
    for g in SIMULATION_GAPS:
        counts[g['status']] = counts.get(g['status'], 0) + 1
    return {'ok': True, 'gaps': rows, 'total': len(SIMULATION_GAPS),
            'byStatus': counts,
            'note': 'a maintained audit — the selftest pins '
                    'integrity; closing a gap means flipping its '
                    'status WITH the model named'}
