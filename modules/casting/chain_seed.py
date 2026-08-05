"""
@cross-cutting
@module casting.chain_seed
@tags @xc:bindings

cast-3 seeds — the two chains Dustin named on 2026-08-05:

  chain-wax-geopolymer      1 inverting stage: the wax IS the mold
                            (parity: negative), geopolymer poured in,
                            wax melts out and reclaims.
  chain-wax-gp-clay-fired   the NESTED chain: geopolymer invested
                            around a wax POSITIVE (parity flips),
                            plastic clay PRESSED in (slip-casting
                            into geopolymer is refused), then FIRED
                            to earthenware at 1000°C with the
                            geopolymer mold DISPOSABLE — sacrificed
                            in the firing, loudly.

Cure temps are 40°C on wax-molded geopolymer stages ON PURPOSE: the
measured exotherm peaks 70°C at cure 40 (2°C under carnauba's 72°C
softening) but 100°C at cure 60 — a hotter cure MELTS THE MOLD, and
the chain gate proves it.

@consumers casting.casting_seed (upsert), polariServer [CastingSeed]
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-3)
"""

SEED_NESTING_CHAINS = [
    {'name': 'chain-wax-geopolymer',
     'display_name': 'Wax mold → geopolymer part',
     'target_part_shape_ref': 'unit-sphere',
     'mold_def_ref': 'demo-sphere-mold',
     'is_prior': True, 'provenance_id': 'cast-3',
     'notes': 'the simplest chain: one inversion, wax is the mold.'},
    {'name': 'chain-wax-gp-clay-fired',
     'display_name': 'Wax master → geopolymer mold → fired clay',
     'target_part_shape_ref': 'frustum-pot',
     'mold_def_ref': 'pot-frustum-mold',
     'is_prior': True, 'provenance_id': 'cast-3',
     'notes': 'two inversions + a firing conversion; the geopolymer '
              'mold is DISPOSABLE (Dustin 2026-08-05) — sacrificed '
              'at 1000°C, broken out, crushed to aggregate.'},
]

SEED_CASTING_STAGES = [
    # --- chain-wax-geopolymer ---
    {'name': 'st-wg-1-geopolymer',
     'display_name': 'Pour geopolymer into the wax mold',
     'chain_ref': 'chain-wax-geopolymer', 'sequence': 1,
     'stage_kind': 'cast', 'mold_material_ref': 'carnauba-pellet',
     'cast_material_ref': 'geopolymer-slurry',
     'fill_method': 'gravity-pour', 'cure_temp_c': 40.0,
     'removal_route': 'melt-out', 'is_prior': True,
     'provenance_id': 'cast-3',
     'notes': 'cure at 40°C ON PURPOSE — exotherm peaks 70°C, 2°C '
              'under carnauba softening; a 60°C cure peaks 100°C '
              'and melts the mold.'},
    # --- chain-wax-gp-clay-fired ---
    {'name': 'st-wgc-1-invest',
     'display_name': 'Invest geopolymer around the wax master',
     'chain_ref': 'chain-wax-gp-clay-fired', 'sequence': 1,
     'stage_kind': 'cast', 'mold_material_ref': 'carnauba-pellet',
     'cast_material_ref': 'geopolymer-slurry',
     'fill_method': 'gravity-pour', 'cure_temp_c': 40.0,
     'removal_route': 'melt-out', 'is_prior': True,
     'provenance_id': 'cast-3',
     'notes': 'the wax is a POSITIVE here (parity says so); melt it '
              'out at ~90°C after the geopolymer cures — reclaims.'},
    {'name': 'st-wgc-2-press-clay',
     'display_name': 'Press plastic clay into the geopolymer mold',
     'chain_ref': 'chain-wax-gp-clay-fired', 'sequence': 2,
     'stage_kind': 'cast', 'mold_material_ref': 'geopolymer',
     'cast_material_ref': 'plastic-clay', 'fill_method': 'press',
     'mold_disposable': True, 'removal_route': 'mechanical',
     'is_prior': True, 'provenance_id': 'cast-3',
     'notes': 'PRESSED, not slip-cast — geopolymer has no proven '
              'capillarity (mold_analysis rule; the gate refuses '
              'slip).'},
    {'name': 'st-wgc-3-fire',
     'display_name': 'Fire to earthenware (mold sacrificed)',
     'chain_ref': 'chain-wax-gp-clay-fired', 'sequence': 3,
     'stage_kind': 'conversion', 'mold_material_ref': 'geopolymer',
     'cast_material_ref': 'plastic-clay',
     'target_material_ref': 'earthenware-terracotta',
     'process_temp_c': 1000.0, 'mold_disposable': True,
     'removal_route': 'mechanical', 'is_prior': True,
     'provenance_id': 'cast-3',
     'notes': 'fired AT the geopolymer crystallization onset — the '
              'disposable mold is sacrificed (finding, not blocker); '
              'break out after firing, crush to aggregate.'},
]
