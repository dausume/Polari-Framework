"""
@module motors.wire_insulation

mag-24: A RESEARCH ROUTE TO LOCALLY PRODUCIBLE MAGNET WIRE.

Dustin 2026-07-31: "we also will want to see if we can find a
research route toward a locally producible enamling for copper wire
and processing."

This is the right thing to attack. mag-22 found a locally producible
clock and had to declare ONE import: copper magnet wire. That import
is really TWO capabilities, and they fail differently:
  1. DRAWING copper to fine gauge, and
  2. INSULATING it.
Insulation turns out to be the tractable half and drawing the hard
one, which is the opposite of the intuitive order.

WHAT THE HISTORY GIVES US. Magnet wire was insulated for its first
half-century with no petrochemicals at all. What the trade called
"plain enamel" was an OLEORESINOUS VARNISH — a drying oil, usually
tung or linseed, cooked with a natural resin. Tung dominated because
it dries faster and harder than linseed and resists water better; by
the late 1920s ~90% of high-grade US varnishes contained it.
Synthetic enamel (polyvinyl formal) only arrived in 1939, and into
the 1950s most "plain enamel" was still a vegetable-oil alkyd. So
the question is not whether an oil-based magnet wire enamel can
work — it is what we give up using one.

THE CONSTRAINT THAT DECIDES IT, and it is not the chemistry:
INSULATION THICKNESS. mag-22's answer needs 15000 turns of 46 AWG,
and 46 AWG is 0.0399 mm of bare copper. Commercial enamel adds
~0.025 mm to the DIAMETER, which already makes the wound area 2.6x
the bare copper area. Anything thicker does not merely cost a little
fill — it squares. A fibre covering at 0.075 mm makes the wound area
over 12x bare, and the deep-winding strategy that the whole power
argument rests on simply stops fitting.

So this module does not argue about chemistry in the abstract. It
runs each candidate insulation through the EXISTING winding model at
its own build thickness and reports what happens to the window, the
turns, and therefore the battery life.

@consumers motors.motor_api, motors.selftest_motors
"""

PROV = 'mag-24'

#: Candidate insulations. `build_mm` is added to the wire DIAMETER
#: (both sides), which is what the winding model consumes. Values are
#: literature CLASS figures for fine gauges, not measurements of
#: anything we have made — the realization_level column says which is
#: which, and none of these is above literature-demonstrated.
INSULATION_OPTIONS = [
    {
        'name': 'ins-polyurethane-commercial',
        'display_name': 'Polyurethane enamel (bought wire)',
        'build_mm': 0.025,
        'temp_class_c': 155,
        'cure_c': 400,
        'local': False,
        'realization_level': 'buyable-cited',
        'flexibility': 'excellent',
        'inputs': ['petrochemical polyol + isocyanate',
                   'wire enamelling tower'],
        'why': 'THE BASELINE we are trying to replace. Solderable '
               'without stripping, which is why clock coils use it.',
        'blocker': 'not local at any level — the chemistry and the '
                   '400 C tower are both out of reach',
    },
    {
        'name': 'ins-oleoresinous-tung',
        'display_name': 'Oleoresinous varnish (tung oil + resin)',
        'build_mm': 0.040,
        'temp_class_c': 105,
        'cure_c': 180,
        'local': True,
        'realization_level': 'literature-demonstrated',
        'flexibility': 'good',
        'inputs': ['tung or linseed oil (pressed from seed)',
                   'natural resin (rosin/copal)',
                   'metallic drier (cobalt/manganese salt)',
                   'dip tank + 180 C bake, multiple passes'],
        'why': 'THE HISTORICAL ANSWER. This IS what magnet wire was '
               'insulated with before 1939 — the trade called it '
               '"plain enamel". Tung dries faster and harder than '
               'linseed and resists water better, which is why it '
               'took the market. Every input is a pressed oil or a '
               'tree resin, and the bake is oven temperature, not '
               'tower temperature.',
        'blocker': 'thicker than modern enamel and only class 105 C, '
                   'and the DRIER is a cobalt or manganese salt we '
                   'would still have to source',
    },
    {
        'name': 'ins-solgel-silica',
        'display_name': 'Sol-gel silica film',
        'build_mm': 0.006,
        'temp_class_c': 400,
        'cure_c': 350,
        'local': True,
        'realization_level': 'literature-demonstrated',
        'flexibility': 'BRITTLE',
        'inputs': ['silica sol (the materialsScience sol-gel stack '
                   'we already run)', 'dip-coater', '350 C bake'],
        'why': 'THINNEST of the local options by a wide margin, and '
               'it reuses a stack we already have rather than '
               'inventing one.',
        'blocker': 'BRITTLE is not a footnote here — the film has to '
                   'survive being bent round a 3 mm bobbin fifteen '
                   'thousand times. A ceramic film cracks and a '
                   'crack is a short. This is the option most worth '
                   'testing and least safe to assume.',
    },
    {
        'name': 'ins-silk-covered',
        'display_name': 'Silk covered (SSC)',
        'build_mm': 0.040,
        'temp_class_c': 90,
        'cure_c': 0,
        'local': True,
        'realization_level': 'literature-demonstrated',
        'flexibility': 'excellent',
        'inputs': ['silk thread', 'wire covering machine'],
        'why': 'NO CHEMISTRY AT ALL. Fine instrument and clock coils '
               'were wound with silk-covered wire for a century, and '
               'silk is thin enough to be usable at fine gauges '
               'where cotton is not.',
        'blocker': 'needs a covering machine that wraps thread round '
                   'a moving 0.04 mm wire without breaking it — the '
                   'mechanism is the hard part, not the material. '
                   'Also hygroscopic: it must be varnished after '
                   'winding.',
    },
    {
        'name': 'ins-cotton-covered',
        'display_name': 'Cotton covered (SCC)',
        'build_mm': 0.075,
        'temp_class_c': 90,
        'cure_c': 0,
        'local': True,
        'realization_level': 'literature-demonstrated',
        'flexibility': 'excellent',
        'inputs': ['cotton thread', 'wire covering machine'],
        'why': 'the most locally available fibre there is.',
        'blocker': 'TOO THICK for fine gauge. Included precisely to '
                   'show that — it is the option most people reach '
                   'for first and the numbers rule it out.',
    },
]

_BY_NAME = {o['name']: o for o in INSULATION_OPTIONS}

#: The drawing ladder. This is where "local" actually hurts.
DRAWING_LADDER = [
    {'stage': 'rod to ~1 mm', 'awgReach': 18,
     'tooling': 'tungsten carbide dies, hand or motor draw bench',
     'feasibility': 'reachable — WC dies are buyable and the forces '
                    'are modest',
     'note': 'reduction is 15-25% of area per pass with anneal '
             'steps between; this end of the ladder is ordinary '
             'metalworking'},
    {'stage': '1 mm to ~0.25 mm (30 AWG)', 'awgReach': 30,
     'tooling': 'WC dies, more passes, controlled anneal',
     'feasibility': 'plausible with patience and good lubrication',
     'note': 'anneal between passes or the copper work-hardens and '
             'snaps; commercial practice anneals in-line by passing '
             'current through the wire under water to stop oxide'},
    {'stage': '0.25 mm to 0.04 mm (46 AWG)', 'awgReach': 46,
     'tooling': 'NATURAL DIAMOND or polycrystalline diamond dies, '
                'in-line annealer, chilled coolant below 35 C',
     'feasibility': 'THE WALL. Carbide will not hold tolerance or '
                    'finish at these diameters — diamond dies last '
                    '10-30x longer and are effectively required. A '
                    'break at 0.04 mm ends the run.',
     'note': 'this is the step that makes buying wire the sensible '
             'answer, and it is a TOOLING wall rather than a '
             'knowledge one'},
]


def insulation_catalog():
    """Every candidate, with what it costs and what blocks it."""
    return {
        'ok': True, 'options': INSULATION_OPTIONS,
        'count': len(INSULATION_OPTIONS),
        'thicknessIsTheConstraint': (
            'build_mm adds to the wire DIAMETER, so its effect on '
            'the coil goes as the SQUARE. At 46 AWG (0.0399 mm bare) '
            'even commercial 0.025 mm enamel already makes the wound '
            'area 2.6x the copper area.'),
        'historyNote': (
            'magnet wire was insulated with oleoresinous varnish — '
            'drying oil plus natural resin — for its first half '
            'century. Synthetic enamel arrived in 1939 and '
            'vegetable-oil alkyds still dominated into the 1950s. '
            'An oil-based magnet wire enamel is not a novelty, it is '
            'the original.'),
        'provenance': PROV,
    }


def drawing_capability():
    """How far down the gauge ladder a local shop can realistically
    get, and where it stops."""
    return {
        'ok': True, 'ladder': DRAWING_LADDER,
        'localCeilingAwg': 30,
        'mag22NeedsAwg': 46,
        'finding': (
            'the INSULATION is the tractable half of this problem '
            'and the DRAWING is the wall — the opposite of the '
            'intuitive order. Oil-and-resin enamel is a dip tank and '
            'an oven; drawing to 46 AWG needs diamond dies, in-line '
            'annealing and chilled coolant, and a single break ends '
            'the run. A local shop can plausibly reach ~30 AWG.'),
        'consequence': (
            'if the wire must be locally DRAWN as well as insulated, '
            'the coil is stuck at a coarse gauge — and mag-22 showed '
            'the power answer lives in fine-gauge deep winding. That '
            'tension is quantified by insulated_winding_effect().'),
    }


def insulated_winding_effect(manager, design_name='clock-lavet-m0',
                             turns=15000, awg=46):
    """WHAT EACH INSULATION DOES TO THE mag-22 COIL.

    Runs every candidate through the EXISTING winding model at its
    own build thickness — no new winding arithmetic here — and
    reports the window it would need. mag-22 settled on 15000 turns
    of 46 AWG in an ~83 mm2 window; the question is which insulations
    still permit that.
    """
    import json
    from magnetics.magnet_analysis import _named
    from motors.motor_winding import winding_report
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no design named "{design_name}"'}
    original = getattr(design, 'params_json', '') or '{}'
    base = json.loads(original)
    base_mmf = (float(base.get('coil_turns', 0) or 0)
                * float(base.get('coil_amps', 0) or 0))
    rows = []
    try:
        for opt in INSULATION_OPTIONS:
            p = dict(base)
            p['coil_turns'] = turns
            p['coil_amps'] = base_mmf / float(turns)
            p['wire_awg'] = awg
            design.params_json = json.dumps(p)
            w = winding_report(manager, design_name,
                               enamel_mm=opt['build_mm'])
            if not w.get('ok'):
                rows.append({'insulation': opt['name'], 'ok': False,
                             'why': w.get('refusal', '')[:120]})
                continue
            window = float(w.get('bobbinWindowMm2') or 0.0)
            fill = float(w.get('fillFactor') or 0.0)
            rows.append({
                'insulation': opt['name'],
                'displayName': opt['display_name'],
                'ok': True, 'local': opt['local'],
                'buildMm': opt['build_mm'],
                'flexibility': opt['flexibility'],
                'fillFactor': fill,
                'windowNeededMm2': (round(window * fill / 0.6, 3)
                                    if fill else None),
                'copperMassG': w.get('copperMassG'),
                'blocker': opt['blocker'],
            })
    finally:
        design.params_json = original

    good = [r for r in rows if r.get('ok')]
    baseline = next((r for r in good
                     if r['insulation'] == 'ins-polyurethane-commercial'),
                    None)
    for r in good:
        if baseline and baseline['windowNeededMm2']:
            r['windowVsCommercial'] = round(
                r['windowNeededMm2'] / baseline['windowNeededMm2'], 2)
    locals_ = [r for r in good if r['local']]
    best = min(locals_, key=lambda r: r['windowNeededMm2'] or 1e9) \
        if locals_ else None
    return {
        'ok': True, 'design': design_name,
        'turns': turns, 'awg': awg,
        'rows': rows, 'bestLocal': best,
        'finding': (
            f'{best["displayName"]} is the thinnest local option, '
            f'needing a {best["windowNeededMm2"]} mm2 window — '
            f'{best["windowVsCommercial"]}x the bought-wire '
            f'baseline. But read its blocker before treating that as '
            f'the answer: {best["blocker"][:120]}'
            if best else
            'no local insulation produced a winding at these turns'),
        'squareLaw': (
            'build thickness adds to DIAMETER, so the window penalty '
            'goes as the square. That is why cotton — the most '
            'available fibre of all — is ruled out by arithmetic '
            'rather than by taste.'),
    }


def local_wire_route(manager, design_name='clock-lavet-m0'):
    """THE RESEARCH ROUTE, composed: what to try, in what order, and
    what each step would prove."""
    eff = insulated_winding_effect(manager, design_name)
    draw = drawing_capability()
    if not eff.get('ok'):
        return eff
    return {
        'ok': True, 'question': 'a locally producible route to '
                                'insulated copper magnet wire',
        'twoCapabilities': [
            {'capability': 'INSULATING the wire',
             'verdict': 'TRACTABLE',
             'why': 'oleoresinous varnish was the industry standard '
                    'until 1939 and needs a dip tank and a 180 C '
                    'oven. Sol-gel silica is thinner still and '
                    'reuses a stack we already run.'},
            {'capability': 'DRAWING the wire to fine gauge',
             'verdict': 'THE WALL',
             'why': draw['finding']},
        ],
        'insulationEffect': eff, 'drawing': draw,
        'researchOrder': [
            {'step': 1,
             'act': 'buy bare 46 AWG copper and enamel it ourselves '
                    'with tung-oil varnish',
             'proves': 'the INSULATION half in isolation, which is '
                       'the half we can actually win. Measure the '
                       'build thickness and the breakdown voltage, '
                       'then wind a coil and see whether it shorts.',
             'cost': 'a dip tank, an oven, and oil we can press'},
            {'step': 2,
             'act': 'sol-gel dip a short length and BEND IT round a '
                    '3 mm former',
             'proves': 'whether the brittleness objection is fatal. '
                       'This is a one-afternoon test that either '
                       'opens the thinnest local route or closes '
                       'it, and guessing is worse than either.',
             'cost': 'the sol-gel stack we already have'},
            {'step': 3,
             'act': 'draw copper down the WC ladder as far as it '
                    'goes, and record where it stops',
             'proves': 'the real local gauge ceiling. The literature '
                       'says ~30 AWG without diamond dies; our '
                       'number is the one that matters and we do '
                       'not have it.',
             'cost': 'a draw bench, WC dies, an anneal step'},
            {'step': 4,
             'act': 'rerun the mag-22 turns sweep at whatever gauge '
                    'step 3 actually reached',
             'proves': 'whether a fully locally-made coil can still '
                       'hit the power target, or whether wire stays '
                       'the one honest import.',
             'cost': 'nothing — the sweep already exists'},
        ],
        'honestExpectation': (
            'the likely outcome is that insulation goes local and '
            'DRAWING does not, leaving bare fine wire as the import '
            'instead of finished magnet wire. That is a real '
            'improvement and a smaller dependency, and it is not the '
            'same as closing the loop. Saying so now is better than '
            'discovering it at step 3.'),
        'provenance': PROV,
    }
