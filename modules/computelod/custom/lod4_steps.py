"""
@module computelod.custom.lod4_steps

FABRICATION AS ROWS (lod-4b, 2026-09-26; plan §H.3): lod-4 entered the fabrication → materials rung by reference (the
`sky130` SiliconProcessNode → sifet's electronic-grade silicon) and said the metal stack, gate oxide, poly and dopants were
"named as not modelled". This flow writes the process ROUTE down in PSPP's own vocabulary — the classes the concept tree
already names for the fabrication rung (`ProcessingStage`, `MaterialProcessDefinition`) — for BOTH branches, and is honest
about what each row rests on:

    SKY130    the PDK publishes its LAYER STACK (the drawing layers and their purposes: wells, diffusion, poly, implants,
              contacts, local interconnect, five metals, passivation) and the process description of its README — it does
              NOT publish SkyWater's recipe (temperatures, doses, gas flows: the foundry's). So the STAGES are the wafer
              states the documented layers imply, cited to the PDK docs (URL + the quoted layer descriptions, read
              2026-09-26); the UNIT PROCESSES that produce them (lithography, implantation, oxidation, deposition, etch,
              metallization, CMP, anneal) are the textbook CMOS operations each layer requires — cited to Plummer, Deal &
              Griffin, "Silicon VLSI Technology" (Prentice Hall, 2000), evidence `analytical`, with the sentence "SkyWater's
              actual recipe is proprietary and not here" on every row. The materials each stage adds are NAMED (Si, SiO2,
              poly-Si, B/P/As dopants, Si3N4, W plugs, Al/Cu metal, TiN barriers) — names, not material rows (which would
              need their own sources).
    CNT       cntfet already carries the aligned-CNT process as parameter rows (cnt_process: purification, alignment,
              placement, contacts, lithography, gate stack — each with its own `source` and `confidence`). lod-4b maps the
              same route onto the SAME PSPP classes BY REFERENCE: every stage / process row names the cntfet row that holds
              its numbers and says the parameters are `engineering prior — TUNABLE` where that row says so.

Rows: 8 + 6 ProcessingStage (families `silicon-cmos-sky130`, `aligned-cnt`), 8 + 6 MaterialProcessDefinition (all
TRANSFORMATIVE; PSPP invariant I2 — a definition's effect is declared, never inferred). The lod-4 mapping
`lod4: fabrication → materials` is REPLACED by name with the route and its named materials; the CNT branch gains
`lod4b-cnt: fabrication → materials`. Nothing is fetched at run time (a reading); the report records the citations.

    python3 -m computelod.custom.lod4_steps run
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'lod4')
READ_ON = '2026-09-26'
PDK_LAYERS_URL = 'https://skywater-pdk.readthedocs.io/en/main/rules/layers.html'
PDK_RULES_URL = 'https://skywater-pdk.readthedocs.io/en/main/rules/summary.html'
PDK_README_URL = 'https://github.com/google/skywater-pdk/blob/main/README.rst'
TEXTBOOK = {'key': '[PDG00]', 'citation': 'J. D. Plummer, M. D. Deal, P. B. Griffin, "Silicon VLSI Technology: Fundamentals, Practice and Modeling", Prentice Hall, 2000 (ISBN 0-13-085037-3)',
            'role': 'the standard CMOS unit processes each documented SKY130 layer requires; NOT SkyWater\'s recipe, which is proprietary and not published in the PDK'}
README_QUOTE = ('"The SKY130 is a mature 180nm-130nm hybrid technology originally developed internally by Cypress Semiconductor before being spun out into SkyWater Technology" · '
                '"Support for internal 1.8V with 5.0V I/Os (operable at 2.5V) · 1 level of local interconnect · 5 levels of metal · Is inductor-capable · Has high sheet rho poly resistor · '
                'Optional MiM capacitors · Includes SONOS shrunken cell · Supports 10V regulated supply · HV extended-drain NMOS and PMOS"')
NOT_HERE = 'SkyWater\'s actual recipe (temperatures, doses, gas chemistries, film thicknesses beyond the models\' toxe) is proprietary and NOT in the PDK — not here either'
_PROV_SKY = 'computelod lod-4b (2026-09-26): SKY130 layer stack read from the PDK docs (%s, %s, %s); unit processes per %s' % (PDK_LAYERS_URL, PDK_RULES_URL, PDK_README_URL, TEXTBOOK['key'])
_PROV_CNT = 'computelod lod-4b (2026-09-26): the aligned-CNT route as cntfet\'s cnt_process rows carry it (process_set s1-target-line), mapped onto PSPP\'s classes by reference'
FAM_SKY, FAM_CNT = 'silicon-cmos-sky130', 'aligned-cnt'

#: the SKY130 route: (stage name, display, prior stage, the PDK layers it corresponds to (quoted purposes), materials added (names), the unit processes)
SKY130_STAGES = [
    ('sky130-eg-si-wafer', 'Electronic-grade Si wafer', '', {}, ['Si (electronic-grade, 9N–11N — sifet SiliconGrade eg-si via RefinementRoute siemens-route)'], [],
     'the substrate lod-4 reached by reference; p-type bulk for the n devices (the PDK\'s `tap` layer is "type equal to the well/substrate underneath")'),
    ('sky130-wells', 'Wells formed', 'sky130-eg-si-wafer', {'dnwell': 'Deep n-well region', 'nwell': 'N-well region'}, ['P and/or As dopant (n-well), B (p-well/substrate tuning)'], ['sky130-photolithography', 'sky130-ion-implantation', 'sky130-anneal'],
     'the well regions the layer stack names; a deep n-well for isolation'),
    ('sky130-active', 'Active areas isolated', 'sky130-wells', {'diff': 'Active (diffusion) area (type opposite of well/substrate underneath)', 'tap': 'Active (diffusion) area (type equal to the well/substrate underneath)'},
     ['SiO2 (field isolation)', 'Si3N4 (pad / stop layers)'], ['sky130-photolithography', 'sky130-plasma-etch', 'sky130-thermal-oxidation', 'sky130-lpcvd-deposition', 'sky130-cmp'],
     'diffusion and tap openings — the isolation between them (LOCOS or STI: WHICH is not published; the layer is)'),
    ('sky130-gate-stack', 'Gate stack formed', 'sky130-active', {'poly': 'Polysilicon', 'hvi': 'High voltage (5.0V) thick oxide gate regions', 'hvtp': 'High-Vt LVPMOS implant', 'lvtn': 'Low-Vt NMOS device'},
     ['SiO2 gate dielectric (the models\' toxe 4.148 nm for the 1.8 V nfet — lod-3b/4c cards; a thicker oxide where `hvi` is drawn)', 'poly-Si (gate)', 'B / As Vt-adjust implants (hvtp, lvtn)'],
     ['sky130-thermal-oxidation', 'sky130-ion-implantation', 'sky130-lpcvd-deposition', 'sky130-photolithography', 'sky130-plasma-etch'],
     'two gate oxides (1.8 V core, 5 V `hvi`) and the Vt flavours as implants — the models we ran in lod-4c are of THIS stack (nfet_01v8: vth0 0.519 V, toxe 4.148 nm in the tt card)'),
    ('sky130-source-drain', 'Source/drain implanted', 'sky130-gate-stack', {'nsdm': 'N+ source/drain implant', 'psdm': 'P+ source/drain implant', 'rpm': '300 ohms/square polysilicon resistor implant'},
     ['As / P (n+), B (p+) dopants'], ['sky130-photolithography', 'sky130-ion-implantation', 'sky130-anneal'],
     'the self-aligned source/drain (and the poly resistor implant the README\'s "high sheet rho poly resistor" refers to)'),
    ('sky130-contacts-li', 'Contacts + local interconnect', 'sky130-source-drain', {'npc': 'Nitride poly cut (under licon1 areas)', 'licon1': 'Contact to local interconnect', 'li1': 'Local interconnect', 'mcon': 'Contact from local interconnect to metal1'},
     ['Si3N4 (the nitride the `npc` cut opens)', 'contact plug metal (W plugs are the textbook choice; the PDK does not say)', 'local-interconnect metal (TiN-class; the PDK does not say)'],
     ['sky130-lpcvd-deposition', 'sky130-photolithography', 'sky130-plasma-etch', 'sky130-metallization', 'sky130-cmp'],
     'the "1 level of local interconnect" the README names — lod-3c extracted its capacitances on the cells'),
    ('sky130-metal-stack', 'Five metals + vias', 'sky130-contacts-li', {'met1': 'Metal 1', 'via': 'Contact from metal 1 to metal 2', 'met2': 'Metal 2', 'via2': 'Contact from metal 2 to metal 3', 'met3': 'Metal 3', 'via3': 'Contact from metal 3 to metal 4', 'met4': 'Metal 4', 'via4': 'Contact from metal 4 to metal 5', 'met5': 'Metal 5'},
     ['Al (or Cu) interconnect metal — the PDK does not say which', 'inter-metal dielectric SiO2', 'via plug metal (W)', 'optional MiM capacitor dielectric (capm)'],
     ['sky130-metallization', 'sky130-photolithography', 'sky130-plasma-etch', 'sky130-lpcvd-deposition', 'sky130-cmp'],
     'the "5 levels of metal" — lod-3e routed the adder on met1–met5 (3002 µm of wire, 1186 vias, as-flow)'),
    ('sky130-passivation', 'Passivated die', 'sky130-metal-stack', {'nsm': 'Nitride seal mask', 'pad': 'Passivation cut (opening over pads)'}, ['Si3N4 seal', 'pad metal exposed'],
     ['sky130-lpcvd-deposition', 'sky130-photolithography', 'sky130-plasma-etch'], 'the finished wafer; packaging is NOT a rung (D1)'),
]
#: the unit processes (MaterialProcessDefinition rows), all TRANSFORMATIVE — the textbook operations the layers require
SKY130_PROCESSES = [
    ('sky130-photolithography', 'Photolithography (pattern a layer)', 'patterning', '', 'resist coat → expose the layer\'s mask → develop: every drawn layer of the stack is one or more of these; the PDK\'s rules (min width/space per layer) are its footprint'),
    ('sky130-ion-implantation', 'Ion implantation (dope)', 'doping', '', 'wells, Vt adjust (hvtp/lvtn), source/drain (nsdm/psdm), resistor (rpm): the implant layers of the stack; doses/energies are the recipe — not published'),
    ('sky130-thermal-oxidation', 'Thermal oxidation (grow SiO2)', 'film-growth', 'conventional-heating', 'the gate oxides (thin 1.8 V core; thick where `hvi` is drawn) and field oxide; the models\' toxe is the only published thickness'),
    ('sky130-lpcvd-deposition', 'CVD deposition (poly, nitride, oxide)', 'deposition', 'conventional-heating', 'polysilicon gates, nitride stop/seal layers, inter-layer dielectrics'),
    ('sky130-plasma-etch', 'Plasma etch (remove where unmasked)', 'removal', 'rf', 'anisotropic etch of poly, contacts, vias, metals after each lithography'),
    ('sky130-metallization', 'Metallization (plugs, li, five metals)', 'deposition', '', 'contact/via plug fill and the interconnect metals; which metals SkyWater uses is not published — Al/W/TiN are the textbook set for this generation'),
    ('sky130-cmp', 'Chemical-mechanical planarization', 'planarization', '', 'planarize after isolation, plugs and each metal — what makes five levels stackable'),
    ('sky130-anneal', 'Anneal / activation', 'heating', 'conventional-heating', 'dopant activation and damage repair after implants (RTA or furnace: not published)'),
]
#: the CNT route (cntfet cnt_process rows by name): (stage, display, prior, cntfet row class:name, materials named, process row name)
CNT_STAGES = [
    ('cnt-purified-solution', 'Purified s-SWCNT solution', '', 'CNTPurificationProcess:s1-target-purification', ['semiconducting single-wall CNTs (purity 0.9999 — [HIL19] anchor), solvent/surfactant (not modelled)'], 'cnt-purification'),
    ('cnt-aligned-film', 'Aligned CNT film', 'cnt-purified-solution', 'CNTAlignmentProcess:s1-target-alignment', ['aligned CNT array on the substrate'], 'cnt-alignment'),
    ('cnt-placed-channel', 'Placed channel', 'cnt-aligned-film', 'CNTPlacementProcess:s1-target-placement', ['CNTs at the channel pitch (one tube at the S1 scope)'], 'cnt-placement'),
    ('cnt-contacts-formed', 'Contacts formed', 'cnt-placed-channel', 'ContactFormationProcess:s1-target-contacts', ['contact metal (Rc median 5.5 kΩ per the row — [VS1]/[FC10])'], 'cnt-contact-formation'),
    ('cnt-gate-stack-formed', 'Gate stack formed', 'cnt-contacts-formed', 'GateStackProcess:s1-target-gatestack', ['gate dielectric (tox σ 0.1 nm, k σ 0.5 per the row)', 'gate metal'], 'cnt-gate-stack'),
    ('cnt-patterned-device', 'Patterned device', 'cnt-gate-stack-formed', 'LithographyProcess:s1-target-litho', [], 'cnt-lithography'),
]
CNT_PROCESSES = [
    ('cnt-purification', 'CNT purification (semiconducting sort)', 'separation', '', 'CNTPurificationProcess:s1-target-purification'),
    ('cnt-alignment', 'CNT alignment', 'deposition', '', 'CNTAlignmentProcess:s1-target-alignment'),
    ('cnt-placement', 'CNT placement (pitch, yield)', 'patterning', '', 'CNTPlacementProcess:s1-target-placement'),
    ('cnt-contact-formation', 'Contact formation', 'deposition', '', 'ContactFormationProcess:s1-target-contacts'),
    ('cnt-gate-stack', 'Gate stack (dielectric + gate)', 'film-growth', '', 'GateStackProcess:s1-target-gatestack'),
    ('cnt-lithography', 'Lithography (feature/overlay σ)', 'patterning', '', 'LithographyProcess:s1-target-litho'),
]


def stage_rows():
    rows = []
    for name, disp, prior, layers, materials, procs, desc in SKY130_STAGES:
        rows.append({'name': name, 'display_name': disp, 'material_family': FAM_SKY, 'typical_prior_stage': prior, 'provenance_id': _PROV_SKY,
                     'description': '%s. PDK layers: %s. Materials added (named, not rows): %s. Unit processes: %s.' % (desc, '; '.join('`%s` = "%s"' % kv for kv in layers.items()) or 'none (the substrate)', '; '.join(materials) or 'none', ', '.join(procs) or 'none'),
                     'notes': NOT_HERE + '; layer purposes quoted from %s (read %s)' % (PDK_LAYERS_URL, READ_ON)})
    for name, disp, prior, ref, materials, proc in CNT_STAGES:
        rows.append({'name': name, 'display_name': disp, 'material_family': FAM_CNT, 'typical_prior_stage': prior, 'provenance_id': _PROV_CNT,
                     'description': 'The aligned-CNT route, stage after %s (cntfet row %s carries the parameters and their source/confidence). Materials (named): %s.' % (proc, ref, '; '.join(materials) or 'none'),
                     'notes': 'parameters live on the cntfet row by reference — where it says "engineering prior — TUNABLE", so does this stage'})
    return rows


def process_rows():
    rows = []
    for name, disp, ptype, energy, desc in SKY130_PROCESSES:
        rows.append({'name': name, 'display_name': disp, 'process_type': ptype, 'execution_effect': 'TRANSFORMATIVE', 'energy_deposition_model': energy, 'material_family': FAM_SKY,
                     'description': desc + '. ' + TEXTBOOK['role'], 'provenance_id': _PROV_SKY, 'notes': TEXTBOOK['citation'] + ' — ' + NOT_HERE,
                     'accepted_input_constraints_json': '{}', 'parameter_schema_json': json.dumps({'note': 'the recipe parameters (dose, energy, temperature, time, gas) are the foundry\'s — none published; the PDK\'s models carry only their consequences (toxe, vth0, …)'}),
                     'transformation_engine_refs_json': '[]', 'output_state_schema_json': '{}'})
    for name, disp, ptype, energy, ref in CNT_PROCESSES:
        rows.append({'name': name, 'display_name': disp, 'process_type': ptype, 'execution_effect': 'TRANSFORMATIVE', 'energy_deposition_model': energy, 'material_family': FAM_CNT,
                     'description': 'The aligned-CNT unit process whose parameters are cntfet row %s (its `source` and `confidence` are the evidence).' % ref, 'provenance_id': _PROV_CNT,
                     'notes': 'by reference to cntfet.cnt_process; the parameter carrier is that row', 'accepted_input_constraints_json': '{}', 'parameter_schema_json': json.dumps({'cntfet_row': ref}),
                     'transformation_engine_refs_json': '[]', 'output_state_schema_json': '{}'})
    return rows


def run():
    rep = {'read_on': READ_ON, 'sources': {'pdk_layers': PDK_LAYERS_URL, 'pdk_rules_summary': PDK_RULES_URL, 'pdk_readme': PDK_README_URL, 'readme_quote': README_QUOTE, 'textbook': TEXTBOOK},
           'not_here': NOT_HERE,
           'sky130': {'family': FAM_SKY, 'stages': [s[0] for s in SKY130_STAGES], 'processes': [p[0] for p in SKY130_PROCESSES],
                      'layers_covered': sorted({l for s in SKY130_STAGES for l in s[3]}), 'materials_named': sorted({m.split(' (')[0] for s in SKY130_STAGES for m in s[4]}),
                      'what_is_published': 'the drawing layers and their purposes, the design rules, the device models (toxe, vth0, …), the README\'s stack description',
                      'what_is_not': 'the recipe: temperatures, doses, gas chemistries, which isolation (LOCOS/STI), which metals (Al/Cu), plug and barrier materials'},
           'cnt': {'family': FAM_CNT, 'stages': [s[0] for s in CNT_STAGES], 'processes': [p[0] for p in CNT_PROCESSES], 'cntfet_rows': [s[3] for s in CNT_STAGES],
                   'note': 'the CNT branch\'s process rows already existed in cntfet (cnt_process); lod-4b maps them onto PSPP\'s classes by reference — the gap on that branch stays LAYOUT (lod-3), not process'},
           'rows': {'ProcessingStage': len(stage_rows()), 'MaterialProcessDefinition': len(process_rows())}}
    os.makedirs(OUT, exist_ok=True)
    from computelod.custom.repro import record
    rep['reproduction'] = record('computelod.custom.lod4_steps', inputs=[{'label': 'PDK layers page (quoted)', 'url': PDK_LAYERS_URL}, {'label': 'PDK rules summary', 'url': PDK_RULES_URL}, {'label': 'PDK README (quoted)', 'url': PDK_README_URL}, {'label': TEXTBOOK['key'], 'url': 'ISBN 0-13-085037-3'}],
                                 knobs={'read_on': READ_ON, 'families': [FAM_SKY, FAM_CNT]}, conditions={'reading': 'stages from the documented layers; unit processes per the textbook; CNT by reference to cntfet rows'},
                                 deterministic='a reading of documents, nothing computed')
    json.dump(rep, open(os.path.join(OUT, 'steps_report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'steps_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep, lod4_rep, lod3_rep):
    """REPLACE lod-4's `fabrication → materials` by name with the route + its named materials; ADD the CNT branch's."""
    if not rep or not lod4_rep or not lod3_rep:
        return [], []
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    fab_ref = 'SiliconProcessNode sky130 (130 nm planar bulk, 1.8 V core, L = 0.15 µm, 5 metals; Apache-2.0 PDK)'
    mats = rep['sky130']['materials_named']
    mat_ref = 'SiliconGrade eg-si (electronic-grade, 9N–11N) via RefinementRoute siemens-route + the stack\'s materials NAMED per stage: %s' % ', '.join(mats)
    ev = 'lod4/steps_report.json — ProcessingStage ×%d + MaterialProcessDefinition ×%d rows (PSPP classes), SKY130 stages from the PDK layer docs (%s, read %s), unit processes per %s; CNT by reference to cntfet.cnt_process' % (
        rep['rows']['ProcessingStage'], rep['rows']['MaterialProcessDefinition'], PDK_LAYERS_URL, READ_ON, TEXTBOOK['key'])
    maps = [
        M(name='lod4: fabrication → materials', kind='one-to-many', source_rung='fabrication', source_ref=fab_ref, target_rung='materials', target_ref=mat_ref,
          mapping_status='implemented', evidence_level='analytical', evidence_ref=ev,
          notes='lod-4b: the route is ROWS now — %d ProcessingStage rows (%s) produced by %d unit processes (%s); each stage names the materials it adds. %s. The substrate is eg-si by the Siemens route (sifet, cited there: [CEC12]).' % (
              len(rep['sky130']['stages']), ' → '.join(s.replace('sky130-', '') for s in rep['sky130']['stages']), len(rep['sky130']['processes']), ', '.join(p.replace('sky130-', '') for p in rep['sky130']['processes']), NOT_HERE),
          loss_note='the recipe (doses, temperatures, gases, exact films and metals) is the foundry\'s and absent; the rows carry what is published and name what is not'),
        M(name='lod4b-cnt: fabrication → materials', kind='one-to-many', source_rung='fabrication', source_ref='the aligned-CNT process route: %d ProcessingStage rows (%s) — parameters on cntfet\'s cnt_process rows (process_set s1-target-line)' % (len(rep['cnt']['stages']), ' → '.join(s.replace('cnt-', '') for s in rep['cnt']['stages'])),
          target_rung='materials', target_ref='semiconducting single-wall CNTs (purity 0.9999 per s1-target-purification, [HIL19]); contact metal, gate dielectric and gate metal NAMED (not rows)',
          mapping_status='proposed', evidence_level='analytical', evidence_ref=ev,
          notes='the CNT branch\'s fabrication → materials by reference; its parameters are engineering priors marked TUNABLE on the cntfet rows (confidence low/medium) — status proposed, not implemented: no line has made these devices here. The branch\'s gap stays LAYOUT (lod-3), not process.',
          loss_note='no measured process capability yet (the cntfet rows say so); materials named, not rows'),
    ]
    return maps, []


if __name__ == '__main__':
    print(json.dumps(run() if len(sys.argv) > 1 and sys.argv[1] == 'run' else (report() or 'no report yet: python3 -m computelod.custom.lod4_steps run'), indent=1))
