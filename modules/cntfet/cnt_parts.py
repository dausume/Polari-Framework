"""
@module cntfet.cnt_parts

Dustin 2026-08-29: "categorize by materials used for different
sub-sections of the FET … n-doped, p-doped, un-doped — what exactly
did we use for that; if we used a dielectric, what was that? A simple
list of the pieces and purpose of the FET."

One GENERIC reading for every FET (CNT or silicon): the ordered list
of PARTS — each with its purpose, its material, its doping (type /
species / concentration / method, or undoped / metal), its dimensions,
the process that made it where a row says so, and the ROW it is read
from. This list is also the contract the planned 2-D SVG view binds
to (FET_VIEWS_PLAN fv-7): every part = one SVG region with data.

@consumers cnt_api (GET /api/cntfet/device/{name}/parts), pages
"""

from cntfet.cnt_derive import get_row


def _ref(row):
    return {'className': type(row).__name__ if not hasattr(row, '_cls')
            else row._cls, 'name': getattr(row, 'name', '')}


def _part(part, purpose, material, doping, dims, row_ref, process='',
          notes='', region_kind=''):
    return {'part': part, 'purpose': purpose, 'material': material,
            'doping': doping, 'dimensions': dims, 'row': row_ref,
            'process': process, 'notes': notes,
            # the region this part maps to in the 2-D / 3-D views
            'regionKind': region_kind}


UNDOPED = {'type': 'undoped', 'species': '', 'concentration_cm3': None,
           'method': '', 'statement': 'intrinsic (no intentional dopant)'}
METAL = {'type': 'metal', 'species': '', 'concentration_cm3': None,
         'method': '', 'statement': 'metal — not a semiconductor'}
INSULATOR = {'type': 'insulator', 'species': '', 'concentration_cm3': None,
             'method': '', 'statement': 'dielectric — not a semiconductor'}


def _cnt_parts(manager, device):
    from cntfet.cnt_derive import resolve_components
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False, 'error': f'missing component rows: {missing}'}
    mat, geo, gate = rows['material'], rows['geometry'], rows['gate_stack']
    contact, transport = rows['contact'], rows['transport']
    par = rows.get('parasitics')
    pol = getattr(device, 'polarity', 'n') or 'n'
    chir = f'({mat.chirality_n},{mat.chirality_m})'
    ext_doping = {
        'type': pol, 'species': 'electrostatic / chemical (Efsd)',
        'concentration_cm3': None,
        'method': 'contact-region doping set by the Fermi level '
                  f'Efsd = {getattr(transport, "efsd_ev", 0):g} eV above '
                  'the band edge ([VS1] Sec.II.C; [FIO05] doped '
                  'extensions)',
        'statement': f'{pol}+ doped CNT extension (Efsd '
                     f'{getattr(transport, "efsd_ev", 0):g} eV)'}
    parts = [
        _part('source contact', 'injects carriers; sets the contact '
              'resistance Rc (quantum floor RQ/2)',
              getattr(contact, 'metal', 'Pd') or 'Pd', METAL,
              {'rc_ohm': getattr(contact, 'rc_ohm', None),
               'l_c_nm': getattr(geo, 'l_c_nm', None)},
              {'className': 'CNTContact', 'name': contact.name},
              notes=getattr(contact, 'rc_source', ''),
              region_kind='contact'),
        _part('source extension', 'low-resistance doped lead into the '
              'channel', f'CNT {chir}, {pol}+', ext_doping,
              {'l_ext_nm': getattr(geo, 'l_ext_nm', None)},
              {'className': 'CNTTransportModel', 'name': transport.name},
              region_kind='extension'),
        _part('channel', 'the gated semiconductor the switch happens in',
              f'semiconducting CNT {chir}, d = '
              f'{getattr(mat, "diameter_nm", 0):.3g} nm, Eg = '
              f'{getattr(mat, "eg_ev", 0):.3g} eV', UNDOPED,
              {'lg_nm': geo.lg_nm, 'diameter_nm': getattr(mat, 'diameter_nm', None),
               'tube_count': getattr(geo, 'tube_count', 1)},
              {'className': 'CNTMaterialState', 'name': mat.name},
              region_kind='channel'),
        _part('gate dielectric', 'insulates the gate; sets Cox and, with '
              'the quantum capacitance, Cinv — hence SS and Vt control',
              getattr(gate, 'dielectric_material', 'HfO2') or 'HfO2',
              INSULATOR,
              {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox,
               'geometry': getattr(gate, 'geometry', '')},
              {'className': 'GateStack', 'name': gate.name},
              process='gate-all-around dielectric (ALD idealised at S1)',
              region_kind='oxide'),
        _part('gate electrode', 'the control terminal; its work function '
              'sets the flat-band / Vt0 prior',
              'gate metal (W prior)', METAL,
              {'vt0_v': getattr(transport, 'vt0_v', None)},
              {'className': 'CNTTransportModel', 'name': transport.name},
              notes=getattr(transport, 'vt0_source', ''),
              region_kind='gate'),
        _part('drain extension', 'low-resistance doped lead out of the '
              'channel', f'CNT {chir}, {pol}+', ext_doping,
              {'l_ext_nm': getattr(geo, 'l_ext_nm', None)},
              {'className': 'CNTTransportModel', 'name': transport.name},
              region_kind='extension'),
        _part('drain contact', 'collects carriers; Rc as the source',
              getattr(contact, 'metal', 'Pd') or 'Pd', METAL,
              {'rc_ohm': getattr(contact, 'rc_ohm', None)},
              {'className': 'CNTContact', 'name': contact.name},
              region_kind='contact'),
    ]
    if par is not None:
        parts.append(_part('parasitics', 'lumped fringe / coupling '
                           'capacitance the intrinsic model does not carry',
                           '—', INSULATOR,
                           {'c_par_f': getattr(par, 'c_par_f', None)},
                           {'className': 'CNTParasitics', 'name': par.name},
                           notes=getattr(par, 'source', ''),
                           region_kind=''))
    return {'ok': True, 'technology': 'aligned-CNT (GAA)',
            'polarity': pol, 'parts': parts}


def _si_parts(manager, device):
    from sifet.si_device import resolve_components as si_resolve
    rows, missing = si_resolve(manager, device)
    if missing:
        return {'ok': False, 'error': f'missing component rows: {missing}'}
    shape, ch, sd = rows['shape'], rows['channel_doping'], rows['sd_doping']
    diel, proc = rows['dielectric'], rows['process']
    pol = getattr(device, 'polarity', 'n') or 'n'

    def doping(row, where):
        t = getattr(row, 'dopant_type', '')
        return {'type': t, 'species': getattr(row, 'species', ''),
                'concentration_cm3': getattr(row, 'concentration_cm3', None),
                'method': getattr(row, 'method', ''),
                'activation_fraction': getattr(row, 'activation_fraction', None),
                'statement': f'{t}-type {getattr(row, "species", "")} '
                             f'{getattr(row, "concentration_cm3", 0):.2g} cm⁻³ '
                             f'by {getattr(row, "method", "")} ({where})'}

    kind = getattr(shape, 'kind', '')
    diel_mat = getattr(diel, 'material', '')
    precursor = getattr(diel, 'precursor', '')
    parts = [
        _part('source contact', 'injects carriers; contact + extension '
              'resistance per µm width', 'silicide / metal (Rc prior)',
              METAL, {'rc_ohm_um': getattr(device, 'rc_ohm_um', None)},
              {'className': 'SiliconMOSFET', 'name': device.name},
              region_kind='contact'),
        _part('source / drain', 'heavily doped junctions that supply and '
              'collect the channel carriers', 'silicon',
              doping(sd, 'S/D'),
              {'junction_depth_nm': getattr(sd, 'junction_depth_nm', None)},
              {'className': 'SiliconDopingProfile', 'name': sd.name},
              process=getattr(sd, 'method', ''), region_kind='extension'),
        _part('channel / body', 'the gated silicon where inversion forms; '
              'body doping sets Vt (with the flat-band) and the depletion '
              'capacitance (n_ss)', f'silicon ({kind})',
              doping(ch, 'channel/body'),
              {'lg_nm': getattr(device, 'lg_nm', None),
               'w_nm': getattr(device, 'w_nm', None),
               'fin_height_nm': getattr(shape, 'fin_height_nm', None),
               'fin_width_nm': getattr(shape, 'fin_width_nm', None),
               'n_fins': getattr(shape, 'n_fins', None)},
              {'className': 'SiliconDopingProfile', 'name': ch.name},
              region_kind='channel'),
        _part('gate dielectric', 'insulates the gate; Cox from k and '
              'thickness — the sol-gel route is the open-source '
              'alternative to thermal / ALD oxides',
              f'{diel_mat}' + (f' from {precursor}' if precursor else ''),
              INSULATOR,
              {'thickness_nm': getattr(diel, 'thickness_nm', None),
               'k_rel': getattr(diel, 'k_rel', None),
               'anneal_c': getattr(diel, 'anneal_c', None),
               'anneal_min': getattr(diel, 'anneal_min', None),
               'leakage_prior_a_per_cm2': getattr(diel, 'leakage_prior_a_per_cm2', None)},
              {'className': 'SolGelDielectric', 'name': diel.name},
              process=(f'{getattr(proc, "deposition", "")} '
                       f'{getattr(proc, "spin_rpm", "")} rpm × '
                       f'{getattr(proc, "layers", "")} layer(s)'
                       if proc is not None else ''),
              notes=getattr(diel, 'citation', ''),
              region_kind='oxide'),
        _part('gate electrode', 'the control terminal; work function → '
              'flat-band voltage prior', 'gate metal / poly (Vfb prior)',
              METAL, {'vfb_v': getattr(device, 'vfb_v', None)},
              {'className': 'SiliconMOSFET', 'name': device.name},
              region_kind='gate'),
        _part('drain contact', 'collects carriers', 'silicide / metal '
              '(Rc prior)', METAL,
              {'rc_ohm_um': getattr(device, 'rc_ohm_um', None)},
              {'className': 'SiliconMOSFET', 'name': device.name},
              region_kind='contact'),
    ]
    return {'ok': True, 'technology': f'silicon MOSFET ({kind})',
            'polarity': pol, 'parts': parts}


def device_parts(manager, device):
    """The generic parts list for any FET row."""
    if hasattr(device, 'material'):
        report = _cnt_parts(manager, device)
    elif hasattr(device, 'shape'):
        report = _si_parts(manager, device)
    else:
        report = {'ok': False, 'error': 'not a known FET row class'}
    if not report.get('ok'):
        return report
    parts = report['parts']
    doped = [p for p in parts if p['doping']['type'] in ('n', 'p')]
    return {
        **report, 'device': device.name,
        'summary': {
            'partCount': len(parts),
            'n_doped': [p['part'] for p in doped if p['doping']['type'] == 'n'],
            'p_doped': [p['part'] for p in doped if p['doping']['type'] == 'p'],
            'undoped': [p['part'] for p in parts if p['doping']['type'] == 'undoped'],
            'dielectrics': [f"{p['part']}: {p['material']}" for p in parts
                            if p['doping']['type'] == 'insulator'],
            'metals': [f"{p['part']}: {p['material']}" for p in parts
                       if p['doping']['type'] == 'metal'],
        },
        'plainList': [f"{p['part']} — {p['material']} — "
                      f"{p['doping']['statement']} — {p['purpose']}"
                      for p in parts],
        'note': 'every part names the ROW it is read from; the same '
                'list is the binding contract of the 2-D parts view '
                '(FET_VIEWS_PLAN fv-7)',
    }
