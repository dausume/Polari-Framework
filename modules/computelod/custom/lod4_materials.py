"""
@module computelod.custom.lod4_materials

MATERIALS AS ROWS (lod-4d, 2026-09-27; plan §H.6 slice 1). lod-4b wrote the SKY130 fabrication route as PSPP rows whose
stages NAME the materials they add (strings: Si, SiO2, poly-Si, B/P/As, Si3N4, W plugs, Al or Cu, TiN). This slice makes each
named material a ROW a person can open — the materials rung's own classes (`MaterialsScienceMaterial` identities, the
materials module's home; never a second materials database) with one `MaterialScaleDefinition` at scale 0 (experimental)
per material carrying the properties a chip cares about, EVERY NUMBER derived or cited:

    cited     a literature constant with its source key (Sze & Ng 2007 appendices for Si / SiO2 / Si3N4 / dopant levels;
              the CRC Handbook for the pure metals' resistivity, density, melting point)
    derived   computed here, at run time, from the PDK's OWN files — the sc_hd technology LEF (sheet resistance, thickness,
              area capacitance per routing layer; per-cut via resistance) and magic's sky130A.tech (layer heights, poly and
              diffusion/well sheet resistances) — cited by path + sha256, never committed (PDK content stays out of git);
              e.g. metal resistivity = RPERSQ × THICKNESS, the met1-to-substrate dielectric thickness = ε0·εr(SiO2)/C_area
              (cross-checked against magic's met1 height), poly resistivity from its Ω/□ and height
    inference what the PDK does NOT say and the textbook does (boron is the p-type species; W plugs, Al-with-barrier
              metal, TiN-class local interconnect are the generation's set) — marked `asserted_by_pdk: false`; the PDK's
              own numbers are then EVIDENCE for or against a candidate (the metals' effective resistivity 3.4–4.4 µΩ·cm
              sits 1.3–1.7× bulk Al and 2–2.6× bulk Cu), stated as evidence, never as the answer

The rows: `silicon` already exists (the materials basis' own identity) and only gains a scale row; the others are new
identities tagged `semiconductor-process` + `sky130`. Each SKY130 stage's named materials resolve to these rows
(STAGE_MATERIALS) or to an explicit NOT_MODELLED entry (the MiM capacitor dielectric, photoresist); the lod-4
`fabrication → materials` mapping's target_ref lists the rows, so the walk from `c = a + b` ends on objects.

    python3 -m computelod.custom.lod4_materials run      # parses the two PDK files, writes initialData/lod4/materials_report.json
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
OUT = os.path.join(MOD, 'initialData', 'lod4')
PROV = 'computelod lod-4d (2026-09-27): chip materials as rows — constants cited (Sze & Ng 2007; CRC Handbook), PDK-derived numbers computed from the sc_hd technology LEF and magic sky130A.tech (sha256 in the report)'
TAGS = ['semiconductor-process', 'sky130']
EPS0 = 8.8541878128e-12   # F/m (CODATA 2018)

#: the sources every number points at (keys used in the property rows)
SOURCES = {
    'SZE07': {'citation': 'S. M. Sze, K. K. Ng, "Physics of Semiconductor Devices", 3rd ed., Wiley, 2007 — appendices "Properties of Si and GaAs" and "Properties of SiO2 and Si3N4" (300 K), and the shallow-level ionization energies in Ch. 1',
              'kind': 'textbook'},
    'CRC': {'citation': 'CRC Handbook of Chemistry and Physics, 97th ed., CRC Press, 2016 — "Electrical Resistivity of Pure Metals" (20 °C) and "Physical Constants of Inorganic Compounds"', 'kind': 'handbook'},
    'PDG00': {'citation': 'J. D. Plummer, M. D. Deal, P. B. Griffin, "Silicon VLSI Technology", Prentice Hall, 2000 — the CMOS generation\'s material set (W plugs, Al interconnect with Ti/TiN barriers, doped poly gates, B / P / As dopants)', 'kind': 'textbook'},
    'PDK_TLEF': {'citation': 'SkyWater sky130A, sky130_fd_sc_hd technology LEF (nominal corner): libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef — LAYER … THICKNESS / RESISTANCE RPERSQ / CAPACITANCE CPERSQDIST, via RESISTANCE per cut',
                 'kind': 'pdk-file', 'repo': 'google/skywater-pdk (Apache-2.0); built by open_pdks, fetched with ciel (polari-eda-tools/fetch-pdk.sh)', 'file': 'sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef'},
    'PDK_MAGIC': {'citation': 'SkyWater sky130A magic technology file: libs.tech/magic/sky130A.tech — extract section `height <layer> <bottom µm> <thickness µm>` and `resist <layer> <mΩ/□>` (first extract style)',
                  'kind': 'pdk-file', 'repo': 'google/skywater-pdk (Apache-2.0) via open_pdks', 'file': 'sky130A/libs.tech/magic/sky130A.tech'},
    'LOD4C': {'citation': 'computelod lod-4c / lod-3b: the PDK\'s BSIM4 model cards as RUN here (tt corner) — toxe of nfet_01v8', 'kind': 'this-arc', 'file': 'lod4/devices_report.json'},
}
NOT_MODELLED = {
    'optional MiM capacitor dielectric (capm)': 'not modelled — the PDK draws the capacitor layers (capm / cap2m) but names no dielectric; a row would be a guess',
    'photoresist': 'not modelled — a consumable of every photolithography step, not a material of the finished die',
    'pad metal exposed': 'the interconnect metal itself (aluminium / copper candidate rows) exposed through the passivation cut — no separate material',
}


def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def pdk_root():
    from computelod.custom.eda_engines import PDK_ROOT
    return PDK_ROOT


def parse_tlef(path):
    """{layer: {'type', 'thickness_um', 'rpersq_ohm', 'cperdist_pf_per_um2', 'edgecap_pf_per_um', 'resistance_ohm_per_cut'}} from the technology LEF."""
    layers, cur = {}, None
    for line in open(path, errors='replace'):
        t = line.strip()
        m = re.match(r'^LAYER\s+(\S+)\s*$', t)      # a LAYER definition (the `LAYER x ;` lines inside VIA blocks end with `;` and are not)
        if m:
            cur = m.group(1); layers.setdefault(cur, {}); continue
        if t.startswith('END ') and cur and t.split()[1] == cur:
            cur = None; continue
        if not cur:
            continue
        m = re.match(r'^TYPE\s+(\S+)', t)
        if m:
            layers[cur]['type'] = m.group(1)
        m = re.match(r'^THICKNESS\s+([\d.Ee+-]+)', t)
        if m:
            layers[cur]['thickness_um'] = float(m.group(1))
        m = re.match(r'^RESISTANCE\s+RPERSQ\s+([\d.Ee+-]+)', t)
        if m:
            layers[cur]['rpersq_ohm'] = float(m.group(1))
        elif re.match(r'^RESISTANCE\s+([\d.Ee+-]+)\s*;', t):
            layers[cur]['resistance_ohm_per_cut'] = float(re.match(r'^RESISTANCE\s+([\d.Ee+-]+)', t).group(1))
        m = re.match(r'^CAPACITANCE\s+CPERSQDIST\s+([\d.Ee+-]+)', t)
        if m:
            layers[cur]['cperdist_pf_per_um2'] = float(m.group(1))
        m = re.match(r'^EDGECAPACITANCE\s+([\d.Ee+-]+)', t)
        if m:
            layers[cur]['edgecap_pf_per_um'] = float(m.group(1))
    return layers


def parse_magic_tech(path):
    """The FIRST extract style's `height` (bottom, thickness in µm) and `resist` (mΩ/□) lines: {'height': {layer: (bottom, thick)}, 'resist_ohm_per_sq': {layer: Ω/□}}."""
    heights, resist, in_extract, seen_style = {}, {}, False, 0
    for line in open(path, errors='replace'):
        t = line.strip()
        if t == 'extract':
            in_extract = True; continue
        if in_extract and t == 'end':
            break
        if not in_extract:
            continue
        if t.startswith('style '):
            seen_style += 1
            if seen_style > 1:
                break            # the first style only (the others are corner variants)
        m = re.match(r'^height\s+(\S+)\s+([\d.Ee+-]+)\s+([\d.Ee+-]+)', t)
        if m:
            for lay in m.group(1).split(','):
                heights[lay] = (float(m.group(2)), float(m.group(3)))
        m = re.match(r'^resist\s+(\S+)\s+([\d.Ee+-]+)', t)
        if m and m.group(1) not in resist:
            resist[m.group(1)] = float(m.group(2)) / 1000.0
    return {'height': heights, 'resist_ohm_per_sq': resist}


def _p(prop, value, unit, source, basis='cited', conditions='', derivation='', vmin=None, vmax=None, note=''):
    d = {'property': prop, 'unit': unit, 'source': source, 'basis': basis}
    if value is not None:
        d['value'] = value
    if vmin is not None:
        d['value_min'] = vmin; d['value_max'] = vmax
    if conditions:
        d['conditions'] = conditions
    if derivation:
        d['derivation'] = derivation
    if note:
        d['note'] = note
    return d


def derived_numbers(tlef, mag):
    """Every PDK-derived number, computed from the parsed files (the report keeps them; the rows point at them)."""
    out = {'metals': {}, 'vias': {}, 'poly': {}, 'diffusion': {}, 'li1': {}, 'dielectric': {}}
    for lay in ('met1', 'met2', 'met3', 'met4', 'met5'):
        L = tlef.get(lay, {})
        if 'rpersq_ohm' in L and 'thickness_um' in L:
            rho_uohm_cm = L['rpersq_ohm'] * L['thickness_um'] * 1e-4 * 1e6   # Ω/□ × cm = Ω·cm → µΩ·cm
            out['metals'][lay] = {'rpersq_ohm': L['rpersq_ohm'], 'thickness_um': L['thickness_um'], 'effective_resistivity_uohm_cm': round(rho_uohm_cm, 3),
                                  'magic_thickness_um': mag['height'].get('all' + lay.replace('met', 'm'), (None, None))[1]}
    for lay in ('mcon', 'via', 'via2', 'via3', 'via4'):
        if 'resistance_ohm_per_cut' in tlef.get(lay, {}):
            out['vias'][lay] = tlef[lay]['resistance_ohm_per_cut']
    li = tlef.get('li1', {})
    if 'rpersq_ohm' in li and 'thickness_um' in li:
        out['li1'] = {'rpersq_ohm': li['rpersq_ohm'], 'thickness_um': li['thickness_um'], 'effective_resistivity_uohm_cm': round(li['rpersq_ohm'] * li['thickness_um'] * 100.0, 1)}
    pr = mag['resist_ohm_per_sq']; ph = mag['height']
    if 'allpoly' in ph and ('(allpolynonres)/active' in pr or 'rmp/active' in pr):
        rs = pr.get('(allpolynonres)/active', pr.get('rmp/active'))
        out['poly'] = {'rpersq_ohm': rs, 'thickness_um': ph['allpoly'][1], 'resistivity_ohm_cm': round(rs * ph['allpoly'][1] * 1e-4, 6),
                       'resistor_flavours_ohm_per_sq': {k.split('/')[0]: v for k, v in pr.items() if 'poly' in k and 'nonres' not in k}}
    _key = lambda k: k.split('/')[0].strip('()').split(',')[0].lstrip('*')   # '(*ndiff,nsd)/active' → 'ndiff'
    out['diffusion'] = {_key(k): v for k, v in pr.items() if k.endswith('/active') and ('diff' in k or 'sd' in k) and 'res' not in k}
    out['diffusion'].update({_key(k): v for k, v in pr.items() if k.endswith('/well') and 'rpw' not in k})
    m1 = tlef.get('met1', {})
    if 'cperdist_pf_per_um2' in m1:
        c_f_per_m2 = m1['cperdist_pf_per_um2'] * 1e-12 / 1e-12          # pF/µm² → F/m²  (1e-12 F per pF, 1e12 µm² per m²)
        d_um = EPS0 * 3.9 / c_f_per_m2 * 1e6
        out['dielectric'] = {'met1_cperdist_pf_per_um2': m1['cperdist_pf_per_um2'], 'implied_thickness_um_if_sio2': round(d_um, 3), 'magic_met1_bottom_um': ph.get('allm1', (None,))[0],
                             'reading': 'ε0·3.9 / C_area = the dielectric thickness under met1 IF it is SiO2 (εr 3.9): %.2f µm vs magic\'s met1 bottom height %.3f µm — agreement to %.0f %% is evidence the inter-layer dielectric is SiO2-class' % (
                                 d_um, ph.get('allm1', (0,))[0] or 0, 100.0 * abs(d_um - (ph.get('allm1', (0,))[0] or d_um)) / d_um)}
    return out


def materials(derived):
    """The material identities and their property rows (a list of dicts; `existing` = the basis already holds the identity)."""
    D = derived
    met = D.get('metals', {}); vias = D.get('vias', {}); poly = D.get('poly', {}); diff = D.get('diffusion', {}); li = D.get('li1', {}); die = D.get('dielectric', {})
    al_bulk, cu_bulk, w_bulk = 2.65, 1.68, 5.28
    eff = [m['effective_resistivity_uohm_cm'] for m in met.values()]
    metal_evidence = ('the PDK\'s five metals: RPERSQ × THICKNESS = %s µΩ·cm effective (met1…met5) — %.1f–%.1f× bulk Al (%.2f), %.1f–%.1f× bulk Cu (%.2f); a barrier-clad Al film reads 1.3–1.7× bulk, a Cu damascene film ~1.1–1.3×' % (
        ', '.join('%.2f' % e for e in eff), min(eff) / al_bulk, max(eff) / al_bulk, al_bulk, min(eff) / cu_bulk, max(eff) / cu_bulk, cu_bulk)) if eff else 'no metal layers parsed'
    rows = [
        {'name': 'silicon', 'existing': True, 'display': 'Silicon (crystalline)', 'elements': ['Si'], 'role': 'the substrate and every device region (wells, channels, source/drain); electronic-grade via the Siemens route (sifet SiliconGrade eg-si)',
         'asserted_by_pdk': True, 'stages': ['sky130-eg-si-wafer'],
         'properties': [_p('relative_permittivity', 11.9, '', 'SZE07', conditions='300 K'), _p('bandgap', 1.12, 'eV', 'SZE07', conditions='300 K, indirect'), _p('density', 2.329, 'g/cm³', 'SZE07'),
                        _p('intrinsic_resistivity', 3.2e5, 'Ω·cm', 'SZE07', conditions='300 K, undoped'), _p('intrinsic_carrier_concentration', 9.65e9, 'cm⁻³', 'SZE07', conditions='300 K'),
                        _p('breakdown_field', 3e5, 'V/cm', 'SZE07', note='order of magnitude; doping-dependent')]
                       + [_p('sheet_resistance_%s' % k, v, 'Ω/□', 'PDK_MAGIC', basis='derived', derivation='magic extract `resist` (mΩ/□ ÷ 1000), first style', conditions='as implanted by the PDK\'s %s' % k) for k, v in sorted(diff.items())]},
        {'name': 'silicon-dioxide-thermal', 'existing': False, 'display': 'Silicon dioxide (thermal / deposited SiO2)', 'elements': ['Si', 'O'], 'role': 'gate dielectric (1.8 V core and the thick `hvi` oxide), field isolation, inter-layer dielectric between the metals',
         'asserted_by_pdk': True, 'stages': ['sky130-active', 'sky130-gate-stack', 'sky130-metal-stack'],
         'properties': [_p('relative_permittivity', 3.9, '', 'SZE07'), _p('bandgap', 9.0, 'eV', 'SZE07'), _p('density', 2.27, 'g/cm³', 'SZE07', conditions='thermal oxide'), _p('breakdown_field', 1e7, 'V/cm', 'SZE07', note='≈ 10 MV/cm'),
                        _p('resistivity', None, 'Ω·cm', 'SZE07', vmin=1e14, vmax=1e16), _p('gate_oxide_thickness_toxe_nfet_01v8', 4.148, 'nm', 'LOD4C', basis='derived', derivation='toxe in the tt model card as run in lod-4c/3b (an electrical thickness)')]
                       + ([_p('inter_layer_dielectric_thickness_under_met1', die['implied_thickness_um_if_sio2'], 'µm', 'PDK_TLEF', basis='derived', derivation='ε0·εr(3.9) / CPERSQDIST(met1) = %.3f µm; magic height of met1 bottom = %s µm' % (die['implied_thickness_um_if_sio2'], die.get('magic_met1_bottom_um')), note=die['reading'])] if die else [])},
        {'name': 'silicon-nitride', 'existing': False, 'display': 'Silicon nitride (Si3N4)', 'elements': ['Si', 'N'], 'role': 'the nitride the `npc` cut opens under contacts, pad/stop layers in isolation, the `nsm` seal over the die',
         'asserted_by_pdk': True, 'stages': ['sky130-active', 'sky130-contacts-li', 'sky130-passivation'],
         'properties': [_p('relative_permittivity', 7.5, '', 'SZE07'), _p('bandgap', 5.0, 'eV', 'SZE07'), _p('density', 3.1, 'g/cm³', 'SZE07'), _p('breakdown_field', 1e7, 'V/cm', 'SZE07'), _p('resistivity', 1e14, 'Ω·cm', 'SZE07', note='≈, deposited films vary')]},
        {'name': 'polysilicon-doped', 'existing': False, 'display': 'Polysilicon (doped gate poly)', 'elements': ['Si'], 'role': 'the gate electrode (`poly`), and the resistor flavours by implant (`rpm`, high-ρ poly)',
         'asserted_by_pdk': True, 'stages': ['sky130-gate-stack'],
         'properties': ([_p('sheet_resistance', poly['rpersq_ohm'], 'Ω/□', 'PDK_MAGIC', basis='derived', derivation='magic `resist (allpolynonres)/active` %.0f mΩ/□' % (poly['rpersq_ohm'] * 1000)),
                         _p('thickness', poly['thickness_um'], 'µm', 'PDK_MAGIC', basis='derived', derivation='magic `height allpoly` thickness'),
                         _p('resistivity', poly['resistivity_ohm_cm'], 'Ω·cm', 'PDK_MAGIC', basis='derived', derivation='sheet resistance × thickness = %.1f Ω/□ × %.2f µm' % (poly['rpersq_ohm'], poly['thickness_um']), note='a heavily doped n+ poly figure (textbook 5×10⁻⁴–10⁻³ Ω·cm)'),
                         _p('resistor_flavours_sheet_resistance', None, 'Ω/□', 'PDK_MAGIC', basis='derived', derivation=json.dumps(poly.get('resistor_flavours_ohm_per_sq', {})), note='the implant-defined poly resistors (xhrpoly, uhrpoly, mrp1)')] if poly else [])},
        {'name': 'dopant-boron', 'existing': False, 'display': 'Boron (p-type dopant)', 'elements': ['B'], 'role': 'the acceptor: p-wells / substrate tuning, p+ source/drain (`psdm`), the hvtp Vt implant',
         'asserted_by_pdk': False, 'inference': 'the PDK names implant LAYERS (psdm "P+ source/drain implant"), not the species; boron is the one practical acceptor in Si CMOS [PDG00]', 'stages': ['sky130-wells', 'sky130-gate-stack', 'sky130-source-drain'],
         'properties': [_p('ionization_energy_acceptor', 0.045, 'eV', 'SZE07', conditions='above the valence band, in Si'), _p('role', None, '', 'PDG00', basis='inference', note='acceptor (p-type)')]
                       + [_p('sheet_resistance_%s' % k, v, 'Ω/□', 'PDK_MAGIC', basis='derived', derivation='magic `resist`, the p-type layers', conditions='the PDK\'s %s' % k) for k, v in sorted(diff.items()) if k.startswith(('pdiff', 'psd', 'mvpdiff', 'pwell'))]},
        {'name': 'dopant-phosphorus', 'existing': False, 'display': 'Phosphorus (n-type dopant)', 'elements': ['P'], 'role': 'a donor: n-well and deep n-well candidates, n+ source/drain candidate (with arsenic)',
         'asserted_by_pdk': False, 'inference': 'the PDK draws nwell / dnwell / nsdm; whether P or As (or both, by depth) forms each is the recipe\'s — not published', 'stages': ['sky130-wells', 'sky130-source-drain'],
         'properties': [_p('ionization_energy_donor', 0.045, 'eV', 'SZE07', conditions='below the conduction band, in Si'), _p('role', None, '', 'PDG00', basis='inference', note='donor (n-type); the deeper-diffusing n dopant — wells')]
                       + [_p('sheet_resistance_%s' % k, v, 'Ω/□', 'PDK_MAGIC', basis='derived', derivation='magic `resist`, the n-type layers', conditions='the PDK\'s %s' % k) for k, v in sorted(diff.items()) if k.startswith(('nwell', 'dnwell'))]},
        {'name': 'dopant-arsenic', 'existing': False, 'display': 'Arsenic (n-type dopant)', 'elements': ['As'], 'role': 'a donor: the shallow n+ source/drain candidate (`nsdm`), the lvtn Vt implant candidate',
         'asserted_by_pdk': False, 'inference': 'species not named by the PDK; As is the generation\'s shallow-junction n dopant [PDG00]', 'stages': ['sky130-gate-stack', 'sky130-source-drain'],
         'properties': [_p('ionization_energy_donor', 0.054, 'eV', 'SZE07', conditions='below the conduction band, in Si'), _p('role', None, '', 'PDG00', basis='inference', note='donor (n-type); shallow junctions')]
                       + [_p('sheet_resistance_%s' % k, v, 'Ω/□', 'PDK_MAGIC', basis='derived', derivation='magic `resist`, the n+ layers', conditions='the PDK\'s %s' % k) for k, v in sorted(diff.items()) if k.startswith(('ndiff', 'nsd', 'mvndiff'))]},
        {'name': 'aluminium', 'existing': False, 'display': 'Aluminium (interconnect candidate)', 'elements': ['Al'], 'role': 'CANDIDATE interconnect metal for met1–met5 and the pads — the PDK does not name the metal',
         'asserted_by_pdk': False, 'inference': 'Al with Ti/TiN barrier and cap is this generation\'s metal [PDG00]; EVIDENCE from the PDK: ' + metal_evidence, 'stages': ['sky130-metal-stack', 'sky130-passivation'],
         'properties': [_p('resistivity', al_bulk, 'µΩ·cm', 'CRC', conditions='20 °C, bulk'), _p('density', 2.70, 'g/cm³', 'CRC'), _p('melting_point', 660.3, '°C', 'CRC')]
                       + [_p('effective_resistivity_%s' % k, m['effective_resistivity_uohm_cm'], 'µΩ·cm', 'PDK_TLEF', basis='derived', derivation='RPERSQ %.4f Ω/□ × THICKNESS %.2f µm (magic height thickness %s µm)' % (m['rpersq_ohm'], m['thickness_um'], m['magic_thickness_um']),
                             note='the layer\'s figure whatever the metal is; %.2f× bulk Al' % (m['effective_resistivity_uohm_cm'] / al_bulk)) for k, m in sorted(met.items())]},
        {'name': 'copper', 'existing': False, 'display': 'Copper (interconnect candidate)', 'elements': ['Cu'], 'role': 'CANDIDATE interconnect metal — the PDK does not name the metal',
         'asserted_by_pdk': False, 'inference': 'kept as a candidate because the PDK is silent; EVIDENCE from the PDK weighs against it: ' + metal_evidence, 'stages': ['sky130-metal-stack'],
         'properties': [_p('resistivity', cu_bulk, 'µΩ·cm', 'CRC', conditions='20 °C, bulk'), _p('density', 8.96, 'g/cm³', 'CRC'), _p('melting_point', 1084.6, '°C', 'CRC')]
                       + [_p('effective_resistivity_%s' % k, m['effective_resistivity_uohm_cm'], 'µΩ·cm', 'PDK_TLEF', basis='derived', derivation='RPERSQ × THICKNESS (see the aluminium row)', note='%.2f× bulk Cu' % (m['effective_resistivity_uohm_cm'] / cu_bulk)) for k, m in sorted(met.items())]},
        {'name': 'tungsten', 'existing': False, 'display': 'Tungsten (plug candidate)', 'elements': ['W'], 'role': 'CANDIDATE contact / via plug metal (licon, mcon, via…via4) — the PDK names the cuts and their resistance, not the fill',
         'asserted_by_pdk': False, 'inference': 'CVD-W plugs are the generation\'s fill [PDG00]', 'stages': ['sky130-contacts-li', 'sky130-metal-stack'],
         'properties': [_p('resistivity', w_bulk, 'µΩ·cm', 'CRC', conditions='20 °C, bulk'), _p('density', 19.25, 'g/cm³', 'CRC'), _p('melting_point', 3422, '°C', 'CRC')]
                       + [_p('resistance_per_cut_%s' % k, v, 'Ω', 'PDK_TLEF', basis='derived', derivation='LAYER %s RESISTANCE (per cut) in the technology LEF' % k, note='the PDK\'s own per-cut figure, fill unnamed') for k, v in sorted(vias.items())]},
        {'name': 'titanium-nitride', 'existing': False, 'display': 'Titanium nitride (local-interconnect / barrier candidate)', 'elements': ['Ti', 'N'], 'role': 'CANDIDATE for the `li1` local interconnect and the metals\' barrier/cap layers',
         'asserted_by_pdk': False, 'inference': 'TiN-class films are the generation\'s local interconnect and barrier [PDG00]; EVIDENCE: li1\'s effective resistivity %s µΩ·cm is a refractory-nitride film figure (bulk TiN ~20 µΩ·cm, films 50–200), far from any Al / Cu / W film' % li.get('effective_resistivity_uohm_cm', '?'),
         'stages': ['sky130-contacts-li'],
         'properties': ([_p('effective_resistivity_li1', li['effective_resistivity_uohm_cm'], 'µΩ·cm', 'PDK_TLEF', basis='derived', derivation='RPERSQ %.1f Ω/□ × THICKNESS %.2f µm' % (li['rpersq_ohm'], li['thickness_um']), note='the layer\'s figure whatever the film is')] if li else [])
                       + [_p('bulk_resistivity', None, 'µΩ·cm', '', basis='not-modelled', note='film-dependent (stoichiometry, density); no single literature value adopted')]},
    ]
    return rows


#: how the stages' NAMED strings (lod-4b) resolve to rows — every key is a name a stage carries (before its parenthesis / dash)
_NAME_TO_ROWS = {
    'Si': ['silicon'], 'P and/or As dopant': ['dopant-phosphorus', 'dopant-arsenic'], 'SiO2': ['silicon-dioxide-thermal'], 'Si3N4': ['silicon-nitride'],
    'SiO2 gate dielectric': ['silicon-dioxide-thermal'], 'poly-Si': ['polysilicon-doped'], 'B / As Vt-adjust implants': ['dopant-boron', 'dopant-arsenic'],
    'As / P': ['dopant-arsenic', 'dopant-phosphorus'], 'B': ['dopant-boron'], 'contact plug metal': ['tungsten'], 'local-interconnect metal': ['titanium-nitride'],
    'Al': ['aluminium', 'copper'], 'inter-metal dielectric SiO2': ['silicon-dioxide-thermal'], 'via plug metal': ['tungsten'], 'Si3N4 seal': ['silicon-nitride'],
}


def resolve_named(txt):
    """A stage's named-material string → its row names, or the NOT_MODELLED reason ('' when neither — a selftest failure)."""
    key = txt.split(' (')[0].split(' —')[0]
    if key in _NAME_TO_ROWS:
        return _NAME_TO_ROWS[key]
    for k, why in NOT_MODELLED.items():
        if k.split(' (')[0] == key or key in k:
            return why
    return ''


def run():
    from computelod.custom.repro import start_meter, stop_meter, record
    from computelod.custom.lod4_steps import SKY130_STAGES
    start_meter('computelod.custom.lod4_materials')
    root = pdk_root()
    tlef = os.path.join(root, SOURCES['PDK_TLEF']['file']); mag = os.path.join(root, SOURCES['PDK_MAGIC']['file'])
    for p in (tlef, mag):
        if not os.path.exists(p):
            raise SystemExit('PDK file absent: %s (polari-eda-tools/fetch-pdk.sh, or POLARI_PDK_ROOT)' % p)
    T = parse_tlef(tlef); M = parse_magic_tech(mag)
    D = derived_numbers(T, M)
    mats = materials(D)
    by_stage = {}
    for m in mats:
        for s in m['stages']:
            by_stage.setdefault(s, []).append(m['name'])
    named = {}
    for name, _disp, _prior, _layers, materials_, _procs, _desc in SKY130_STAGES:
        for txt in materials_:
            named[txt] = {'stage': name, 'resolves_to': resolve_named(txt)}
    unresolved = [k for k, v in named.items() if not v['resolves_to']]
    counts = {'cited': 0, 'derived': 0, 'inference': 0, 'not-modelled': 0}
    for m in mats:
        for p in m['properties']:
            counts[p['basis']] = counts.get(p['basis'], 0) + 1
    rep = {'read_on': '2026-09-27', 'sources': dict(SOURCES), 'pdk_files': {'tlef': {'file': SOURCES['PDK_TLEF']['file'], 'sha256': _sha(tlef), 'bytes': os.path.getsize(tlef)}, 'magic_tech': {'file': SOURCES['PDK_MAGIC']['file'], 'sha256': _sha(mag), 'bytes': os.path.getsize(mag)}},
           'derived': D, 'materials': mats, 'stage_materials': by_stage, 'named_strings': named, 'unresolved_names': unresolved, 'not_modelled': NOT_MODELLED,
           'counts': {'materials': len(mats), 'new_identities': sum(1 for m in mats if not m['existing']), 'properties': counts, 'asserted_by_pdk': sum(1 for m in mats if m['asserted_by_pdk']), 'candidates': sum(1 for m in mats if not m['asserted_by_pdk'])},
           'reading': 'every material a SKY130 stage names is a row (or an explicit not-modelled entry); every number on a row is cited (Sze & Ng, CRC) or derived here from two PDK files by the formula in its `derivation`; '
                      'what the PDK does not say (WHICH metal, WHICH dopant species, the plug and barrier films) stays a CANDIDATE with the PDK\'s own numbers as evidence — never asserted'}
    try:
        from computelod.custom.lod3_layout import pdk_version
        rep['pdk_files']['ciel_version'] = pdk_version()
    except Exception:
        pass
    os.makedirs(OUT, exist_ok=True)
    rep['reproduction'] = record('computelod.custom.lod4_materials', cost=stop_meter('computelod.custom.lod4_materials'),
                                 inputs=[{'label': 'sc_hd technology LEF (nominal)', 'file': SOURCES['PDK_TLEF']['file'], 'sha256': rep['pdk_files']['tlef']['sha256'], 'url': 'https://github.com/google/skywater-pdk', 'note': 'PDK content: never committed'},
                                         {'label': 'magic sky130A.tech', 'file': SOURCES['PDK_MAGIC']['file'], 'sha256': rep['pdk_files']['magic_tech']['sha256'], 'url': 'https://github.com/google/skywater-pdk', 'note': 'PDK content: never committed'},
                                         {'label': 'Sze & Ng 2007 / CRC 97th / Plummer 2000', 'url': 'urn:isbn:978-0-471-14323-9 (Sze & Ng); urn:isbn:978-1-4987-5428-6 (CRC 97th); urn:isbn:0-13-085037-3 (Plummer)', 'note': 'literature constants typed into materials(); each carries its source key'}],
                                 knobs={'eps_r_sio2_for_the_thickness_derivation': 3.9, 'bulk_resistivities_uohm_cm': {'Al': 2.65, 'Cu': 1.68, 'W': 5.28}, 'magic_extract_style': 'first'},
                                 conditions={'reading': 'a parse of two PDK text files + literature constants; the derivations are the formulas in each property row'},
                                 deterministic='yes: the same two files (sha256) give the same numbers; no randomness, no engines')
    json.dump(rep, open(os.path.join(OUT, 'materials_report.json'), 'w'), indent=1, ensure_ascii=False)
    return rep


def report():
    p = os.path.join(OUT, 'materials_report.json')
    return json.load(open(p)) if os.path.exists(p) else None


def material_rows(rep=None):
    """MaterialsScienceMaterial rows for the NEW identities (silicon already exists in the basis)."""
    rep = rep or report()
    if not rep:
        return []
    rows = []
    for m in rep['materials']:   # material_kind 'pure': an element or a stoichiometric compound — one substance
        if m['existing']:
            continue
        rows.append({'name': m['name'], 'display_name': m['display'], 'description': m['role'] + ('' if m['asserted_by_pdk'] else ' — a CANDIDATE: %s' % m['inference']),
                     'material_kind': 'pure', 'category': 'elemental', 'tags_json': json.dumps(TAGS + (['candidate'] if not m['asserted_by_pdk'] else []) + ['stage:' + s for s in m['stages']]),
                     'element_symbols_json': json.dumps(m['elements']), 'provenance_id': PROV,
                     'notes': 'lod-4d: properties (cited / derived from the PDK) on MaterialScaleDefinition %s@L0-sky130; stages: %s' % (m['name'], ', '.join(m['stages']))})
    return rows


def scale_rows(rep=None):
    """One MaterialScaleDefinition at scale 0 per material — the property rows, each with its source and basis."""
    rep = rep or report()
    if not rep:
        return []
    rows = []
    for m in rep['materials']:
        props = m['properties']
        rows.append({'name': '%s@L0-sky130' % m['name'], 'material_name': m['name'], 'scale_level': 0, 'scale_category': 'experimental',
                     'definition_class': 'ComputeLODMaterialsReport', 'definition_ref': 'computelod/initialData/lod4/materials_report.json#%s' % m['name'],
                     'status': 'defined' if any(p['basis'] in ('cited', 'derived') for p in props) else 'partial', 'derivation_method': 'literature',
                     'parameters_json': json.dumps({'properties': props, 'sources': {k: SOURCES[k]['citation'] for k in sorted({p['source'] for p in props if p.get('source')})}, 'asserted_by_pdk': m['asserted_by_pdk'], 'inference': m.get('inference', ''),
                                                    'pdk_files_sha256': {k: v['sha256'] for k, v in rep['pdk_files'].items() if isinstance(v, dict)}}, ensure_ascii=False),
                     'provenance_id': PROV, 'notes': 'lod-4d: %d properties (%s); derive-or-cite — every value names its source or its formula; PDK-derived values recompute from the two files by sha256' % (
                         len(props), ', '.join('%d %s' % (sum(1 for p in props if p['basis'] == b), b) for b in ('cited', 'derived', 'inference', 'not-modelled') if any(p['basis'] == b for p in props)))})
    return rows


def target_ref(rep=None):
    """What lod-4's `fabrication → materials` mapping now points at: rows, not names."""
    rep = rep or report()
    if not rep:
        return ''
    asserted = [m['name'] for m in rep['materials'] if m['asserted_by_pdk']]
    cands = [m['name'] for m in rep['materials'] if not m['asserted_by_pdk']]
    return 'MaterialsScienceMaterial rows %s (asserted by the PDK\'s layers) + candidates %s (the PDK is silent; evidence on the rows); each with MaterialScaleDefinition <name>@L0-sky130; substrate grade = sifet SiliconGrade eg-si via RefinementRoute siemens-route' % (
        ', '.join(asserted), ', '.join(cands))


if __name__ == '__main__':
    r = run() if len(sys.argv) > 1 and sys.argv[1] == 'run' else report()
    print(json.dumps({'counts': r['counts'], 'unresolved_names': r['unresolved_names'], 'derived': r['derived']} if r else 'no report yet: python3 -m computelod.custom.lod4_materials run', indent=1, ensure_ascii=False))
