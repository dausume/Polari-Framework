#!/usr/bin/env python3
"""
@module mech.custom.registry.build_registry

Polari critical-materials registry + per-part-family material roles — the
mech module's copy of /home/dausume/collab/mech-parts/data/build_materials.py
(econ-core, 2026-11-03), adapted: writes JSON next to itself, no CSV, and
adds the two WOOD rows the drawer plan needs (birch plywood, MDF — marked
`source='mech-mxc-1'`; everything else is the collab registry verbatim,
`source='collab-mech-parts'`). Run it to regenerate:

    cd polari-framework && PYTHONPATH=.:modules python3 \
        modules/mech/custom/registry/build_registry.py

Writes (next to this file):
  materials_registry.json   - one row per material: feedstocks with IARC class, status, end of life
  part_material_roles.json  - per part family: Polari default, acceptable alternatives, legacy/harmful
  REGISTRY.json             - provenance of the whole set (what, who, when, what is NOT yet checked)

Status vocabulary (the plan's section 3.3 and the collab data agree on it):
  polari_preferred   - default choice: no carcinogenic (IARC 1/2A/2B) monomer or process chemical is
                       isolated and handled in bulk to make it, and it has a workable end of life
  polari_acceptable  - usable; carries a named caveat (sensitiser, chlorine at end of life, process control)
  legacy_harmful     - common in existing kits/parts; kept ONLY for comparison and for modelling parts
                       people already own. Not to be specified for new Polari designs.

IARC groups: 1 carcinogenic, 2A probably, 2B possibly, 3 not classifiable, none = not evaluated.
The IARC rows are from knowledge, NOT yet checked against the monographs row by row (plan section 7);
rows with confidence='check' (AEM's methyl acrylate) need that first.
Compiled 2026-11-03 by econ-core (Claude) for Dustin Etts.
"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))

def F(name, iarc, note=''):
    return {'name': name, 'iarc': iarc, 'note': note}

MATERIALS = [
 # ---------------- elastomers ----------------
 dict(id='tpu_mdi', name='Thermoplastic polyurethane (MDI-based)', cls='elastomer', status='polari_preferred',
      feedstocks=[F('MDI (methylene diphenyl diisocyanate)', '3', 'respiratory sensitiser in manufacture'),
                  F('polyester or polyether polyol', 'none', 'bio-based polyols available (castor oil, bio-succinic acid)'),
                  F('1,4-butanediol', 'none')],
      end_of_life='thermoplastic: can be remelted / regranulated', bio_option=True,
      caveats=['isocyanate sensitisation during manufacture (not at use)', 'polyester grades hydrolyse in hot water'],
      confidence='good'),
 dict(id='tpc_et', name='Copolyester elastomer (TPC-ET)', cls='elastomer', status='polari_preferred',
      feedstocks=[F('terephthalic acid', 'none'), F('1,4-butanediol', 'none'), F('polyether glycol (PTMEG)', 'none')],
      end_of_life='thermoplastic: remeltable', bio_option=True, caveats=['cost'], confidence='good'),
 dict(id='epdm_peroxide', name='EPDM, peroxide-cured', cls='elastomer', status='polari_preferred',
      feedstocks=[F('ethylene', '3'), F('propylene', '3'), F('5-ethylidene-2-norbornene (ENB)', 'none', 'a few %')],
      end_of_life='thermoset: grind to crumb / energy recovery', bio_option=True,
      caveats=['poor oil/fuel resistance', 'sulfur-cured grades: use nitrosamine-safe accelerators only'],
      confidence='good'),
 dict(id='cm', name='Chlorinated polyethylene (CM)', cls='elastomer', status='polari_acceptable',
      feedstocks=[F('polyethylene (from ethylene)', '3'), F('chlorine (post-polymerisation)', 'none', 'toxic gas, not a carcinogen')],
      end_of_life='contains chlorine: HCl on combustion, needs scrubbed incineration', bio_option=False,
      caveats=['chlorinated at end of life'], note='closest property match to neoprene with no chlorinated monomer',
      confidence='good'),
 dict(id='natural_rubber', name='Natural rubber (FSC hevea) / guayule', cls='elastomer', status='polari_preferred',
      feedstocks=[F('plant-biosynthesised polyisoprene', 'none', 'no free isoprene is isolated')],
      end_of_life='thermoset: crumb; biodegrades slowly', bio_option=True,
      caveats=['poor ozone + oil resistance', 'latex protein allergy (guayule avoids it)',
               'avoid 6PPD antiozonant (6PPD-quinone is lethal to coho salmon)'],
      confidence='good'),
 dict(id='silicone_vmq', name='Silicone rubber (VMQ)', cls='elastomer', status='polari_acceptable',
      feedstocks=[F('silicon metal', 'none'), F('methyl chloride', '3'), F('D4/D5 cyclic siloxanes (intermediates)', 'none', 'EU-restricted as PBT/vPvB in wash-off products')],
      end_of_life='thermoset: limited recycling (depolymerisation emerging)', bio_option=False,
      caveats=['poor tear/abrasion', 'cyclic siloxane persistence'], confidence='good'),
 dict(id='aem', name='Ethylene-acrylic elastomer (AEM)', cls='elastomer', status='polari_acceptable',
      feedstocks=[F('ethylene', '3'), F('methyl acrylate', 'check', 'confirm current IARC class')],
      end_of_life='thermoset', bio_option=False, caveats=['confirm methyl acrylate classification'], confidence='check'),
 dict(id='neoprene_cr', name='Polychloroprene (neoprene, CR)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('chloroprene', '2B', 'US EPA IRIS: likely human carcinogen'),
                  F('1,3-butadiene (petroleum route)', '1'), F('acetylene via calcium carbide ("limestone" route)', 'none')],
      end_of_life='thermoset, ~40% chlorine: HCl / dioxin risk on burning; landfill', bio_option=False,
      caveats=['ETU (ethylene thiourea) accelerator is a reproductive toxicant'],
      replaced_by=['tpu_mdi', 'tpc_et', 'cm', 'epdm_peroxide'], confidence='good'),
 dict(id='sbr', name='Styrene-butadiene rubber (SBR)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('1,3-butadiene', '1'), F('styrene', '2A')], end_of_life='thermoset: crumb',
      replaced_by=['natural_rubber', 'epdm_peroxide'], confidence='good'),
 dict(id='nbr_hnbr', name='Nitrile rubber (NBR / HNBR)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('1,3-butadiene', '1'), F('acrylonitrile', '1', 'IARC upgraded to Group 1 in 2024')],
      end_of_life='thermoset', replaced_by=['aem', 'tpu_mdi'], confidence='good'),
 dict(id='acm', name='Polyacrylate rubber (ACM)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('ethyl acrylate', '2B')], replaced_by=['aem'], confidence='good'),
 dict(id='sebs_sbs', name='Styrenic block copolymers (SBS / SEBS)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('styrene', '2A'), F('1,3-butadiene', '1')], replaced_by=['tpc_et', 'tpu_mdi'], confidence='good'),
 dict(id='tpu_tdi', name='Polyurethane (TDI-based)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('TDI (toluene diisocyanate)', '2B')], replaced_by=['tpu_mdi'], confidence='good'),
 dict(id='fkm', name='Fluoroelastomer (FKM)', cls='elastomer', status='legacy_harmful',
      feedstocks=[F('vinylidene fluoride / HFP / TFE', 'none', 'PFAS chemistry; fluorosurfactant processing aids historically PFOA (IARC 1)')],
      end_of_life='persistent', replaced_by=['aem', 'silicone_vmq'], note='keep only where nothing else survives the chemical', confidence='good'),

 # ---------------- rigid plastics (printed + moulded parts) ----------------
 dict(id='pla', name='PLA', cls='plastic', status='polari_preferred',
      feedstocks=[F('lactic acid / lactide (fermented sugar)', 'none')],
      end_of_life='industrial compost / remelt', bio_option=True, caveats=['softens ~55-60 C', 'creep under load'], confidence='good'),
 dict(id='petg', name='PETG', cls='plastic', status='polari_preferred',
      feedstocks=[F('terephthalic acid', 'none'), F('ethylene glycol', 'none'), F('CHDM', 'none')],
      end_of_life='remeltable', bio_option=True, confidence='good'),
 dict(id='pp', name='Polypropylene', cls='plastic', status='polari_preferred',
      feedstocks=[F('propylene', '3')], end_of_life='remeltable (recycling code 5)', bio_option=True, confidence='good'),
 dict(id='uhmwpe', name='UHMW polyethylene', cls='plastic', status='polari_preferred',
      feedstocks=[F('ethylene', '3')], end_of_life='remeltable with difficulty / reuse', bio_option=True,
      note='low-friction sliders, wheels, wear strips', confidence='good'),
 dict(id='pa66', name='Nylon PA66', cls='plastic', status='polari_preferred',
      feedstocks=[F('adipic acid', 'none', 'production emits N2O unless abated'), F('hexamethylenediamine', 'none')],
      end_of_life='remeltable', bio_option=True, caveats=['absorbs moisture; dimensions shift'], confidence='good'),
 dict(id='pa6', name='Nylon PA6', cls='plastic', status='polari_preferred',
      feedstocks=[F('caprolactam', '3', 'was the only Group 4 agent until 2019')], end_of_life='remeltable; chemically recyclable to caprolactam',
      bio_option=False, confidence='good'),
 dict(id='pa11', name='Nylon PA11', cls='plastic', status='polari_preferred',
      feedstocks=[F('11-aminoundecanoic acid (castor oil)', 'none')], end_of_life='remeltable', bio_option=True, confidence='good'),
 dict(id='peek', name='PEEK', cls='plastic', status='polari_acceptable',
      feedstocks=[F('hydroquinone', '3'), F('4,4\'-difluorobenzophenone', 'none')], end_of_life='remeltable',
      caveats=['cost; high-temperature processing'], confidence='good'),
 dict(id='pom', name='Acetal (POM, "Delrin")', cls='plastic', status='legacy_harmful',
      feedstocks=[F('formaldehyde / trioxane', '1')], end_of_life='remeltable; releases formaldehyde when overheated',
      replaced_by=['uhmwpe', 'pa66', 'pa11'], note='V-wheels, lead-screw nuts, gears, bushings', confidence='good'),
 dict(id='abs', name='ABS', cls='plastic', status='legacy_harmful',
      feedstocks=[F('acrylonitrile', '1'), F('1,3-butadiene', '1'), F('styrene', '2A')],
      end_of_life='remeltable', caveats=['styrene emissions when printing'], replaced_by=['petg', 'pp', 'pa66'], confidence='good'),
 dict(id='pc_bpa', name='Polycarbonate (BPA)', cls='plastic', status='legacy_harmful',
      feedstocks=[F('bisphenol A', 'none', 'endocrine disruptor; EU SVHC'), F('phosgene', 'none', 'acutely toxic gas (non-phosgene melt route exists)')],
      replaced_by=['petg', 'pa66'], note='"Xtreme" V-wheels, guards', confidence='good'),
 dict(id='pvc', name='PVC', cls='plastic', status='legacy_harmful',
      feedstocks=[F('vinyl chloride', '1')], end_of_life='HCl/dioxin on burning; phthalate plasticisers in flexible grades',
      replaced_by=['pp', 'tpu_mdi'], note='cable insulation, tubing', confidence='good'),
 dict(id='ptfe', name='PTFE', cls='plastic', status='legacy_harmful',
      feedstocks=[F('tetrafluoroethylene', '2A'), F('PFOA processing aid (historical)', '1')],
      end_of_life='persistent (PFAS)', replaced_by=['uhmwpe', 'peek'], note='bowden tubes, low-friction pads', confidence='good'),

 # ---------------- wood (mech addition: the drawer plan's plywood bottom and wooden-runner legacy variant) ----------------
 dict(id='birch_plywood', name='Birch plywood (B/BB, exterior PF glue)', cls='wood', status='polari_acceptable',
      feedstocks=[F('birch veneer', 'none', 'wood DUST is IARC 1 as inhaled dust when machined: an occupational control, not in the part'),
                  F('phenol-formaldehyde adhesive (exterior) / urea-formaldehyde (interior)', '1', 'formaldehyde is IARC 1 in manufacture; cured panel emission limited by E1 / CARB2; NAF (soy, PVAc) glues exist')],
      end_of_life='reuse / energy recovery; PF glue is not compostable', bio_option=True,
      caveats=['specify E1/CARB2 or NAF glue', 'moisture movement across the grain', 'machining dust needs extraction'],
      note='drawer bottoms, cassette frames, the legacy wooden runner', confidence='check', source='mech-mxc-1'),
 dict(id='mdf', name='MDF (medium-density fibreboard)', cls='wood', status='polari_acceptable',
      feedstocks=[F('wood fibre', 'none', 'wood dust IARC 1 when machined (occupational)'),
                  F('urea-formaldehyde binder (~10 % by mass)', '1', 'formaldehyde IARC 1 in manufacture and as panel emission; NAF-MDF (pMDI binder) exists')],
      end_of_life='landfill / energy recovery; not recyclable as fibre', bio_option=True,
      caveats=['high formaldehyde emission unless NAF grade', 'swells when wet', 'low screw-holding on edges'],
      note='flat panels, jigs; weaker than plywood for a loaded bottom', confidence='check', source='mech-mxc-1'),

 # ---------------- metals ----------------
 dict(id='al_6063', name='Aluminium 6063-T5/T6 (extrusion)', cls='metal', status='polari_preferred',
      feedstocks=[F('bauxite -> alumina -> Hall-Heroult smelting', 'none', 'energy-heavy; recycled Al ~5% of the energy')],
      end_of_life='infinitely recyclable', caveats=['prefer high recycled content'], confidence='good'),
 dict(id='al_6061', name='Aluminium 6061-T6 (plate, pulleys, couplings)', cls='metal', status='polari_preferred',
      feedstocks=[F('aluminium + Mg, Si', 'none')], end_of_life='recyclable', confidence='good'),
 dict(id='al_diecast', name='Die-cast aluminium (ADC12 / A380)', cls='metal', status='polari_preferred',
      feedstocks=[F('secondary (recycled) aluminium', 'none')], end_of_life='recyclable', confidence='good'),
 dict(id='steel_carbon', name='Carbon / alloy steel (classes 4.8-12.9, C45, 52100)', cls='metal', status='polari_preferred',
      feedstocks=[F('iron ore / scrap', 'none')], end_of_life='recyclable (EAF scrap route)', caveats=['needs a corrosion finish'], confidence='good'),
 dict(id='stainless_a2_a4', name='Stainless steel A2 (304) / A4 (316)', cls='metal', status='polari_preferred',
      feedstocks=[F('iron, chromium (metallic Cr(III) chemistry), nickel', 'none', 'metallic nickel 2B as dust; no hazard in the part')],
      end_of_life='recyclable', confidence='good'),
 dict(id='brass_lead_free', name='Lead-free brass (CuZn21Si3P / C69300, or CW510L low-lead)', cls='metal', status='polari_preferred',
      feedstocks=[F('copper, zinc, silicon', 'none')], end_of_life='recyclable', note='heat-set inserts, standoffs', confidence='good'),
 dict(id='brass_leaded', name='Leaded free-machining brass (CuZn39Pb3 / C36000)', cls='metal', status='legacy_harmful',
      feedstocks=[F('lead (2-3.5%)', '2A', 'inorganic lead compounds 2A; metallic lead 2B; neurotoxic')],
      end_of_life='recyclable but lead carries over', replaced_by=['brass_lead_free'],
      note='the usual heat-set insert alloy today; RoHS currently exempts it', confidence='good'),
 dict(id='zinc_alloy', name='Zinc die-cast (Zamak)', cls='metal', status='polari_acceptable',
      feedstocks=[F('zinc, aluminium, small Cu/Mg', 'none')], end_of_life='recyclable', caveats=['creeps under sustained load'], confidence='good'),
 dict(id='ndfeb', name='NdFeB magnet', cls='metal', status='polari_acceptable',
      feedstocks=[F('neodymium / rare earths', 'none', 'mining + separation has heavy environmental cost')],
      end_of_life='recyclable in principle, rarely in practice', caveats=['design for removal and reuse'], confidence='good'),
 dict(id='glass_fibre_cord', name='Continuous glass fibre (belt cords)', cls='fibre', status='polari_preferred',
      feedstocks=[F('silica sand, limestone, etc.', 'none', 'continuous filament glass: IARC 3')], end_of_life='not recoverable from belt', confidence='good'),
 dict(id='aramid_cord', name='Aramid fibre (belt cords)', cls='fibre', status='polari_acceptable',
      feedstocks=[F('p-phenylenediamine', 'none', 'skin sensitiser'), F('terephthaloyl chloride', 'none')], confidence='good'),
 dict(id='steel_cord', name='Steel cord', cls='fibre', status='polari_preferred', feedstocks=[F('steel', 'none')],
      end_of_life='recoverable from shredded belts', confidence='good'),

 # ---------------- coatings / surface processes ----------------
 dict(id='zinc_trivalent', name='Zinc plating, trivalent (Cr III) passivation', cls='coating', status='polari_preferred',
      feedstocks=[F('zinc, Cr(III) passivate', 'none')], confidence='good'),
 dict(id='black_oxide', name='Black oxide + oil', cls='coating', status='polari_preferred',
      feedstocks=[F('alkaline nitrate/nitrite salt bath', 'none')], caveats=['mild corrosion protection only'], confidence='good'),
 dict(id='anodise', name='Anodising (sulfuric acid, clear or dyed)', cls='coating', status='polari_preferred',
      feedstocks=[F('sulfuric acid', 'none', 'strong-inorganic-acid MISTS are IARC 1: an occupational control, not in the part')],
      caveats=['seal without nickel acetate where possible'], confidence='good'),
 dict(id='nitriding', name='Nitriding / nitrocarburising', cls='coating', status='polari_preferred',
      feedstocks=[F('ammonia / nitrogen atmosphere', 'none')], note='hard wear surface instead of hard chrome', confidence='good'),
 dict(id='nickel_plating', name='Electroless / electro nickel', cls='coating', status='polari_acceptable',
      feedstocks=[F('nickel salts', '1', 'nickel compounds IARC 1 in the bath; plated metal is 2B and a contact allergen')],
      caveats=['bath control; skin-contact parts avoid it'], confidence='good'),
 dict(id='zinc_hexavalent', name='Zinc plating, hexavalent chromate (yellow) passivation', cls='coating', status='legacy_harmful',
      feedstocks=[F('hexavalent chromium', '1')], replaced_by=['zinc_trivalent'], note='banned in EU vehicles/electronics (ELV, RoHS)', confidence='good'),
 dict(id='hard_chrome', name='Hard chrome plating (from Cr VI bath)', cls='coating', status='legacy_harmful',
      feedstocks=[F('chromic acid (hexavalent chromium)', '1')], replaced_by=['nitriding', 'stainless_a2_a4'],
      note='"chrome-plated" linear shafts', confidence='good'),
 dict(id='cadmium_plating', name='Cadmium plating', cls='coating', status='legacy_harmful',
      feedstocks=[F('cadmium', '1')], replaced_by=['zinc_trivalent'], note='old aerospace/military fasteners', confidence='good'),

 # ---------------- additives worth tracking ----------------
 dict(id='accel_nitrosamine', name='Nitrosamine-forming accelerators (TMTD, ZDMC...)', cls='additive', status='legacy_harmful',
      feedstocks=[F('forms N-nitrosodimethylamine', '2A')], replaced_by=['accel_nitrosamine_safe'], confidence='good'),
 dict(id='accel_nitrosamine_safe', name='Nitrosamine-safe accelerators (ZBEC, TBzTD) / peroxide cure', cls='additive', status='polari_preferred',
      feedstocks=[F('dibenzylamine-based', 'none')], confidence='good'),
 dict(id='ppd6', name='6PPD antiozonant', cls='additive', status='legacy_harmful',
      feedstocks=[F('6PPD -> 6PPD-quinone', 'none', 'acutely lethal to coho salmon')], replaced_by=['epdm_peroxide'],
      note='avoid by choosing ozone-resistant polymers rather than protecting ozone-weak ones', confidence='good'),
 dict(id='carbon_black', name='Carbon black filler', cls='additive', status='polari_acceptable',
      feedstocks=[F('carbon black', '2B', 'as inhalable dust during compounding; bound in rubber')], confidence='good'),
]

# part family -> roles. Families match MECH_KIT_PARTS_CATALOGUE.md section 1 / part_materials.json.
ROLES = [
 ('frame_profile', 'T-slot / V-slot extrusion', ['al_6063'], ['al_6061'], [], 'finish: anodise (clear or black); prefer recycled content'),
 ('frame_joint', 'cast corner / cube bracket', ['al_diecast'], ['zinc_alloy'], [], ''),
 ('frame_joint', 'flat joining plate', ['steel_carbon+zinc_trivalent', 'al_6061'], ['stainless_a2_a4'], ['zinc_hexavalent'], ''),
 ('frame_joint', 'end cap', ['pp'], ['pa66', 'petg'], ['abs'], ''),
 ('slot_fastener', 'T-nut (sliding / drop-in / roll-in)', ['steel_carbon+zinc_trivalent'], ['stainless_a2_a4', 'petg'], ['zinc_hexavalent', 'cadmium_plating'], ''),
 ('screw', 'socket cap / button / countersunk / set', ['steel_carbon+black_oxide', 'stainless_a2_a4'], ['steel_carbon+zinc_trivalent', 'pa66'], ['zinc_hexavalent', 'cadmium_plating'], 'class 8.8-12.9 per ISO 898-1, A2/A4-70 per ISO 3506-1'),
 ('nut', 'hex / flange / thin', ['steel_carbon+zinc_trivalent', 'stainless_a2_a4'], ['pa66', 'brass_lead_free'], ['zinc_hexavalent', 'brass_leaded'], ''),
 ('nut', 'nyloc', ['steel_carbon+pa66', 'stainless_a2_a4+pa66'], [], [], 'insert is PA66'),
 ('washer', 'flat / large / spring', ['steel_carbon+zinc_trivalent', 'stainless_a2_a4'], ['pa66'], ['zinc_hexavalent'], ''),
 ('insert', 'heat-set insert', ['brass_lead_free'], ['stainless_a2_a4'], ['brass_leaded'], 'today most heat-set inserts are leaded brass'),
 ('standoff', 'hex standoff / pillar', ['brass_lead_free', 'al_6061', 'pa66'], ['stainless_a2_a4', 'nickel_plating'], ['brass_leaded'], ''),
 ('rod_pin', 'threaded rod', ['steel_carbon+zinc_trivalent', 'stainless_a2_a4'], [], ['zinc_hexavalent'], ''),
 ('rod_pin', 'dowel / spring pin', ['steel_carbon', 'stainless_a2_a4'], [], [], ''),
 ('retaining_ring', 'circlip / E-clip', ['steel_carbon+black_oxide', 'stainless_a2_a4'], [], ['cadmium_plating'], 'spring steel'),
 ('bearing', 'deep-groove ball bearing', ['steel_carbon (52100) + steel_carbon shield (ZZ)'], ['stainless_a2_a4 (440C)', 'steel_carbon + aem seal'], ['nbr_hnbr (2RS seal)'], 'standard 2RS seals are NBR. EPDM is NOT suitable: it swells in mineral-oil bearing grease. ZZ shields avoid an elastomer entirely'),
 ('linear', 'linear bushing LMxUU', ['steel_carbon + pa66 retainer'], [], ['pom (retainer)'], ''),
 ('linear', 'profile rail + carriage', ['steel_carbon', 'stainless_a2_a4'], [], ['nbr_hnbr (end seals)'], ''),
 ('linear', 'smooth shaft', ['steel_carbon+nitriding', 'stainless_a2_a4'], [], ['hard_chrome'], 'most cheap shafts are hard-chrome plated'),
 ('linear', 'V-slot wheel', ['uhmwpe', 'pa66'], ['tpc_et'], ['pom', 'pc_bpa'], 'standard wheels are POM ("Delrin") or PC ("Xtreme")'),
 ('linear', 'low-friction slider / pad', ['uhmwpe'], ['pa11', 'peek'], ['ptfe', 'pom'], ''),
 ('transmission', 'timing belt body', ['tpu_mdi'], ['tpc_et', 'epdm_peroxide'], ['neoprene_cr'], ''),
 ('transmission', 'timing belt cords', ['steel_cord', 'glass_fibre_cord'], ['aramid_cord'], [], ''),
 ('transmission', 'timing pulley / idler', ['al_6061'], ['pa66', 'petg'], ['pom'], ''),
 ('transmission', 'lead screw', ['stainless_a2_a4'], [], [], ''),
 ('transmission', 'lead screw nut', ['brass_lead_free', 'pa66'], ['pa11'], ['pom', 'brass_leaded'], ''),
 ('transmission', 'shaft coupling', ['al_6061'], ['steel_carbon'], [], ''),
 ('transmission', 'coupling spider (jaw)', ['tpu_mdi'], ['tpc_et'], ['nbr_hnbr'], ''),
 ('transmission', 'spur gear', ['steel_carbon', 'pa66'], ['brass_lead_free', 'pla', 'petg'], ['pom', 'brass_leaded'], ''),
 ('misc', 'spring', ['steel_carbon', 'stainless_a2_a4'], [], [], 'music wire / 302'),
 ('misc', 'magnet', ['ndfeb'], [], [], 'design for removal'),
 ('misc', 'cable chain / zip tie', ['pa66'], ['pp'], [], ''),
 ('misc', 'cable insulation / tubing', ['tpu_mdi', 'pp'], ['silicone_vmq'], ['pvc', 'ptfe'], ''),
 ('misc', 'levelling-foot pad, damper', ['natural_rubber', 'epdm_peroxide'], ['tpu_mdi'], ['sbr', 'neoprene_cr'], ''),
 ('misc', 'gasket / seal', ['epdm_peroxide'], ['silicone_vmq', 'aem'], ['neoprene_cr', 'nbr_hnbr', 'fkm'], 'oil-exposed: aem'),
 ('printed_part', 'printed bracket / mount', ['petg', 'pla'], ['pa66', 'pp'], ['abs'], ''),
]

IDS = {m['id'] for m in MATERIALS}
def refs(xs):  # 'steel_carbon+zinc_trivalent' or 'steel_carbon (52100) + epdm seal' -> ids found
    out = []
    for x in xs:
        for tok in x.replace('(', ' ').replace(')', ' ').replace('+', ' ').split():
            if tok in IDS: out.append(tok)
    return out
problems = []
for c, p, d, a, l, n in ROLES:
    for x in refs(d) + refs(a) + refs(l): pass
    for x in d + a + l:
        if not refs([x]): problems.append((p, x))
for m in MATERIALS:
    for r in m.get('replaced_by', []):
        if r not in IDS: problems.append((m['id'], r))
assert not problems, problems

meta = dict(compiled='2026-11-03', by='econ-core (Claude) for Dustin Etts',
            status_vocabulary={'polari_preferred': 'default for new Polari designs',
                               'polari_acceptable': 'usable with the named caveat',
                               'legacy_harmful': 'comparison / existing parts only; not for new designs'},
            rule='preferred = no IARC 1/2A/2B monomer or process chemical isolated and handled in bulk to make it, plus a workable end of life',
            iarc_groups={'1': 'carcinogenic', '2A': 'probably', '2B': 'possibly', '3': 'not classifiable', 'none': 'not evaluated / not applicable', 'check': 'to confirm'},
            caution='compiled from knowledge, not yet checked row by row against the IARC monographs; review rows with confidence=check first')
roles = [dict(category=c, part=p, polari_default=d, polari_alternatives=a, legacy_harmful=l,
              default_ids=refs(d), alternative_ids=refs(a), legacy_ids=refs(l), notes=n) for c, p, d, a, l, n in ROLES]

def worst(m):
    order = {'1': 0, '2A': 1, '2B': 2, 'check': 3, '3': 4, 'none': 5}
    return min((f['iarc'] for f in m['feedstocks']), key=lambda g: order.get(g, 9), default='none')
for m in MATERIALS:
    m.setdefault('source', 'collab-mech-parts')
    m['worst_feedstock_iarc'] = worst(m)
json.dump(dict(meta=meta, materials=MATERIALS), open(os.path.join(H, 'materials_registry.json'), 'w'), indent=1)
json.dump(dict(meta=meta, part_material_roles=roles), open(os.path.join(H, 'part_material_roles.json'), 'w'), indent=1)

from collections import Counter
by_source = dict(Counter(m['source'] for m in MATERIALS))
provenance = dict(
    what='mech material registry: materials with IARC-classed feedstocks + status, and per-part-family material preferences',
    authored='econ-core (Claude) for Dustin Etts, 2026-11-03',
    from_='the materials work carried in MECH_FREECAD_INTERCHANGE_PLAN.md section 7 (collab/mech-parts/data/build_materials.py)',
    basis='IARC monograph group per feedstock row as the data states it; status by the rule in meta.rule; '
          'basis of each judgement is iarc (monograph class), regulation (EU/US rule) or assessment (engineering judgement)',
    not_yet_checked='iarc rows not yet checked against the monographs; AEM methyl acrylate marked check; '
                    'the two wood rows (mech-mxc-1 additions) marked check',
    counts=dict(materials=len(MATERIALS), by_source=by_source,
                by_status=dict(Counter(m['status'] for m in MATERIALS)), part_roles=len(roles)),
    files=['materials_registry.json', 'part_material_roles.json'],
    generator='build_registry.py (this directory)',
    seed='mech/mech_material_seed.py is generated from these files by build_seed.py; edit here, not there',
)
json.dump(provenance, open(os.path.join(H, 'REGISTRY.json'), 'w'), indent=1)
print(len(MATERIALS), 'materials', dict(Counter(m['status'] for m in MATERIALS)), by_source, '|', len(roles), 'part roles')
