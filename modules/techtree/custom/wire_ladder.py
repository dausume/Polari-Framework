"""
@module techtree.custom.wire_ladder

wire-1: THE DRAWING STRAIN of the manufacturing-tools tree.

Dustin 2026-07-31: "are there other kinds of wires that would need a
similar process at fine resolutions? Should we be standardizing a
tech tree around wire manufacturing in general since it seems to
have some high processing requirements?"

Yes, and yes — but NOT as its own tree. `manufacturing-tools`
already declares itself as the cross-cutting apparatus that refines
materials ("a furnace serves ceramics, metals AND glass"), and its
first populated branch is the THERMAL strain, the furnace escalation
ladder. Wire drawing is the same argument in a different axis, so it
belongs there as the DRAWING strain rather than as a rival tree. A
capability pulled on by many domains should live in one place, which
is precisely what that tree is for.

WHY WIRE EARNS A STRAIN OF ITS OWN. It is not one need, it is a
shared gate under many:
  - magnet wire for every coil we will ever wind (mag-22's clock);
  - THERMOCOUPLE wire, without which the kiln that fires the clock's
    ceramics cannot be controlled;
  - resistance wire for that kiln's own elements;
  - fine mesh, woven from fine wire, for grading powders — including
    the diamond grit that makes the die that draws the wire;
  - tungsten filament for a CVD reactor;
  - strain-gauge wire to validate the FEM we already trust.
Each pulls the same capability at a different rung, so the useful
question is not "can we draw wire" but WHICH RUNG UNLOCKS MOST.

THE PART WORTH THE TREE. Three of those dependencies are CIRCULAR —
the kiln needs wire that needs a die that needs a press, the CVD
reactor needs a filament that needs drawing, the grit needs a sieve
that needs fine wire. A flat ladder hides that. Every loop here is
carried WITH its documented break, because a loop without an entry
point is a dead end and a loop with one is just an ordering problem.

@consumers techtree.techtree_api, techtree.techtree_selftest
"""

PROV = 'wire-1'

#: Gauge ladder. Rungs are capability GATES, not sizes — each is the
#: point where the tooling has to change, which is why the bands are
#: uneven.
WIRE_RUNGS = [
    {
        'rung': 'W0', 'name': 'rod-and-heavy',
        'diameterMm': (12.0, 2.0), 'awgBand': (6, 12),
        'dies': 'hardened steel or tungsten carbide',
        'anneal': 'batch, in a furnace we already have',
        'coolant': 'flood, ambient',
        'difficulty': 'ordinary metalworking',
        'gate': 'a draw bench with real pulling force. The forces '
                'are the problem at this end, not precision.',
    },
    {
        'rung': 'W1', 'name': 'medium',
        'diameterMm': (2.0, 0.5), 'awgBand': (12, 24),
        'dies': 'tungsten carbide',
        'anneal': 'batch between passes',
        'coolant': 'soluble oil, ambient reservoir',
        'difficulty': 'plausible with patience',
        'gate': 'carbide dies in a graded set, and the discipline to '
                'anneal rather than force a pass.',
    },
    {
        'rung': 'W2', 'name': 'fine',
        'diameterMm': (0.5, 0.1), 'awgBand': (24, 38),
        'dies': 'carbide at the top, diamond preferred below ~0.25',
        'anneal': 'batch still workable at our volumes',
        'coolant': 'temperature-controlled emulsion',
        'difficulty': 'the honest edge of a home shop',
        'gate': 'die BORE finish starts to dominate — a scratch here '
                'prints on every metre drawn afterwards.',
    },
    {
        'rung': 'W3', 'name': 'ultrafine',
        'diameterMm': (0.1, 0.02), 'awgBand': (38, 50),
        'dies': 'diamond — single crystal traditionally, or PCD if '
                'the grit is fine enough (see PCD_ROUTE)',
        'anneal': 'batch is FINE at 210 m; in-line annealing is a '
                  'throughput feature, not a physics requirement',
        'coolant': 'chilled below ~35 C to keep the emulsion stable',
        'difficulty': 'a serious project, not a wall',
        'gate': 'a profiled, polished bore of a few tens of microns. '
                'This is the real work, and it is a PRECISION '
                'problem rather than a materials-availability one.',
    },
]

#: Who pulls on which rung. This is the argument for the strain: one
#: capability, many unrelated consumers.
WIRE_CONSUMERS = [
    {'consumer': 'magnet wire — clock/motor coils', 'rung': 'W2',
     'diameterMm': 0.16, 'material': 'copper',
     'tree': 'electronics',
     'why': 'CORRECTED by mag-25. mag-22 put this at W3 (46 AWG) by '
            'optimising for power — but coil voltage depends only '
            'on copper cross-section, and at 46 AWG the coil needs '
            '4.1 V, more than a cell can give, so that design was '
            'silently carrying a step-up converter. At 32-38 AWG it '
            'runs DIRECTLY off one cell and the only cost is a '
            'bigger bobbin. The clock belongs at W2.'},
    {'consumer': 'instrument coils — small movements', 'rung': 'W3',
     'diameterMm': 0.04, 'material': 'copper',
     'tree': 'electronics',
     'why': 'fine wire buys SIZE, not battery life. A movement that '
            'must be physically small still needs W3 — but that is '
            'a different product, with a converter in it.'},
    {'consumer': 'thermocouple wire (type K)', 'rung': 'W2',
     'diameterMm': 0.5, 'material': 'chromel/alumel',
     'tree': 'research-tools',
     'why': 'THE KILN CANNOT BE CONTROLLED WITHOUT ONE, and the kiln '
            'is what fires the clock ceramics. Two alloys, both '
            'drawn.'},
    {'consumer': 'kiln heating element', 'rung': 'W1',
     'diameterMm': 1.0, 'material': 'kanthal/nichrome',
     'tree': 'manufacturing-tools',
     'why': 'the furnace ladder\'s electric rungs are wound from '
            'resistance wire — the thermal strain depends on the '
            'drawing strain'},
    {'consumer': 'fine sieve mesh (powder grading)', 'rung': 'W3',
     'diameterMm': 0.025, 'material': 'stainless',
     'tree': 'materials-science',
     'why': 'a 400-mesh sieve is woven from ~25 um wire, and grading '
            'powder is how every ceramic recipe controls its '
            'particle size — INCLUDING the diamond grit for a PCD '
            'die'},
    {'consumer': 'tungsten filament (CVD reactor)', 'rung': 'W2',
     'diameterMm': 0.15, 'material': 'tungsten',
     'tree': 'manufacturing-tools',
     'why': 'hot-filament CVD runs a tungsten filament at ~2200 C. '
            'Tungsten is drawn HOT and is its own discipline — this '
            'is the least transferable rung on the list.'},
    {'consumer': 'strain gauge wire', 'rung': 'W3',
     'diameterMm': 0.025, 'material': 'constantan',
     'tree': 'research-tools',
     'why': 'we compute von Mises fields by FEM and have never '
            'measured one; a strain gauge is how that claim gets '
            'tested'},
    {'consumer': 'EDM wire', 'rung': 'W2',
     'diameterMm': 0.25, 'material': 'brass',
     'tree': 'manufacturing-tools',
     'why': 'wire EDM cuts precision profiles in hard material — '
            'including, plausibly, die blanks'},
]

#: The diamond chain Dustin named: grit, then a PCD die, then a
#: bench. Each step states what it needs and what it does NOT need,
#: because the second is what makes a plan actionable.
PCD_ROUTE = [
    {'step': 'D1', 'act': 'synthesise diamond GRIT',
     'route': 'HPHT: ~5-6 GPa and 1400-1600 C with an Fe/Ni/Co '
              'solvent-catalyst. 1954 technology, and grit is the '
              'easiest and highest-volume thing the process makes.',
     'needs': 'a belt or cubic press — the single largest capital '
              'item in this whole chain',
     'doesNotNeed': 'any single-crystal growth. Growing one large '
                    'crystal is the hard problem and this route '
                    'never asks for it.',
     'shortcut': 'industrial diamond micron powder is a cheap, '
                 'ubiquitous abrasive commodity. Buying grit and '
                 'sintering locally skips the press entirely for a '
                 'first die.'},
    {'step': 'D2', 'act': 'GRADE the grit',
     'route': 'sieving or, below sieve range, sedimentation and '
              'elutriation in a liquid column.',
     'needs': 'a narrow, known particle-size distribution — this is '
              'THE spec that decides whether the die works',
     'doesNotNeed': 'a fine sieve, IF graded by sedimentation. That '
                    'matters because fine sieves are woven from fine '
                    'wire, which is what we are trying to make.',
     'shortcut': 'sedimentation grading is glassware and patience'},
    {'step': 'D3', 'act': 'sinter a PCD compact',
     'route': 'HPHT again, diamond grit with a cobalt binder, into '
              'a die blank.',
     'needs': 'the press again, plus a few grams of cobalt',
     'doesNotNeed': 'high temperature service — the cobalt binder '
                    'catalyses graphitisation above ~700 C, which '
                    'is irrelevant at coolant temperature',
     'shortcut': 'PCD die blanks are themselves a stock item'},
    {'step': 'D4', 'act': 'BORE and profile the die',
     'route': 'entrance bell, approach cone, bearing land, back '
              'relief — traditionally cut by rotating a fine needle '
              'or wire loaded with diamond slurry.',
     'needs': 'precision and time. THIS IS THE REAL WORK and it '
              'survives every shortcut above: whether the blank is '
              'bought, sintered or single-crystal, someone still '
              'has to make a polished 40 um profiled hole.',
     'doesNotNeed': 'a large die inventory — one die per gauge step, '
                    'and our volumes are metres, not kilometres',
     'shortcut': 'none identified. Buying finished dies is the only '
                 'known bypass.'},
    {'step': 'D5', 'act': 'build the draw bench',
     'route': 'capstan drive, die holder, lubricant bath, spooler. '
              'Multi-die continuous machines are a production '
              'convenience; single-pass benches with rewinding are '
              'not.',
     'needs': 'steady low-speed pull and tension control — a break '
              'at 0.04 mm ends the run',
     'doesNotNeed': 'IN-LINE ANNEALING or a refrigerated chiller. '
                    'Both are THROUGHPUT features. We need 210 m of '
                    'magnet wire, so batch annealing between passes '
                    'and a reservoir with thermal mass are enough.',
     'shortcut': 'draw slowly. Almost every industrial requirement '
                 'on this list exists to keep a line running fast '
                 'and unattended.'},
]

#: The loops, each WITH its break. A cycle without an entry point is
#: a dead end; a cycle with one is only an ordering problem.
BOOTSTRAP_LOOPS = [
    {'loop': 'kiln -> thermocouple -> fine wire -> die -> press',
     'why': 'the kiln that fires the clock ceramics needs temperature '
            'control, and a thermocouple is drawn wire',
     'break': 'PYROMETRIC CONES. Potters controlled kilns for '
              'centuries without electronics, and we already specify '
              'cone 8-10 rather than a temperature — the loop was '
              'already broken before we noticed it was a loop.',
     'breakStrength': 'strong — established practice, and already '
                      'how our own ceramics rung is specified'},
    {'loop': 'CVD diamond -> tungsten filament -> wire drawing -> '
             'diamond die',
     'why': 'hot-filament CVD needs a tungsten filament, and drawing '
            'tungsten needs dies',
     'break': 'take the HPHT route instead, which needs no filament '
              'at all. Or buy one filament — it is a single '
              'consumable, not a supply chain.',
     'breakStrength': 'strong — two independent breaks'},
    {'loop': 'PCD die -> graded grit -> fine sieve -> fine wire -> '
             'PCD die',
     'why': 'grading grit finely suggests a fine sieve, which is '
            'woven from the fine wire we cannot yet draw',
     'break': 'grade by SEDIMENTATION rather than sieving. Stokes '
              'settling in a liquid column separates by size with '
              'no mesh anywhere.',
     'breakStrength': 'strong — and it reaches finer than sieving '
                      'does'},
]


def wire_ladder():
    """The gauge ladder with its tooling gates."""
    return {'ok': True, 'rungs': WIRE_RUNGS, 'count': len(WIRE_RUNGS),
            'provenance': PROV,
            'principle': 'rungs are capability GATES, not sizes — '
                         'each marks where the tooling must change, '
                         'which is why the bands are uneven'}


def unlock_analysis():
    """WHICH RUNG BUYS THE MOST. The point of treating wire as a
    shared capability rather than a per-project errand."""
    by_rung = {}
    for c in WIRE_CONSUMERS:
        by_rung.setdefault(c['rung'], []).append(c)
    order = [r['rung'] for r in WIRE_RUNGS]
    cumulative, running = [], 0
    for rung in order:
        here = by_rung.get(rung, [])
        running += len(here)
        cumulative.append({
            'rung': rung,
            'unlockedHere': [c['consumer'] for c in here],
            'cumulativeConsumers': running,
            'trees': sorted({c['tree'] for c in here}),
        })
    best = max(cumulative, key=lambda r: len(r['unlockedHere']))
    return {
        'ok': True, 'byRung': cumulative,
        'totalConsumers': len(WIRE_CONSUMERS),
        'biggestSingleUnlock': best['rung'],
        'finding': (
            f'{best["rung"]} unlocks the most in one step '
            f'({len(best["unlockedHere"])} consumers across '
            f'{len(best["trees"])} trees). But note what W2 alone '
            f'buys: the THERMOCOUPLE and the kiln element. Those are '
            f'the two that make the FURNACE ladder controllable, '
            f'and the furnace is what fires the ceramics the clock '
            f'needs. The cheapest rung is not the least valuable '
            f'one.'),
        'crossTreeNote': (
            'consumers sit in electronics, research-tools, '
            'materials-science and manufacturing-tools. That spread '
            'IS the argument for a shared strain: four trees pull '
            'one capability, and without a common node each would '
            'have rediscovered wire drawing separately.'),
    }


def pcd_route():
    """The diamond chain, with what each step does NOT need."""
    return {
        'ok': True, 'steps': PCD_ROUTE,
        'irreducible': [s for s in PCD_ROUTE
                        if 'none identified' in s['shortcut']],
        'finding': (
            'every step in this chain has a documented shortcut '
            'EXCEPT boring the die. Grit can be bought, grading can '
            'skip sieves, blanks are a stock item, and the bench can '
            'run slowly enough to drop in-line annealing and '
            'chilling. What survives all of it is producing a '
            'polished, profiled 40 um bore — so that is the '
            'capability to attack, and the one to prototype at a '
            'COARSER gauge first where a mistake costs less.'),
        'reframing': (
            'most industrial requirements on this chain — die life '
            '10-30x, in-line annealing, refrigerated coolant — exist '
            'to keep a production line running fast and unattended. '
            'We need 210 m of wire once. A die that visibly degrades '
            'over a few hundred metres is a production disaster and '
            'entirely acceptable to us, and that difference is worth '
            'stating wherever an industrial spec is quoted at us.'),
    }


def bootstrap_loops():
    """The circular dependencies, each with its break."""
    return {
        'ok': True, 'loops': BOOTSTRAP_LOOPS,
        'count': len(BOOTSTRAP_LOOPS),
        'principle': (
            'a loop is only a dead end if it has no entry point. '
            'Every loop here is carried WITH its break, and all '
            'three breaks turn out to be old technology: pyrometric '
            'cones, an alternative synthesis route, and settling in '
            'a column. Finding the loop was the hard part; none of '
            'the exits is exotic.'),
        'unbroken': [loop for loop in BOOTSTRAP_LOOPS
                     if not loop.get('break')],
    }


def drawing_strain():
    """The whole strain, composed — what to build and in what order."""
    unlock = unlock_analysis()
    return {
        'ok': True,
        'question': 'should wire manufacturing be a standardised '
                    'capability rather than a per-project errand',
        'answer': (
            'YES, and it belongs in manufacturing-tools as the '
            'DRAWING strain beside the existing THERMAL strain — not '
            'as its own tree. That tree already exists for exactly '
            'this: cross-cutting apparatus that refines materials, '
            'pulled on by many domains. Four trees consume wire.'),
        'ladder': wire_ladder(), 'unlock': unlock,
        'pcdRoute': pcd_route(), 'loops': bootstrap_loops(),
        'buildOrder': [
            {'step': 1, 'act': 'W1 bench and carbide dies',
             'buys': 'kiln elements — the furnace ladder stops '
                     'depending on bought resistance wire'},
            {'step': 2, 'act': 'W2 with careful bore finish',
             'buys': 'THERMOCOUPLE wire, which makes the furnace '
                     'controllable, which is what the ceramics rung '
                     'actually needs. Highest value per unit effort '
                     'on this list.'},
            {'step': 3, 'act': 'bore a die at W2 gauge as a REHEARSAL',
             'buys': 'the boring skill at a size where failure is '
                     'cheap — the one irreducible step, practised '
                     'before it is needed'},
            {'step': 4, 'act': 'grit, PCD compact, W3 die',
             'buys': 'magnet wire, sieve mesh, strain gauges — but '
                     'only after step 3 has proven the bore'},
        ],
        'honestOrdering': (
            'the clock started this and was assumed to sit at W3 — '
            'mag-25 moved it to W2, because the fine-wire design '
            'needed more voltage than a cell can supply and was '
            'quietly carrying a converter. The clock now shares a '
            'rung with the THERMOCOUPLE and sits one step above the '
            'kiln element, which is a better road than the one we '
            'drew first: the same rung that makes the furnace '
            'controllable also makes the movement. W3 is left to '
            'the consumers that genuinely need it — sieve mesh, '
            'strain gauges, and any movement that must be small.'),
        'provenance': PROV,
    }
