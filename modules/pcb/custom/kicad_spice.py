"""
@module pcb.custom.kicad_spice

kxc-3 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): A SPICE DECK FROM OUR OWN ROWS. Polari is the source of truth (his ruling 2026-10-30): the deck is built
from the ingested rows - SchematicSymbol (with its Sim.* fields), NetEndpoint (our own nets, kxc-2) and the KiCadArtifact files (the schematic's text
directives, the model libraries) - never copied from KiCad's export, which is only the cross-check.

  build_deck(rows)   → {'deck', 'elements': {ref: {'kind', 'nodes', 'value'}}, 'includes', 'directives', 'skipped', 'problems'}
  parse_deck(text)   → the same 'elements' shape from any SPICE deck (KiCad's export, ours) - for comparing

tmp-1 / tmp-2 (TEMPERATURE_PLAN): build_deck(rows, temp_c=None, part_temps=None, coefficients=None)
  temp_c        the whole board's (background) temperature: one `.temp` line - every model's own temperature terms act (ngspice's default is
                27 C, its TNOM: the temperature model parameters are given at); a `.temp` / `.options temp=` the schematic carries is then left out
  coefficients  {ref: (tc1 1/K, tc2 1/K2, origin)} - an R, C or L gets tc1= tc2= (a person's figure wins over the symbol's Sim.Params tc1/tc2);
                without one an ideal R, C or L does not change with temperature at all (ngspice's tc1 = tc2 = 0)
  part_temps    {ref: C} - the part's OWN temperature as an instance `temp=` where ngspice takes one (INSTANCE_TEMP: probed on libngspice, KiCad
                10.0.6, econ-core 2026-10-31); elsewhere the part stays at the board's temperature and 'temperature' says why

KiCad's simulation model, as its files carry it (KiCad 7+): Sim.Device (R C L V I D NPN PNP NMOS PMOS SUBCKT SPICE ...; absent = inferred from the
reference letter), Sim.Type (DC SIN PULSE PWL EXP AM SFFM ... for sources), Sim.Params (key=value pairs, or for SPICE: type= model= lib=), Sim.Pins
(symbol pin = model pin; the deck lists the nodes in MODEL pin order: 1 2 ..., + -, or a subcircuit's ports as its .subckt line orders them),
Sim.Library + Sim.Name (a model or subcircuit in a library file). Node names = our net names with KiCad's substitutions ('(' ')' ' ' → '_').
Values: SI prefixes as KiCad reads them - 'M' on a passive is MEGA (ngspice reads M as milli), so it is written 'Meg'.
"""
import re

from pcb.custom import sexpr as S

PASSIVE = {'R': 'R', 'C': 'C', 'L': 'L'}
SOURCES = ('V', 'I')
#: Sim.Type → the SPICE source function and the Sim.Params keys in its argument order (KiCad's SIM_MODEL_SOURCE names)
SOURCE_ARGS = {'SIN': ('SIN', ('dc', 'ampl', 'f', 'td', 'theta', 'phase')), 'PULSE': ('PULSE', ('y1', 'y2', 'td', 'tr', 'tf', 'tw', 'per', 'np')),
               'EXP': ('EXP', ('y1', 'y2', 'td1', 'tau1', 'td2', 'tau2')), 'SFFM': ('SFFM', ('dc', 'ampl', 'fc', 'mdi', 'fs', 'phasec', 'phases')),
               'AM': ('AM', ('vo', 'vmo', 'vma', 'fm', 'fc', 'td', 'phasem', 'phasec'))}


#: tmp-2: the instance `temp=` ngspice accepts, by element letter - probed 2026-10-31 on econ-core's libngspice (KiCad 10.0.6): R C L D Q J take it,
#: a MOSFET only for levels 1 2 3 6 and VDMOS; BSIM (level 8/49, 14/54) refuses the line ("circuit not parsed") and a subcircuit (X) line with
#: temp= CRASHES the library ("ngspice.dll cannot recover"), so neither is ever written
INSTANCE_TEMP = ('R', 'C', 'L', 'D', 'Q', 'J')
MOS_INSTANCE_TEMP_LEVELS = (1, 2, 3, 6)
TEMP_DIRECTIVE = re.compile(r'^\.(temp\b|options\b.*\btemp\s*=)', re.I)


def model_card(lib_text, name):
    """(type, {param: value}) of `.model <name> <type> (...)` in a library text (continuation lines joined), else (None, {})."""
    lines, cur = [], ''
    for line in (lib_text or '').splitlines():
        if line.startswith('+'):
            cur += ' ' + line[1:]
        else:
            lines.append(cur)
            cur = line
    lines.append(cur)
    for line in lines:
        parts = line.replace('(', ' ').replace(')', ' ').split()
        if len(parts) > 2 and parts[0].lower() == '.model' and parts[1].lower() == name.lower():
            return parts[2].upper(), {k.lower(): v for k, v in re.findall(r'(\w+)\s*=\s*(\S+)', ' '.join(parts[3:]))}
    return None, {}


def instance_temp_refusal(kind, lib_text, model):
    """'' when ngspice takes an instance temp= on this element, else why not (INSTANCE_TEMP)."""
    if kind == 'M':
        mtype, params = model_card(lib_text, model)
        if mtype == 'VDMOS':
            return ''
        if mtype is None:
            return 'MOSFET model %s not found in its library, so its level (which decides whether ngspice takes temp=) is unknown' % model
        try:
            level = int(float(params.get('level', 1)))
        except ValueError:
            level = -1
        return '' if level in MOS_INSTANCE_TEMP_LEVELS else ('MOSFET model %s is level %s: ngspice takes a per-part temp= only for levels 1, 2, 3, 6 '
                                                              'and VDMOS (BSIM refuses it)' % (model, params.get('level', '?')))
    if kind in INSTANCE_TEMP:
        return ''
    if kind == 'X':
        return 'a subcircuit takes no per-part temperature in ngspice (temp= on an X line crashes the library): it follows the board\'s'
    return 'ngspice takes no temperature on a %s element' % kind


def node_name(net):
    return 'GND' if net in ('GND', '0') else re.sub(r'[()\s]', '_', net)


def spice_value(v):
    """KiCad's value text → SPICE: 1M → 1Meg (mega, not milli), 4k7 → 4.7k, units after the prefix dropped (100nF → 100n)."""
    v = (v or '').strip()
    m = re.match(r'^([0-9]*\.?[0-9]+)([pnuµmkKMGT]?)([0-9]*)([A-Za-zΩ]*)$', v)
    if not m:
        return v
    num, pre, frac, _unit = m.groups()
    if frac and pre:   # 4k7
        num = '%s.%s' % (num, frac)
    pre = {'M': 'Meg', 'µ': 'u', 'K': 'k'}.get(pre, pre)
    return num + pre


def _params(text):
    """Sim.Params → {key: value} (key=value pairs; a value may be "quoted")."""
    return {k.lower(): (a if a else b) for k, a, b in re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|(\S+))', text or '')}


def _pin_map(text):
    """Sim.Pins "2=1 1=2" → {symbol pin: model pin}."""
    return dict(re.findall(r'(\S+)=(\S+)', text or ''))


def _subckt_ports(lib_text, name):
    for line in (lib_text or '').splitlines():
        parts = line.split()
        if len(parts) > 2 and parts[0].lower() == '.subckt' and parts[1].lower() == name.lower():
            return [p for p in parts[2:] if '=' not in p and p.lower() != 'params:']
    return None


def _model_kind(lib_text, name):
    for line in (lib_text or '').splitlines():
        parts = line.replace('(', ' ').split()
        if len(parts) > 2 and parts[0].lower() == '.model' and parts[1].lower() == name.lower():
            return parts[2].upper()
    return None


def _directives(rows):
    """The schematic's text items that are simulation directives ('.tran ...', '.ac ...', '.include ...', '.control ... .endc'), in file order."""
    out = []
    for a in rows.get('KiCadArtifact', []):
        if a['kind'] != 'schematic' or not a['content']:
            continue
        for t in S.find(S.parse(a['content']), 'text'):
            body = str(t[1]) if len(t) > 1 else ''
            if body.lstrip().startswith('.'):
                out.append(body.strip())
    return out


def build_deck(rows, title='Polari deck (kxc-3, from the ingested rows)', temp_c=None, part_temps=None, coefficients=None):
    part_temps, coefficients = part_temps or {}, coefficients or {}
    applied, refused, tcs = {}, {}, {}
    arts = {a['path']: a['content'] for a in rows.get('KiCadArtifact', [])}
    nodes = {}
    for e in rows.get('NetEndpoint', []):
        nodes[(e['ref'], e['pin'])] = node_name(e['net'])
    elements, includes, skipped, problems = {}, [], [], []
    for s in sorted(rows.get('SchematicSymbol', []), key=lambda s: (s['ref'], s['unit'])):
        if s['power'] == 'yes' or s['ref'] in elements:
            continue
        if s['exclude_from_sim'] == 'yes' or s['dnp'] == 'yes':
            skipped.append('%s: excluded from simulation' % s['ref'])
            continue
        mine = {pin: n for (ref, pin), n in nodes.items() if ref == s['ref']}
        pins = _pin_map(s['sim_pins']) or {p: p for p in mine}
        device, letter = (s['sim_device'] or '').upper(), s['ref'][:1].upper()
        lib = arts.get(s['sim_library'], '') if s['sim_library'] else ''
        if s['sim_library'] and s['sim_library'] not in arts:
            problems.append('%s: model library %s is not among the project files' % (s['ref'], s['sim_library']))
        if s['sim_library'] and s['sim_library'] not in includes:
            includes.append(s['sim_library'])
        ports = _subckt_ports(lib, s['sim_name']) if s['sim_name'] else None
        order = ports if ports else sorted(set(pins.values()), key=lambda m: ({'+': 0, '-': 1}.get(m, 2), int(m) if m.isdigit() else 99, m))
        by_model = {m: mine.get(p, '') for p, m in pins.items()}
        node_list = [by_model.get(m, '') for m in order]
        if '' in node_list:
            problems.append('%s: model pin(s) %s reach no net' % (s['ref'], [m for m in order if not by_model.get(m)]))
        p = _params(s['sim_params'])
        if device == 'SPICE':   # raw SPICE: type= model= lib=
            kind, value = p.get('type', letter).upper(), p.get('model', '')
        elif ports is not None:
            kind, value = 'X', s['sim_name']
        elif s['sim_name']:
            mk = _model_kind(lib, s['sim_name'])
            kind, value = {'D': 'D', 'NPN': 'Q', 'PNP': 'Q', 'NMOS': 'M', 'PMOS': 'M', 'NJF': 'J', 'PJF': 'J'}.get(mk or '', letter), s['sim_name']
        elif device in SOURCES or (not device and letter in SOURCES):
            kind = device or letter
            st = (s['sim_type'] or 'DC').upper()
            raw_val = '' if s['value'].startswith('${') else s['value']
            if st == 'DC':
                value = 'DC %s' % spice_value(p.get('dc') or raw_val or '0')
            elif st in SOURCE_ARGS:
                fn, keys = SOURCE_ARGS[st]
                args = [spice_value(p[k]) for k in keys if k in p]
                value = '%s(%s)' % (fn, ' '.join(args))
            elif st == 'PWL':
                value = 'PWL(%s)' % ' '.join(spice_value(x) for x in re.findall(r'\S+', p.get('t', '') + ' ' + p.get('y', '')))
            else:
                value = ''
                problems.append('%s: source type %s not rendered yet' % (s['ref'], st))
            if p.get('ac'):
                value += ' AC %s' % spice_value(p['ac'])
        elif (device or letter) in PASSIVE:
            kind, value = PASSIVE[device or letter], spice_value(p.get(({'R': 'r', 'C': 'c', 'L': 'l'})[device or letter]) or s['value'])
            tc = coefficients.get(s['ref'])
            if tc is None and ('tc1' in p or 'tc2' in p):
                tc = (p.get('tc1', '0'), p.get('tc2', '0'), 'the symbol\'s Sim.Params')
            if tc is not None:
                value += ' tc1=%s tc2=%s' % (tc[0], tc[1])
                tcs[s['ref']] = tc
        else:
            skipped.append('%s (%s): no simulation model (no Sim.* fields and the reference letter names no primitive)' % (s['ref'], s['lib_id']))
            continue
        name = s['ref'] if s['ref'][:1].upper() == kind[:1] else kind[:1] + s['ref']
        if s['ref'] in part_temps:
            why = instance_temp_refusal(kind[:1], lib, value)
            if why:
                refused[s['ref']] = why
            else:
                value += ' temp=%g' % float(part_temps[s['ref']])
                applied[s['ref']] = float(part_temps[s['ref']])
        elements[name] = {'kind': kind[:1], 'nodes': node_list, 'value': value, 'ref': s['ref'], 'model': value.split()[0] if kind[:1] in 'DQMJX' else '',
                          'library': s['sim_library'] or ''}
    directives = _directives(rows)
    dropped = [d for d in directives if TEMP_DIRECTIVE.match(d)] if temp_c is not None else []
    directives = [d for d in directives if d not in dropped]
    head = ['.temp %g' % float(temp_c)] if temp_c is not None else []
    lines = ['.title %s' % title] + ['.include "%s"' % i for i in includes] + head + directives + ['']
    lines += ['%s %s %s' % (n, ' '.join(e['nodes']), e['value']) for n, e in sorted(elements.items())]
    lines.append('.end')
    for ref in sorted(set(part_temps) - set(applied) - set(refused)):
        refused[ref] = 'not in the deck (no simulation model, or excluded)'
    temperature = {'temp_c': float(temp_c) if temp_c is not None else None, 'part_temps': applied, 'refused': refused, 'coefficients': tcs,
                   'schematic_temp_dropped': dropped}
    return {'deck': '\n'.join(lines) + '\n', 'elements': elements, 'includes': includes, 'directives': directives, 'skipped': skipped, 'problems': problems,
            'temperature': temperature}


def parse_deck(text):
    """Element lines of a SPICE deck → {name: {'kind', 'nodes', 'value'}} (node counts by the element letter; X = all but the last token)."""
    out = {}
    count = {'R': 2, 'C': 2, 'L': 2, 'V': 2, 'I': 2, 'D': 2, 'Q': 3, 'M': 4, 'J': 3}
    in_control = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().startswith('.control'):
            in_control = True
        if line.lower().startswith('.endc'):
            in_control = False
            continue
        if in_control or not line or line[0] in '.*+':
            continue
        tok = line.split()
        kind = tok[0][0].upper()
        n = count.get(kind, len(tok) - 2 if kind == 'X' else 2)
        out[tok[0]] = {'kind': kind, 'nodes': tok[1:1 + n], 'value': ' '.join(tok[1 + n:])}
    return out
