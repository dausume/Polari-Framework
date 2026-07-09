"""
@cross-cutting
@module biomining.optical_seed
@tags @xc:bindings

biomine-1 optical-dielectric variants (dielectric-optics-1) — the
fully-bio-derivable dielectric-crystal + glass extraction chains for
precision laser control. Every agent concentrates a common, fully
bio-derivable element/ligand; every product refines toward a real
MaterialsScienceMaterial in dielectric_optics_seed. Idempotent-by-name.
Flagged priors.

Design filter (Dustin): must be FULLY bio-derivable from common
materials, buildable in any community globally.

@consumers
  - polariServer seed_pairs (appended to the biomining agent/product/
    system lists)
@see materialsScience/dielectric_optics_seed.py
"""

import json


def _agent(name, display, atype, mechanism, element, selectivity,
           rate, byproduct):
    return {'name': name, 'display_name': display, 'agent_type': atype,
            'mechanism': mechanism, 'target_element': element,
            'selectivity': selectivity,
            'uptake_rate_mg_per_g_per_day': rate, 'water_type': 'both',
            'byproduct': byproduct, 'provenance_id': 'dielectric-optics-1'}


SEED_OPTICAL_AGENTS = [
    # Potassium — potash from algae/plant ash (universally common).
    _agent('potassium-accumulating-alga', 'Potassium-accumulating alga',
           'algae', 'bioaccumulation', 'K', 0.8, 50.0,
           'K-rich biomass (potash on ashing)'),
    # Silica — diatoms biomineralize amorphous SiO2 with nm precision.
    _agent('silica-biomineralizing-diatom',
           'Silica-biomineralizing diatom', 'algae',
           'biomineralization', 'Si', 0.95, 70.0,
           'amorphous silica frustules'),
    # Zinc — bacterial/fungal ZnO bio-synthesis (well published).
    _agent('zinc-accumulating-microbe', 'Zinc-accumulating microbe',
           'bacteria', 'bioprecipitation', 'Zn', 0.8, 20.0,
           'ZnO nanoparticles'),
    # Magnesium — from seawater/biomass.
    _agent('magnesium-accumulating-microbe',
           'Magnesium-accumulating microbe', 'bacteria',
           'bioaccumulation', 'Mg', 0.75, 30.0, 'Mg-rich biomass'),
    # Calcium carbonate — calcifying microalgae (coccolithophores).
    _agent('calcifying-microalga', 'Calcifying microalga '
           '(coccolithophore)', 'algae', 'biomineralization', 'Ca',
           0.9, 60.0, 'CaCO3 coccoliths'),
    # Sodium/chloride — halophytes / seawater concentration.
    _agent('halophyte-salt-accumulator', 'Halophyte salt accumulator',
           'algae', 'bioaccumulation', 'Na', 0.7, 80.0,
           'NaCl on evaporation'),
    # Tartrate — fermentation byproduct (wine tartar); organic ligand.
    _agent('tartrate-fermenting-yeast', 'Tartrate-fermenting yeast',
           'fungi', 'biosynthesis', 'C', 0.85, 40.0,
           'potassium bitartrate (cream of tartar)'),
    # Glycine — fermentation; the ligand for TGS.
    _agent('glycine-fermenting-microbe', 'Glycine-fermenting microbe',
           'bacteria', 'biosynthesis', 'C', 0.8, 45.0,
           'glycine (amino acid)'),
]


def _product(name, display, kind, element, refined, material_ref,
             steps, yield_factor, notes=''):
    return {'name': name, 'display_name': display, 'product_kind': kind,
            'source_element': element, 'refined_form': refined,
            'material_ref': material_ref,
            'refinement_pathway_json': json.dumps(steps),
            'element_to_product_yield': yield_factor,
            'purity_target': 0.99, 'provenance_id': 'dielectric-optics-1',
            'notes': notes}


_SOLN = 'recrystallize from aqueous solution (slow evaporation) to '\
        'optical grade'

SEED_OPTICAL_PRODUCTS = [
    _product('kdp-crystal', 'KDP electro-optic crystal',
             'electro-optic-crystal', 'P', 'KH2PO4 single crystal',
             'kdp-electro-optic',
             ['bio-concentrate K (potash) + phosphate', 'neutralize to '
              'KH2PO4 solution', _SOLN, 'cut + polish + electrode'],
             4.39, 'yield ~ KDP MW 136 / P 31'),
    _product('adp-crystal', 'ADP electro-optic crystal',
             'electro-optic-crystal', 'P', 'NH4H2PO4 single crystal',
             'adp-electro-optic',
             ['recover phosphate + ammonium (aquaculture waste)',
              'form NH4H2PO4 solution', _SOLN, 'cut + polish + electrode'],
             3.71, 'yield ~ ADP MW 115 / P 31'),
    _product('rochelle-salt-crystal', 'Rochelle salt piezo/EO crystal',
             'electro-optic-crystal', 'K',
             'KNaC4H4O6·4H2O single crystal', 'rochelle-salt',
             ['ferment tartrate (wine tartar) + potash + salt',
              'form K-Na tartrate solution', _SOLN,
              'cut + polish (sealed, cooled)'],
             7.2, 'yield ~ Rochelle MW 282 / K 39'),
    _product('tgs-crystal', 'TGS ferroelectric crystal',
             'electro-optic-crystal', 'S',
             'triglycine sulfate single crystal', 'tgs-ferroelectric',
             ['ferment glycine + recover sulfate', 'form TGS solution',
              _SOLN, 'pole below Curie point'],
             10.1, 'yield ~ TGS MW 323 / S 32'),
    _product('fused-silica-optic', 'Fused silica (bio) optic',
             'optical-glass', 'Si', 'purified fused silica',
             'bio-fused-silica',
             ['harvest diatom frustules / rice-husk silica',
              'acid-leach + calcine to high-purity SiO2',
              'melt/consolidate to fused silica', 'draw fiber / polish '
              'substrate'],
             2.14, 'yield ~ SiO2 MW 60 / Si 28'),
    _product('zinc-oxide-coating', 'Zinc oxide high-index coating',
             'coating-dielectric', 'Zn', 'ZnO thin film',
             'bio-zinc-oxide',
             ['bio-precipitate ZnO nanoparticles', 'purify + calcine',
              'sputter/deposit as the high-index coating layer'],
             1.25, 'yield ~ ZnO MW 81 / Zn 65'),
    _product('magnesia-coating', 'Magnesia mid-index coating',
             'coating-dielectric', 'Mg', 'MgO thin film',
             'bio-magnesia',
             ['recover Mg', 'precipitate + calcine to MgO', 'deposit '
              'coating layer'],
             1.66, 'yield ~ MgO MW 40 / Mg 24'),
    _product('calcite-polarizer', 'Calcite birefringent optic',
             'birefringent-crystal', 'Ca', 'CaCO3 (calcite)',
             'bio-calcite-optical',
             ['harvest biomineral CaCO3 (shell/coccolith)',
              'select clear domains / recrystallize',
              'cut along optic axis + polish'],
             2.5, 'yield ~ CaCO3 MW 100 / Ca 40'),
    _product('rock-salt-ir-window', 'Rock salt IR window',
             'ir-window', 'Na', 'NaCl single crystal',
             'bio-rock-salt',
             ['concentrate NaCl (halophyte/seawater)', _SOLN,
              'cleave + polish (sealed housing)'],
             2.54, 'yield ~ NaCl MW 58.5 / Na 23'),
]


def _system(name, display, product, agents, element_supply, desc):
    return {'name': name, 'display_name': display,
            'variant': 'optical-dielectric', 'water_type': 'both',
            'agent_stock_json': json.dumps(agents),
            'product_name': product,
            'source_system_name': 'community-mineral-feedstock',
            'source_kind': 'feedstock',
            'source_element_supply_mg_per_day': element_supply,
            'extraction_cap_mg_per_day': 0.0,
            'description': desc, 'provenance_id': 'dielectric-optics-1'}


SEED_OPTICAL_BIOMINE_SYSTEMS = [
    _system('kdp-electro-optic-biomine', 'KDP electro-optic biomine',
            'kdp-crystal',
            {'potassium-accumulating-alga': 20.0,
             'phosphate-accumulating-bacteria': 25.0}, 1200.0,
            'K + phosphate → KDP crystals for Pockels-cell beam '
            'modulation (the headline precision element).'),
    _system('adp-electro-optic-biomine', 'ADP electro-optic biomine',
            'adp-crystal',
            {'phosphate-accumulating-bacteria': 25.0}, 900.0,
            'Phosphate + ammonium (aquaculture waste) → ADP crystals.'),
    _system('rochelle-salt-biomine', 'Rochelle salt piezo/EO biomine',
            'rochelle-salt-crystal',
            {'tartrate-fermenting-yeast': 30.0,
             'potassium-accumulating-alga': 15.0}, 800.0,
            'Wine tartar + potash + salt → Rochelle salt (piezo '
            'nanopositioning + EO), fully community-makeable.'),
    _system('tgs-ferroelectric-biomine', 'TGS ferroelectric biomine',
            'tgs-crystal',
            {'glycine-fermenting-microbe': 30.0}, 600.0,
            'Glycine + sulfate → TGS ferroelectric.'),
    _system('fused-silica-biomine', 'Bio fused-silica biomine',
            'fused-silica-optic',
            {'silica-biomineralizing-diatom': 40.0}, 4000.0,
            'Diatom / rice-husk silica → fused silica substrates, '
            'fiber, windows, and the low-index coating layer.'),
    _system('zinc-oxide-coating-biomine', 'Bio ZnO coating biomine',
            'zinc-oxide-coating',
            {'zinc-accumulating-microbe': 25.0}, 500.0,
            'Bio-ZnO → the high-index partner to bio-silica for '
            'dielectric mirror stacks.'),
    _system('magnesia-coating-biomine', 'Bio magnesia coating biomine',
            'magnesia-coating',
            {'magnesium-accumulating-microbe': 25.0}, 700.0,
            'Bio-MgO → mid-index coating dielectric.'),
    _system('calcite-polarizer-biomine', 'Bio calcite polarizer biomine',
            'calcite-polarizer',
            {'calcifying-microalga': 30.0}, 1500.0,
            'Biomineral CaCO3 → birefringent polarization optics.'),
    _system('rock-salt-window-biomine', 'Bio rock-salt IR window biomine',
            'rock-salt-ir-window',
            {'halophyte-salt-accumulator': 30.0}, 2000.0,
            'Halophyte/seawater NaCl → IR windows for CO2/IR melt '
            'lasers.'),
]
