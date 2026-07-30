"""
@module motors.motor_parts

mag-11: THE PER-PART BILL — every physical piece of the motor tied
to the material it is made of, the properties that RESULT from that
choice, and WHAT THE PIECE IS FOR in the clock.

Until now the pieces and the materials lived apart: geometry was
MathShapeDefinition rows, materials were per-SLOT on the design
(rotor_material / stator_material / winding_material), and nothing
said which shape was made of what, how much it weighed, what it
cost, or why it existed. A reader could see a stator plate and a
list of magnetic options and had to join them in their head.

A MotorPartDefinition row makes that join explicit and, more
importantly, carries the FUNCTION — the sentence that says why the
part is in the machine at all. "The window in the stator plate
forces flux around the rotor instead of across it" is not
decoration; it is the reason the part is shaped the way it is, and
it belongs next to the material and the mass.

Everything numeric DERIVES:
  volume    from the part's own MathShapeDefinition (mathshapes
            shape_properties — the SAME geometry the viewer draws
            and the mould would cast, so the mass cannot drift from
            the picture)
  mass      volume x the material's density property
  cost      mass x the cascaded make-or-buy price (supplychain)
and each one REFUSES rather than guessing when its input is absent:
no shape row, no volume; no density, no mass; no cascade, no cost.

@consumers motors.motor_api, motors.selftest_motors
"""

from objectTreeDecorators import treeObject, treeObjectInit

from magnetics.magnet_analysis import _named, _rows

#: What a piece DOES in the machine. The vocabulary is functional,
#: not geometric — two parts can be the same shape and have
#: different jobs, and the job is what a reader actually needs.
PART_FUNCTIONS = (
    'flux-path', 'flux-shaping', 'field-source', 'torque-producing',
    'detent', 'mmf-source', 'power-transmission', 'structural',
    'electrical-connection', 'viz-only',
)


class MotorPartDefinition(treeObject):
    """One physical piece: its geometry, its material, and its job.

    `shape_ref` points at a MathShapeDefinition, so volume/mass/cost
    derive from the SAME rows the 3D view renders — the picture and
    the bill cannot disagree."""

    @treeObjectInit
    def __init__(self, name='', display_name='', design_ref='',
                 shape_ref='', shape_units='cm', material_ref='',
                 function='flux-path',
                 purpose='', why_this_material='', quantity=1,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.design_ref = design_ref
        self.shape_ref = shape_ref
        #: Units the SHAPE row is authored in. mathshapes'
        #: shape_properties reports volumeCm3, i.e. it assumes cm —
        #: but the Lavet v2 geometry is authored in mm (1 unit =
        #: 1 mm), and reading those as cm silently turned a clock
        #: motor into a 1.1 kg object. Declaring the unit per part
        #: makes the conversion explicit instead of a footnote
        #: nobody applies.
        #: MagneticMaterialOption name, or a supplychain item_ref
        #: for non-magnetic parts (copper wire, steel shaft).
        self.material_ref = material_ref
        self.function = (function if function in PART_FUNCTIONS
                         else 'structural')
        #: WHAT IT IS FOR, in a sentence a builder can act on.
        self.purpose = purpose
        #: Why THIS material for THIS job — the property that
        #: actually decided it, not a general description.
        self.why_this_material = why_this_material
        self.quantity = quantity
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


#: The Lavet v2 parts (mag-10b geometry), each with its job.
SEED_MOTOR_PARTS = [
    {'name': 'lavet-v2-stator', 'design_ref': 'clock-lavet-m0',
     'display_name': 'Stator plate (squared-C bracket)',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-stator',
     'material_ref': 'opt-geopolymer-ferrite',
     'function': 'flux-shaping',
     'purpose': 'Carries the coil\'s flux around to the rotor bore '
                'and back. The big rectangular WINDOW is what makes '
                'it work: without it the flux would take the short '
                'path straight across the plate and never reach the '
                'rotor. The narrow neck beside the bore saturates '
                'first, which is what concentrates field INTO the '
                'gap rather than letting it leak.',
     'why_this_material': 'Needs the highest mu we can cast — this '
                          'is the flux CONDUCTOR, and every unit of '
                          'reluctance here is torque lost. At '
                          'mu~2.2 our composite is far below the '
                          'laminated steel a commercial movement '
                          'uses (mu ~1e3-1e4), and that gap is why '
                          'our detent is coarse and our pulse '
                          'current is milliamps where a real clock '
                          'uses microamps.',
     'quantity': 1, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': ''},
    {'name': 'lavet-v2-rotor-magnet',
     'design_ref': 'clock-lavet-m0',
     'display_name': 'Rotor magnet (diametric cylinder)',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-rotor-magnet',
     'material_ref': 'opt-bonded-hexaferrite-geopolymer',
     'function': 'torque-producing',
     'purpose': 'THE part that actually turns. Magnetised across '
                'its diameter, so it has a north side and a south '
                'side; the coil\'s field pushes one and pulls the '
                'other, and the pair of forces is the torque. Every '
                'other piece exists to serve this one.',
     'why_this_material': 'Must be HARD magnetic — it has to keep '
                          'its own field against the coil\'s '
                          'reversing one. B_r sets the torque '
                          'directly; H_c is what stops the coil '
                          'demagnetising it. This is the single '
                          'part where a soft material (magnetite) '
                          'fails outright, which is what the mag-2r '
                          'torque-magnet role predicate encodes.',
     'quantity': 1, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': ''},
    {'name': 'lavet-v2-coil', 'design_ref': 'clock-lavet-m0',
     'display_name': 'Coil winding (1500 t, 44 AWG)',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-coil',
     'material_ref': 'magnet-wire-copper',
     'function': 'mmf-source',
     'purpose': 'Turns the quartz oscillator\'s 1 Hz electrical '
                'pulse into a magnetic one. Its ALTERNATING '
                'polarity is the whole mechanism: each pulse '
                'reverses the field, the rotor flips 180 degrees to '
                'realign, and one flip per second is one second '
                'hand tick. Same-polarity pulses do nothing — the '
                'sim demonstrates that failure deliberately.',
     'why_this_material': 'Copper, because conductivity decides how '
                          'many amp-turns a given voltage buys. Our '
                          'ferrite-CNT conductor is ~5 orders of '
                          'magnitude worse and cannot do this job '
                          '— it is the one part of the motor the '
                          'local materials stack cannot yet make, '
                          'and the mag-8 wire co-op exists because '
                          'of it.',
     'quantity': 1, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': 'Volume here is the winding BODY (the tube), so its '
              'mass is the copper plus air between turns — the '
              'mag-9 winding report gives the true wire mass from '
              'turns x length, and that is the number to trust for '
              'cost.'},
    {'name': 'lavet-v2-pinion', 'design_ref': 'clock-lavet-m0',
     'display_name': 'Rotor pinion (8 teeth, module 0.3)',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-rotor-pinion',
     'material_ref': 'opt-plain-geopolymer',
     'function': 'power-transmission',
     'purpose': 'Hands the rotor\'s motion to the gear train. This '
                'is where the motor stops and the CLOCK starts: 8 '
                'teeth driving the 240-tooth seconds wheel is the '
                '30:1 first stage that turns 30 rpm of rotor into '
                '1 rpm of seconds hand. The rest of the reduction '
                '(60:1 more, to one turn per hour) is the gears '
                'module\'s clock-train-m0.',
     'why_this_material': 'Non-magnetic ON PURPOSE — a ferrous '
                          'pinion sitting on the rotor would offer '
                          'the flux a parallel path and steal from '
                          'the working gap. Here plain geopolymer '
                          'is the RIGHT choice precisely because it '
                          'is magnetically useless.',
     'quantity': 1, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': 'Teeth are generated by gears gr-3; the shape row is '
              'the pitch cylinder.'},
    {'name': 'lavet-v2-bobbin-flanges',
     'design_ref': 'clock-lavet-m0',
     'display_name': 'Bobbin flanges (x2)',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-bobbin-flange-a',
     'material_ref': 'opt-plain-geopolymer',
     'function': 'structural',
     'purpose': 'Keeps 1500 turns of hair-fine wire stacked on the '
                'core instead of sliding off the ends. Unglamorous, '
                'and the coil is unwindable without it.',
     'why_this_material': 'Non-magnetic and non-conductive: it sits '
                          'in the coil\'s field, so a conductive '
                          'flange would carry eddy currents and a '
                          'magnetic one would short the flux path.',
     'quantity': 2, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': ''},
    {'name': 'lavet-v2-leads', 'design_ref': 'clock-lavet-m0',
     'display_name': 'Coil lead wires (x2)',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-lead-a',
     'material_ref': 'magnet-wire-copper',
     'function': 'electrical-connection',
     'purpose': 'The two ends of the winding, brought out to the '
                'driver. Polarity matters here and nowhere else: '
                'swap them and the motor still runs, because the '
                'drive alternates anyway — which is a genuinely '
                'useful property of this design.',
     'quantity': 2, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': ''},
    {'name': 'lavet-v2-index', 'design_ref': 'clock-lavet-m0',
     'display_name': 'Rotor index mark',
     'shape_units': 'mm', 'shape_ref': 'motor-m0v2-rotor-index',
     'material_ref': '',
     'function': 'viz-only',
     'purpose': 'Not a part of the motor — a scribe on the rotor '
                'top so a viewer can SEE the 180 degree step. It is '
                'in the parts list so that nobody mistakes it for '
                'one, and so its mass never lands in the bill.',
     'why_this_material': 'No material: it is a mark, not a piece.',
     'quantity': 1, 'is_prior': True, 'provenance_id': 'mag-11',
     'notes': ''},
]


# ------------------------------------------------------------------ #
# The report. Every number DERIVES, and every derivation refuses
# rather than guessing when its input is absent.
# ------------------------------------------------------------------ #

def _prop_entry(option, key):
    """(value, provenance) for one property of a catalog option."""
    import json as _json
    try:
        props = _json.loads(getattr(option, 'properties_json', '')
                            or '{}')
    except (TypeError, ValueError):
        return None, ''
    entry = props.get(key)
    if not isinstance(entry, dict):
        return None, ''
    return entry.get('value'), entry.get('provenance', '')


#: mm-authored geometry -> cm3: (1/10)^3.
_UNIT_TO_CM3 = {'cm': 1.0, 'mm': 0.001}


def _part_volume_cm3(manager, shape_ref, units='cm'):
    """Volume from the part's OWN geometry row — the same shape the
    viewer draws, so the bill cannot drift from the picture."""
    if not shape_ref:
        return None, 'no shape row referenced'
    try:
        from mathshapes.shape_analysis import shape_properties
    except ImportError:
        return None, ('mathshapes module not enabled — geometry '
                      'cannot be measured')
    out = shape_properties(manager, shape_ref)
    if not out.get('ok'):
        return None, out.get('error', 'shape not found')
    factor = _UNIT_TO_CM3.get(units)
    if factor is None:
        return None, (f'unknown shape_units "{units}" — state '
                      f'"cm" or "mm"')
    raw = out.get('volumeCm3')
    return (None if raw is None else raw * factor), ''


def part_report(manager, design_name):
    """Every piece of one design: what it is, what it is made of,
    what that makes it, and WHAT IT IS FOR."""
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no MotorDesignDefinition named '
                           f'"{design_name}"'}
    parts = [p for p in _rows(manager, 'MotorPartDefinition')
             if getattr(p, 'design_ref', '') == design_name]
    if not parts:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition rows for '
                           f'"{design_name}" — the design has '
                           f'materials by SLOT but no per-piece '
                           f'bill yet',
                'suggestion': {'knob': 'MotorPartDefinition',
                               'action': 'seed the parts for this '
                                         'design'}}
    entries, gaps = [], []
    total_mass_g = 0.0
    total_cost = 0.0
    cost_complete = True
    for p in sorted(parts, key=lambda r: getattr(r, 'name', '')):
        name = getattr(p, 'name', '')
        qty = int(getattr(p, 'quantity', 1) or 1)
        shape_ref = getattr(p, 'shape_ref', '')
        units = getattr(p, 'shape_units', 'cm') or 'cm'
        vol, vol_gap = _part_volume_cm3(manager, shape_ref, units)
        mat_ref = getattr(p, 'material_ref', '')
        option = (_named(manager, 'MagneticMaterialOption', mat_ref)
                  if mat_ref else None)

        density = provenance = None
        props = []
        if option is not None:
            density, provenance = _prop_entry(option,
                                              'density_kg_m3')
            import json as _json
            try:
                raw = _json.loads(
                    getattr(option, 'properties_json', '') or '{}')
            except (TypeError, ValueError):
                raw = {}
            props = [{'property': k, 'value': v.get('value'),
                      'unit': v.get('unit', ''),
                      'provenance': v.get('provenance', ''),
                      'note': v.get('note', '')}
                     for k, v in sorted(raw.items())
                     if isinstance(v, dict)]

        mass_g = None
        if vol is not None and density:
            # cm3 * kg/m3 = g  (1e-6 m3 per cm3, 1e3 g per kg)
            mass_g = vol * float(density) / 1000.0 * qty
            if getattr(p, 'function', '') != 'viz-only':
                total_mass_g += mass_g

        entry = {
            'part': name,
            'displayName': getattr(p, 'display_name', ''),
            'quantity': qty,
            'function': getattr(p, 'function', ''),
            'purpose': getattr(p, 'purpose', ''),
            'whyThisMaterial': getattr(p, 'why_this_material', ''),
            'shapeRef': shape_ref,
            'volumeCm3': (round(vol, 6) if vol is not None
                          else None),
            'shapeUnits': units,
            'material': mat_ref or None,
            'materialDisplayName': (getattr(option, 'display_name',
                                            '') if option else None),
            'realizationLevel': (getattr(option, 'realization_level',
                                         '') if option else None),
            'densityKgM3': density,
            'densityProvenance': provenance,
            'massG': (round(mass_g, 4) if mass_g is not None
                      else None),
            'properties': props,
            'notes': getattr(p, 'notes', ''),
        }
        if vol is None and getattr(p, 'function', '') != 'viz-only':
            entry['volumeGap'] = vol_gap
            gaps.append(f'{name}: {vol_gap}')
        if mat_ref and option is None:
            entry['materialGap'] = (
                f'"{mat_ref}" is not a MagneticMaterialOption — it '
                f'is a supplychain item (wire, shaft), so its '
                f'properties live there and no density is resolved '
                f'here')
        if mass_g is None and getattr(p, 'function', '') not in (
                'viz-only',):
            gaps.append(f'{name}: no mass (needs volume AND a '
                        f'density property)')
            cost_complete = False
        entries.append(entry)

    by_function = {}
    for e in entries:
        by_function.setdefault(e['function'], []).append(e['part'])

    return {
        'ok': True, 'design': design_name,
        'ladderRung': getattr(design, 'ladder_rung', ''),
        'parts': entries, 'count': len(entries),
        'byFunction': by_function,
        'totalMassG': round(total_mass_g, 4),
        'massNote': 'viz-only parts are excluded from the total — '
                    'a mark on the rotor is not a piece',
        'gaps': gaps,
        'costComplete': cost_complete,
        'honesty': 'volumes come from each part\'s OWN '
                   'MathShapeDefinition — the same rows the 3D view '
                   'draws and a mould would cast, so the bill and '
                   'the picture cannot disagree. Mass = volume x '
                   'the material row\'s density; where either is '
                   'missing the part reports a GAP instead of a '
                   'guessed number. The coil\'s volume is its '
                   'winding BODY (copper plus the air between '
                   'turns) — for true wire mass and cost use the '
                   'mag-9 winding report.',
    }
