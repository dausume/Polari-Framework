"""
@cross-cutting
@module waxsupply.wax_seed
@tags @xc:bindings

wax-1 seeds — bio wax sources spanning plants, crop byproducts, insects,
and macroalgae, each linked to a real materialsScience wax material.
Emphasis on sources that grow in (or feed from) hydroponic + food-forest
systems. Idempotent-by-name. Flagged priors.

@consumers
  - polariServer seed_pairs
@see materialsScience wax rows; /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json


def _wax(name, display, stype, organism, ref, melt, hardness, feas,
         yield_g, basis, use, secondary, notes=''):
    return {'name': name, 'display_name': display, 'source_type': stype,
            'organism': organism, 'wax_material_ref': ref,
            'melt_point_c': melt, 'hardness': hardness,
            'hydroponic_feasibility': feas, 'yield_g_per_year': yield_g,
            'yield_basis': basis, 'primary_use': use,
            'secondary_uses_json': json.dumps(secondary),
            'provenance_id': 'wax-1', 'notes': notes}


SEED_WAX_SOURCES = [
    # --- hard, high-melt plant waxes: the mold + mask workhorses ---
    _wax('carnauba', 'Carnauba wax (Copernicia palm)', 'plant-leaf',
         'Copernicia prunifera palm leaves', 'carnauba-wax', 82.0, 0.95,
         'hard', 40.0, 'per-plant-per-year', 'mold',
         ['electronic-mask', 'coating'],
         'Hardest natural wax, highest melt — the premier lost-wax + '
         'mask material. Palm → needs DWARF/container culture indoors '
         '(hydroponic-hard).'),
    _wax('candelilla', 'Candelilla wax (Euphorbia shrub)', 'plant-leaf',
         'Euphorbia antisyphilitica shrub', 'candelilla-wax', 70.0, 0.8,
         'moderate', 30.0, 'per-plant-per-year', 'mold',
         ['electronic-mask', 'coating'],
         'Hard, high-melt SHRUB wax — grows far more hydroponically '
         'than carnauba; excellent mold + mask feedstock.'),
    _wax('rice-bran-wax', 'Rice bran wax (crop byproduct)',
         'crop-byproduct', 'rice bran (from rice we grow for silica)',
         'candelilla-wax', 79.0, 0.85, 'easy', 60.0, 'per-kg-feedstock',
         'mold', ['electronic-mask', 'coating'],
         'Byproduct of the SAME rice grown for bio-silica — hard, high-'
         'melt, clean burnout. A free co-product of the silica chain.'),
    _wax('sunflower-wax', 'Sunflower wax (crop byproduct)',
         'crop-byproduct', 'sunflower seed hulls/oil', 'candelilla-wax',
         74.0, 0.8, 'easy', 25.0, 'per-kg-feedstock', 'mold',
         ['coating', 'electronic-mask'],
         'Hard crystalline byproduct wax; good detail retention.'),
    # --- versatile mid waxes ---
    _wax('beeswax', 'Beeswax (pollinator)', 'insect',
         'honeybees (pollinator hive alongside the garden)', 'beeswax',
         64.0, 0.5, 'moderate', 500.0, 'per-hive-per-year',
         'electronic-mask', ['mold', 'candle', 'coating'],
         'Classic lost-wax + masking wax; a hive also POLLINATES the '
         'food forest. Softer → often blended with carnauba.'),
    _wax('jojoba', 'Jojoba (liquid wax ester)', 'plant-seed',
         'Simmondsia chinensis shrub seeds', 'coconut-wax', 10.0, 0.1,
         'moderate', 200.0, 'per-plant-per-year', 'lubricant',
         ['coating'],
         'Liquid wax ESTER (not a hard wax) — a mold-release + coating/'
         'lubricant, not a mold body. Drought-tolerant shrub.'),
    _wax('bayberry', 'Bayberry wax (Myrica berries)', 'plant-berry',
         'Myrica cerifera berries', 'soy-wax', 47.0, 0.4, 'moderate',
         15.0, 'per-plant-per-year', 'candle', ['coating'],
         'Aromatic berry wax; softer, lower melt — candle/coating.'),
    _wax('soy-wax', 'Soy wax (crop byproduct)', 'crop-byproduct',
         'soybean oil (hydrogenated)', 'soy-wax', 50.0, 0.3, 'easy',
         40.0, 'per-kg-feedstock', 'candle', ['coating'],
         'Soft, low-melt — candle/coating, not molds.'),
    # --- macroalgae wax ADDITIVE (ties the saltwater food forest in) ---
    _wax('macroalgae-wax-additive', 'Macroalgae wax additive',
         'macroalgae', 'sea lettuce / red ogo / dulse polysaccharides',
         'candelilla-wax', 65.0, 0.6, 'easy', 20.0, 'per-kg-feedstock',
         'wax-additive', ['mold'],
         'Polysaccharide/lipid ADDITIVE from the saltwater food forest '
         'macroalgae (per the spec) — hardens/modifies blended waxes '
         'rather than standing alone.'),
]
