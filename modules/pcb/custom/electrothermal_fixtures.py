"""
@module pcb.custom.electrothermal_fixtures

tmp-3: the boards the self-heating loop is checked on (pcb_electrothermal_selftest) and recorded with (econ-core's libngspice).

  rectifier        the kicad-demos rectifier as ingested, with D1's datasheet Rth j-a CITED: Vishay 1N4148, Document Number 81857, Rev. 1.6,
                   07-Nov-2024, Thermal Characteristics: R_thJA 350 K/W (l = 4 mm, T_L = constant), T_j 175 C. (The demo's own diode model is the
                   generic `.model 1N4148 D` - ngspice's default diode - so the electrical side is generic; only the thermal number is the part's.)
  bjt_rows(re)     a SYNTHETIC transistor stage written as rows: 10 V on the collector, the base held by an ideal source, the emitter to ground
                   through re ohms (0 = straight to ground); the transistor is ngspice's DEFAULT NPN (.model QGEN NPN() - IS 1e-16 A, BF 100,
                   XTI 3, EG 1.11 eV: the ngspice manual's defaults, no vendor's model) and its Rth j-a 200 K/W is a SYNTHETIC number. The base
                   voltage gives about 10 mA at 25 C either way, so the two differ only in the emitter resistor - the textbook case: a transistor
                   held at a fixed V_BE runs away (its current doubles every few kelvin), the emitter resistor stabilises it.
"""
VISHAY_1N4148 = {'document': 'Vishay 1N4148 Small Signal Fast Switching Diode, Document Number 81857', 'revision': 'Rev. 1.6, 07-Nov-2024',
                 'page_table': 'Thermal Characteristics (Tamb = 25 C), p. 1: R_thJA 350 K/W (l = 4 mm, T_L = constant); T_j 175 C',
                 'url': 'https://www.vishay.com/docs/81857/1n4148.pdf', 'rth_ja_k_w': 350.0, 'tj_max_c': 175.0}
RTH_SYNTHETIC = 200.0
VCC = 10.0
VBE_10MA = 0.83     # ngspice's default NPN (IS 1e-16 A) at 25 C: V_T ln(10 mA / IS) = 25.69 mV x 32.24 = 0.828 V


def _sym(ref, value, **kw):
    base = {'ref': ref, 'unit': 1, 'power': 'no', 'exclude_from_sim': 'no', 'dnp': 'no', 'sim_pins': '', 'sim_device': '', 'sim_library': '',
            'sim_name': '', 'sim_params': '', 'sim_type': '', 'value': value, 'lib_id': 'synthetic:%s' % ref[:1]}
    base.update(kw)
    return base


def bjt_rows(re_ohm):
    vb = VBE_10MA + 0.010 * re_ohm
    syms = [_sym('V1', '%g' % VCC, sim_device='V', sim_type='DC', sim_params='dc=%g' % VCC, sim_pins='1=+ 2=-'),
            _sym('V2', '%g' % vb, sim_device='V', sim_type='DC', sim_params='dc=%g' % vb, sim_pins='1=+ 2=-'),
            _sym('Q1', 'QGEN', sim_library='bjt.mod', sim_name='QGEN', sim_pins='1=1 2=2 3=3')]
    ends = [('V1', '1', 'VCC'), ('V1', '2', 'GND'), ('V2', '1', 'BASE'), ('V2', '2', 'GND'), ('Q1', '1', 'VCC'), ('Q1', '2', 'BASE')]
    if re_ohm:
        syms.append(_sym('R1', '%g' % re_ohm, sim_device='R', sim_pins='1=1 2=2'))
        ends += [('Q1', '3', 'EMIT'), ('R1', '1', 'EMIT'), ('R1', '2', 'GND')]
    else:
        ends.append(('Q1', '3', 'GND'))
    return {'SchematicSymbol': syms, 'NetEndpoint': [{'ref': r, 'pin': p, 'net': n} for r, p, n in ends],
            'KiCadArtifact': [{'path': 'bjt.mod', 'kind': 'model', 'content': '* ngspice\'s default NPN (no parameters given)\n.model QGEN NPN()\n'},
                              {'path': 'stage.kicad_sch', 'kind': 'schematic', 'content': '(kicad_sch (text ".tran 1u 20u"))'}]}


#: tmp-3's independent check of the Foster -> Cauer step: a SYNTHETIC 3-stage Foster network, its Cauer ladder run as an RC circuit by ngspice
#: (the thermal-electrical analogy: K/W = ohm, J/K = F, W = A, K = V), a 1 A step into the junction node; V(junction) must be Zth(t)
CAUER_CHECK = [[0.3, 1e-4], [1.2, 0.02], [4.0, 3.0]]
CAUER_TIMES = (1e-4, 1e-3, 1e-2, 0.1, 1.0, 10.0)


def cauer_deck(ladder):
    lines = ['.title Cauer ladder of a 3-stage Foster network (tmp-3 check)', '.tran 0.1m 15 0 1m', '', 'I1 0 n1 PWL(0 0 1e-9 1)']
    for k, (r, c) in enumerate(ladder):
        nxt = 'n%d' % (k + 2) if k + 1 < len(ladder) else '0'
        lines += ['C%d n%d 0 %.12g' % (k + 1, k + 1, c), 'R%d n%d %s %.12g' % (k + 1, k + 1, nxt, r)]
    return '\n'.join(lines + ['.end']) + '\n'
