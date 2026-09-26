"""
@module computelod.custom.lod4_process

FABRICATION → MATERIALS (lod-4, first slice; plan §C Phase 5, the eleventh rung): the layout lod-3 read is
placed on the PROCESS that fabricates it, and the process on the MATERIAL it is made of — both by reference
to rows that already carry the discipline for such claims:

    layout → fabrication    a `SiliconProcessNode` row `sky130` (sifet's ladder shape: node, architecture, Vdd,
                            source, licence + rights class, fabrication evidence, the manufacturability RULE).
                            Seeded HERE (computelod) because the sifet ladder is a ratified reading of prior
                            nodes and the manufacturability ruling ("today: no rung qualifies") is a person's
                            to change — so `manufacturable` is left None (evidence-only) with the evidence
                            named, and D-lod4-1 asks for the ruling.
    fabrication → materials  sifet's `SiliconGrade` `eg-si` (electronic-grade, 9N–11N) reached by the
                            `siemens-route` RefinementRoute (mg-si → TCS → Czochralski) — the substrate; the
                            metal stack (Al, with W plugs in SKY130) is NAMED as not modelled.

Nothing is fetched: every number below was either read in lod-3 (L = 0.15 µm from the cell netlists, the
Apache-2.0 SPDX headers on the files) or is the PDK's own documentation, cited by URL. Evidence `analytical`.
The CNT branch cannot take this rung by the ladder (no layout, lod-3) — its process rows (cntfet
`cnt_process_basis`: alignment, placement, purification, contact, lithography, gate stack) are NAMED so the
gap is precise, not vague.

    python3 -m computelod.custom.lod4_process run
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'lod4')
PDK_DOCS = 'https://skywater-pdk.readthedocs.io/en/main/'
PDK_REPO = 'https://github.com/google/skywater-pdk'
OPEN_MPW = 'https://efabless.com/open_shuttle_program'

#: the process-node row, in sifet's SiliconProcessNode shape (its vocabularies: FABRICATION_EVIDENCE, RIGHTS_CLASS)
SKY130_NODE = {
    'name': 'sky130', 'display_name': 'SkyWater SKY130 (130 nm open foundry PDK)', 'node_nm': 130.0, 'architecture': 'planar-bulk', 'vdd_v': 1.8,
    'source': 'SKY130', 'source_url': PDK_REPO, 'licence': 'Apache-2.0', 'licence_verified': True, 'licence_gplv3_compatible': 'yes', 'rights_class': 'incorporable-open',
    'fabrication_evidence': 'measured-fabricated-device',
    'manufacturable': None,
    'manufacturability': 'proven-on-request',
    'manufacturable_reason': 'D-lod4-1 RULED 2026-09-26 (his): PROVEN ON REQUEST — SkyWater fabricates SKY130 as a production process, and Google-sponsored open MPW '
                             'shuttles (Efabless, 2020–2023) fabricated designs under this open PDK; fabrication might be requested from a third party (a shuttle or the foundry) '
                             'but no standing route is verified here — his `available` needs a named closed-source vendor taking orders, his `open` a fully open-source option AND route — '
                             'so `manufacturable` stays None; verify a vendor route (SkyWater direct or a paid shuttle) to move it to `available`.',
    'model_family': 'BSIM4',
    'key_numbers_json': json.dumps({
        'l_min_um': {'value': 0.15, 'unit': 'um', 'source': 'read in lod-3: every transistor of the seven mapped sky130_fd_sc_hd cells has l=150000u (scale 1e-6)', 'note': 'drawn gate length of the 1.8 V core devices'},
        'vdd_core_v': {'value': 1.8, 'unit': 'V', 'source': 'the Liberty corner tt_025C_1v80 (lod-2) and the sky130_fd_pr__*_01v8 device names', 'note': '1.8 V core; 5 V / HV devices exist in the PDK, not used here'},
        'metal_layers': {'value': 5, 'unit': 'layers', 'source': PDK_DOCS + ' (process stack: 5 levels of metal, local interconnect)', 'note': 'documentation, not read from a file here'},
        'device_flavours_used': {'value': ['sky130_fd_pr__nfet_01v8', 'sky130_fd_pr__pfet_01v8_hvt'], 'source': 'lod-3 netlists'},
    }),
    'what_we_can_use': 'the open PDK artefacts (cells, Liberty, LEF, SPICE models) under Apache-2.0 — read and cited in lod-2/lod-3; the process as the fabrication rung of the compute ladder',
    'what_we_must_not_assume': 'that a design mapped here can be fabricated TODAY (shuttle availability is a person\'s verification), or that the PDK\'s models equal a measured die of our own',
    'search_json': json.dumps({'have': ['PDK repo + docs', 'cell library files (lod-3)', 'Liberty corner (lod-2)'], 'missing': ['a current open-shuttle confirmation', 'a die measurement of our own']}),
    'evidence_json': '[]', 'notes': 'seeded by computelod lod-4 as the fabrication rung of the SKY130 branch; NOT part of the sifet ladder\'s ratified prior nodes', 'is_prior': True,
}


def run():
    rep = {'sky130': {'process_node': SKY130_NODE['name'], 'docs': PDK_DOCS, 'repo': PDK_REPO, 'open_mpw': OPEN_MPW,
                      'materials': {'substrate': {'grade': 'eg-si', 'route': 'siemens-route', 'source': 'sifet si_refinement seeds (SiliconGrade / RefinementRoute rows, cited there)'},
                                    'not_modelled': ['metal stack (Al / W plugs)', 'gate oxide and poly', 'dopants (B, P, As) as materials rows']}},
           'cnt': {'layout': None, 'process_rows_named': ['CNTAlignmentProcess', 'CNTPlacementProcess', 'CNTPurificationProcess', 'ContactFormationProcess', 'LithographyProcess', 'GateStackProcess'],
                   'note': 'the CNT branch cannot take the layout → fabrication rung (no layout, lod-3); its process rows exist in cntfet (cnt_process_basis) — the gap is layout, not process'},
           'decisions': {'D-lod4-1': 'RULED 2026-09-26 (his): a third category — manufacturability = proven-on-request (historically fabricated under the open PDK; a third party might take a request); manufacturable (open today) stays None.'}}
    os.makedirs(OUT, exist_ok=True)
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w'), indent=1)
    return rep


def report():
    p = os.path.join(OUT, 'report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def rows(rep, lod3_rep):
    """(compute_mappings, characterizations): REPLACE lod-3's partial layout → fabrication by name; ADD fabrication → materials."""
    if not rep or not lod3_rep:
        return [], []
    a = lod3_rep['adder']['sky130']
    lay_ref = 'sky130_fd_sc_hd LEF rv32_add: %.2f µm² over %d cell footprints' % (a['lef_area_um2'], a['cells'])
    fab_ref = 'SiliconProcessNode sky130 (130 nm planar bulk, 1.8 V core, L = 0.15 µm, 5 metals; Apache-2.0 PDK)'
    mat_ref = 'SiliconGrade eg-si (electronic-grade, 9N–11N) via RefinementRoute siemens-route; metal stack not modelled'
    ev = 'lod4/report.json — the PDK (%s, docs %s) + the lod-3 netlists; sifet SiliconGrade/RefinementRoute rows for the material' % (PDK_REPO, PDK_DOCS)
    M = lambda **k: dict({'description': '', 'validity_json': '{}', 'loss_note': '', 'uncertainty_json': '{}', 'notes': ''}, **k)
    maps = [
        M(name='lod3: layout → fabrication', kind='one-to-one', source_rung='layout', source_ref=lay_ref, target_rung='fabrication', target_ref=fab_ref,
          mapping_status='implemented', evidence_level='analytical', evidence_ref=ev,
          notes='RESOLVED by lod-4: the process is a SiliconProcessNode row in sifet\'s ladder shape (manufacturability = proven-on-request, manufacturable = None — D-lod4-1 ruled 2026-09-26). Lithography/implant/metal steps are not modelled as rows.'),
        M(name='lod4: fabrication → materials', kind='one-to-many', source_rung='fabrication', source_ref=fab_ref, target_rung='materials', target_ref=mat_ref,
          mapping_status='implemented', evidence_level='analytical', evidence_ref=ev,
          notes='the substrate is electronic-grade silicon reached by the Siemens route (sifet si_refinement, cited there: [CEC12]); the metal stack, gate oxide/poly and dopants are NAMED as not modelled — the materials rung is entered, not exhausted.'),
    ]
    return maps, []


if __name__ == '__main__':
    print(json.dumps(run() if len(sys.argv) > 1 and sys.argv[1] == 'run' else (report() or 'no report yet: python3 -m computelod.custom.lod4_process run'), indent=1))
