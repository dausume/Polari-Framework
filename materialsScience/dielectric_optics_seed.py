"""
@cross-cutting
@module materialsScience.dielectric_optics_seed
@tags @xc:bindings

Fully-bio-derivable OPTICAL DIELECTRIC materials + their property
meanings (dielectric-optics-1). These are the materials the biomining
optical-dielectric variants refine toward — every one buildable in any
community from common, fully bio-derivable elements (Si, P, K, Na, N,
Ca, S, Zn, Mg, Cl + organic C/H/O), for precision laser control
(electro-optic beam modulation + piezo nanopositioning) on a melt-voxel
system.

Two seed lists (mirroring aquaponics/pot_materials_seed):
  SEED_DIELECTRIC_MATERIALS          MaterialsScienceMaterial rows.
  SEED_DIELECTRIC_PROPERTY_MEANINGS  the dielectric/optical vocabulary
                                     (relativePermittivity, electroOptic
                                     Coefficient, refractiveIndex,
                                     opticalLoss, piezoelectricCoefficient).

Representative property VALUES are noted in each material's `notes`
(literature priors); per-scale MaterialScaleDefinition rows carrying the
numbers as computable properties are a later increment.

@consumers
  - polariServer seed_pairs (MaterialsScienceMaterial + PropertyMeaning)
  - biomining optical products' material_ref links resolve to these
@see /biomining/optical_seed.py
"""

import json

_PROV = 'dielectric-optics-1'


def _mat(name, display, elements, tags, notes):
    return {'name': name, 'display_name': display,
            'material_kind': 'pure' if len(elements) <= 2 else 'composite',
            'category': 'structural',
            'element_symbols_json': json.dumps(elements),
            'tags_json': json.dumps(
                ['optical', 'dielectric', 'fully-bio'] + tags),
            'provenance_id': _PROV, 'notes': notes}


SEED_DIELECTRIC_MATERIALS = [
    # --- active electro-optic / piezo crystals (solution-grown) ---
    _mat('kdp-electro-optic', 'KDP (potassium dihydrogen phosphate)',
         ['K', 'H', 'P', 'O'], ['electro-optic', 'nonlinear', 'piezo',
                                'solution-grown'],
         'KH2PO4. Electro-optic (Pockels) + nonlinear + piezo; grown '
         'from aqueous solution at low temperature — ideal for a '
         'bio-concentrated K + phosphate feedstock. Priors: r41~8-10 '
         'pm/V, n~1.51, eps_r~21 (static), grows from water. Soft + '
         'hygroscopic → sealed, temperature-stabilized cell.'),
    _mat('adp-electro-optic', 'ADP (ammonium dihydrogen phosphate)',
         ['N', 'H', 'P', 'O'], ['electro-optic', 'piezo',
                                'solution-grown'],
         'NH4H2PO4. Piezo + electro-optic + nonlinear; both elements '
         '(ammonium + phosphate) come straight from aquaculture waste. '
         'Prior: r63~24 pm/V, n~1.52, solution-grown.'),
    _mat('rochelle-salt', 'Rochelle salt (K-Na tartrate)',
         ['K', 'Na', 'C', 'H', 'O'], ['ferroelectric', 'piezo',
                                      'electro-optic', 'solution-grown'],
         'KNaC4H4O6·4H2O — the ORIGINAL piezo/ferroelectric/EO crystal, '
         'from wine tartar + potash + salt. Fully bio-common + '
         'solution-grown. Ferroelectric only ~-18..+24 C → run cooled + '
         'sealed. Large piezo + EO response.'),
    _mat('tgs-ferroelectric', 'TGS (triglycine sulfate)',
         ['C', 'H', 'N', 'O', 'S'], ['ferroelectric', 'pyroelectric',
                                     'solution-grown'],
         '(NH2CH2COOH)3·H2SO4 — fully bio-elemental ferroelectric from '
         'glycine (fermentation) + sulfate. Curie ~49 C; strong '
         'pyro/ferroelectric response, solution-grown.'),
    # --- passive glass + coating dielectrics ---
    _mat('bio-fused-silica', 'Bio fused silica (SiO2)',
         ['Si', 'O'], ['low-index', 'substrate', 'fiber', 'coating',
                       'high-damage-threshold'],
         'SiO2 from diatom frustules / rice-husk ash / sponge silica '
         '(rice-husk silica purified to semiconductor grade in the '
         'literature). The universal low-loss substrate/fiber/window + '
         'low-index coating layer. Prior: n~1.46, eps_r~3.8, very high '
         'laser-damage threshold.'),
    _mat('bio-zinc-oxide', 'Bio zinc oxide (ZnO)',
         ['Zn', 'O'], ['high-index', 'coating', 'piezo',
                       'semiconductor'],
         'ZnO from bacterial/fungal/plant bio-synthesis (extensively '
         'published). The HIGH-index partner (n~2.0) to bio-silica '
         '(n~1.46) for dielectric mirror stacks; also piezoelectric.'),
    _mat('bio-magnesia', 'Bio magnesia (MgO)',
         ['Mg', 'O'], ['mid-index', 'coating'],
         'MgO from bio-magnesium (seawater/biomass). Mid-index '
         '(n~1.74) coating dielectric; wide transparency.'),
    # --- polarization + IR optics ---
    _mat('bio-calcite-optical', 'Bio calcite (CaCO3, birefringent)',
         ['Ca', 'C', 'O'], ['birefringent', 'polarizer', 'biomineral'],
         'CaCO3 biomineralized by mollusks/corals/coccolithophores. '
         'Strongly birefringent (polarizers, waveplates). CAVEAT: '
         'bio-carbonate is polycrystalline — optical single-crystal '
         'grade is the hard step; abundant as birefringent feedstock.'),
    _mat('bio-rock-salt', 'Bio rock salt (NaCl, IR window)',
         ['Na', 'Cl'], ['ir-window', 'solution-grown'],
         'NaCl from seawater/halophyte ash, solution-grown. Broadband '
         'IR transparency (relevant to CO2/IR melt lasers ~10.6 um); '
         'soft + hygroscopic → sealed housing.'),
]

SEED_DIELECTRIC_PROPERTY_MEANINGS = [
    {'name': 'relativePermittivity',
     'display_name': 'Relative permittivity (dielectric constant)',
     'units': 'dimensionless',
     'meaning': 'How strongly the material polarizes in an electric '
                'field, ε_r = ε/ε0 — the core dielectric property. Sets '
                'the capacitance + the field a Pockels/piezo cell sees.',
     'scenario_context': 'For precision laser control, a STABLE ε_r '
                         '(low drift with temperature + frequency) '
                         'matters more than a high one — drift is what '
                         'de-calibrates a melt-voxel adjustment.',
     'aliases_json': json.dumps(
         ['dielectricConstant', 'epsilonR', 'eps_r',
          'relative_permittivity', 'permittivity']),
     'scale_levels_json': json.dumps([0, 1])},
    {'name': 'electroOpticCoefficient',
     'display_name': 'Electro-optic (Pockels) coefficient',
     'units': 'pm/V',
     'meaning': 'How much the refractive index shifts per unit applied '
                'electric field (linear Pockels r_ij) — the lever for '
                'voltage-controlled phase/amplitude/beam modulation.',
     'scenario_context': 'Higher r → lower drive voltage for a given '
                         'phase shift → finer, faster per-voxel dosing. '
                         'KDP ~8-10, ADP ~24 pm/V.',
     'aliases_json': json.dumps(
         ['pockelsCoefficient', 'r41', 'r63', 'eoCoefficient',
          'electro_optic_coefficient']),
     'scale_levels_json': json.dumps([0, 1])},
    {'name': 'refractiveIndex',
     'display_name': 'Refractive index',
     'units': 'dimensionless',
     'meaning': 'The optical index n = c/v — sets refraction, Fresnel '
                'reflection, and (as a high/low contrast pair) dielectric '
                'mirror design.',
     'scenario_context': 'Coating stacks need a HIGH-index (bio-ZnO '
                         '~2.0) and a LOW-index (bio-silica ~1.46) '
                         'dielectric alternating; the contrast sets how '
                         'few layers reach a target reflectivity.',
     'aliases_json': json.dumps(
         ['refractive_index', 'n', 'opticalIndex']),
     'scale_levels_json': json.dumps([0, 1])},
    {'name': 'opticalLoss',
     'display_name': 'Optical loss / absorption',
     'units': 'dB/cm',
     'meaning': 'How much light the dielectric absorbs/scatters per unit '
                'length — the purity-limited property. Low loss = high '
                'laser-damage threshold + stable behavior.',
     'scenario_context': 'This is where BIO-REFINEMENT wins: selective '
                         'bioaccumulation + low-temperature '
                         'biomineralization yield the ultra-purity + '
                         'homogeneity that keep loss (and damage) low.',
     'aliases_json': json.dumps(
         ['absorptionCoefficient', 'opticalAbsorption', 'loss',
          'optical_loss']),
     'scale_levels_json': json.dumps([0, 1])},
    {'name': 'piezoelectricCoefficient',
     'display_name': 'Piezoelectric coefficient',
     'units': 'pC/N',
     'meaning': 'Charge produced per unit mechanical stress (d_ij) — and '
                'inversely, the strain per applied field. Enables '
                'nanometer mechanical POSITIONING of optics.',
     'scenario_context': 'The same bio crystals (KDP, Rochelle salt, '
                         'ZnO) that modulate the beam also actuate '
                         'mirror/lens position — one bio chemistry '
                         'covers both senses of precision adjustment.',
     'aliases_json': json.dumps(
         ['d33', 'd_ij', 'piezoCoefficient',
          'piezoelectric_coefficient']),
     'scale_levels_json': json.dumps([0, 1])},
]
