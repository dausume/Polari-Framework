"""
@module board.custom.enclosure_kinds

hsp-0 (L1, HARDWARE_SYSTEM_PINS_PLAN.md §2): THE ENCLOSURE KINDS CATALOGUE — every kind listed in SYSTEM_HIERARCHY_TERMINOLOGY.md §12.2 "By level"
(levels E0 die .. E5 installation), every row `status: tentative` (his go 2026-10-17: "tentatively make the different kinds of enclosures we need ...
we are only accounting for terminology and the need for devices down the road"). TERMINOLOGY DATA ONLY: no physics number lives here (no
thermal resistance, no IP rating, no stress) — those belong to the Embedded Device slice, which is not built.

`functions_json` is a subset of FUNCTIONS (terminology §12.2 "By function"): mechanical | thermal | ingress | emi | electrical-safety | exposure | optical.
Each kind's `notes` says WHY those functions (plain reasoning, not a measurement). `pin_relevant` is true when the kind exposes or carries electrical
pins / contacts (a chip package, a board, a connector, a carrier), false for a pure body part (a heat sink, a gasket, a vent).
One row per kind; `E2:test-pad` is the one addition beyond the §12.2 table: §11.1 names test pads as an exposure feature and the UNO schematic has them.
"""
FUNCTIONS = ('mechanical', 'thermal', 'ingress', 'emi', 'electrical-safety', 'exposure', 'optical')
LEVELS = {0: 'E0', 1: 'E1', 2: 'E2', 3: 'E3', 4: 'E4', 5: 'E5'}
LEVEL_NAMES = {0: 'die', 1: 'component', 2: 'board', 3: 'sub-assembly', 4: 'device housing', 5: 'installation'}
SRC = 'SYSTEM_HIERARCHY_TERMINOLOGY.md §12.2 (by level), 2026-10-17'

M, T, I, E, S, X, O = FUNCTIONS
#: (level, slug, title, functions, pin_relevant, plain words, why these functions)
KINDS = [
    (0, 'passivation', 'Die passivation', (I, M), False, 'the thin glassy skin over the finished chip that keeps moisture and dirt off the circuit', 'protects the die surface: environment first, a little mechanical'),
    (0, 'die-attach', 'Die attach', (M, T), False, 'the glue or solder layer that holds the chip to its carrier and carries heat out of it', 'holds the die (mechanical) and is the first step of the heat path (thermal)'),
    (0, 'underfill', 'Underfill', (M, T), False, 'a filler under a flip-chip die that spreads stress and heat', 'spreads thermal-expansion stress (mechanical) and heat (thermal)'),
    (0, 'glob-top', 'Glob-top (chip on board)', (M, I), False, 'a blob of resin over a bare chip bonded straight onto a board', 'covers a bare die and its bond wires: mechanical protection and environment'),
    (1, 'dip', 'DIP package', (M, T, X), True, 'a through-hole chip case with two rows of legs (the UNO\'s main chip is the shrink version)', 'plastic body holds the die (mechanical), the legs are the exposure (exposure), the body is the die\'s first heat path (thermal)'),
    (1, 'soic', 'SOIC package', (M, T, X), True, 'a small surface-mount chip case with gull-wing legs on two sides', 'same functions as any chip package: body, legs, first heat path'),
    (1, 'tqfp', 'TQFP package', (M, T, X), True, 'a thin flat surface-mount chip case with legs on four sides (the surface-mount variant of the UNO\'s main chip)', 'same functions as any chip package: body, legs, first heat path'),
    (1, 'qfn', 'QFN package', (M, T, X), True, 'a flat chip case with pads under its edge and often a centre pad (the UNO\'s USB chip)', 'body, edge pads (exposure) and a centre pad that is the main heat path into the board (thermal)'),
    (1, 'bga', 'BGA package', (M, T, X), True, 'a chip case with a grid of solder balls underneath', 'body, ball grid (exposure) and heat through the balls (thermal)'),
    (1, 'sot', 'SOT package', (M, T, X), True, 'a tiny three-to-six-leg surface-mount case for transistors and small chips', 'body, legs, first heat path'),
    (1, 'to-220', 'TO-220 package', (M, T, X), True, 'a three-leg power-transistor case with a metal tab for a heat sink', 'legs (exposure) and the tab, a deliberate heat path (thermal); the tab may also be an electrical contact'),
    (1, 'to-92', 'TO-92 package', (M, X), True, 'a small three-leg plastic through-hole case for small transistors and sensors', 'body and legs; its heat path is small and is left to the device level'),
    (1, 'led-dome', 'LED dome', (M, O, X), True, 'the clear lens over an LED that shapes and lets out its light', 'holds the die (mechanical), lets light out (optical), the leads are the exposure'),
    (1, 'crystal-can', 'Crystal can', (M, I, X), True, 'the sealed metal can around a quartz crystal', 'sealed against environment (ingress), holds the crystal (mechanical), leads are the exposure'),
    (1, 'relay-can', 'Relay can', (M, I, E, S, X), True, 'the sealed case around a relay\'s coil and switch', 'mechanical and sealing; a relay case also keeps coil and contacts apart (electrical-safety) and shields them (emi)'),
    (1, 'electrolytic-can', 'Electrolytic capacitor can', (M, T, X), True, 'the metal can around an electrolytic capacitor', 'holds the foil and electrolyte (mechanical), the can is its heat path (thermal), leads are the exposure'),
    (1, 'optocoupler', 'Optocoupler package', (M, S, O, X), True, 'a chip case holding an LED and a light sensor that pass a signal across a gap', 'keeps the two sides electrically apart (electrical-safety), passes light inside (optical), legs are the exposure'),
    (1, 'connector-shell', 'Connector shell', (M, E, X), True, 'the metal or plastic housing of a connector (a USB socket, a header)', 'holds the contacts (mechanical), a metal shell is also the shield ground (emi), the contacts are the exposure'),
    (1, 'servo-housing', 'Servo housing', (M, I, X), True, 'the case around a servo\'s motor and gears', 'holds the mechanism (mechanical), may be sealed (ingress), its wire or plug is the exposure'),
    (1, 'motor-housing', 'Motor housing', (M, T, X), True, 'the case around a motor', 'holds the motor (mechanical), carries its heat (thermal), terminals are the exposure'),
    (1, 'sensor-housing', 'Sensor housing', (M, I, O, X), True, 'the case around a sensor, with whatever opening or window it needs', 'holds the sensor (mechanical), seals it (ingress), may need an opening or window (optical), pins are the exposure'),
    (2, 'board', 'The board (PCB or dev board)', (M, T, E, S, X), True, 'the circuit board that carries the chips and brings their pins out to headers and connectors', 'carries everything (mechanical), spreads heat through copper (thermal), routes and isolates signals (electrical-safety), headers and connectors are the exposure'),
    (2, 'heat-sink', 'Heat sink', (T, M), False, 'a finned metal part bolted to a chip or the board to carry heat away', 'a body part: thermal, held on mechanically; carries no pin'),
    (2, 'thermal-pad-via', 'Thermal pads and vias', (T,), False, 'soft pads and copper-plated holes that carry heat from a part into the board or the case', 'a body part: thermal only'),
    (2, 'shield-can', 'RF/EMI shield can', (E, M), False, 'a metal lid soldered over a group of components to block radio noise', 'a body part: emi, held on mechanically'),
    (2, 'conformal-coating', 'Conformal coating', (I, S), False, 'a thin lacquer over the finished board against moisture and dust', 'a body part: ingress, and it adds insulation (electrical-safety)'),
    (2, 'potting', 'Potting', (I, M, T, S), False, 'resin poured around a board or module to seal and hold it', 'a body part: ingress and mechanical support; it also carries heat and insulates'),
    (2, 'test-pad', 'Test pad', (X,), True, 'a bare copper dot on a board where a probe can touch a signal', 'exposure only; not in the §12.2 table: §11.1 names test pads as an exposure feature and the UNO schematic has them'),
    (3, 'shield-stack', 'Shield stack', (M, X), True, 'a board that plugs on top of another and passes its pins up (an Arduino shield)', 'stacks mechanically (mechanical) and passes the pins through (exposure)'),
    (3, 'module-carrier', 'Module carrier', (M, T, X), True, 'a base board that holds a plug-in module and brings its pins out', 'holds the module (mechanical), may carry its heat (thermal), brings pins out (exposure)'),
    (3, 'standoff', 'Standoff', (M,), False, 'a small post that holds two boards apart', 'a body part: mechanical only'),
    (3, 'bracket', 'Bracket', (M,), False, 'a metal or plastic piece that fixes a board or module to something', 'a body part: mechanical only'),
    (3, 'card-cage', 'Card cage', (M, E, T), False, 'a frame that holds several boards side by side', 'a body part: holds the boards (mechanical), shields them (emi), gives air a path (thermal)'),
    (3, 'daughterboard', 'Daughterboard', (M, X), True, 'a smaller board plugged or soldered onto a bigger one', 'holds parts (mechanical) and passes pins to the board below (exposure)'),
    (3, 'harness-sleeve', 'Harness sleeve', (M, I), False, 'a protective sleeve around a bundle of wires', 'a body part: protects the wires (mechanical) and from the environment (ingress)'),
    (4, 'housing-3d-printed', 'Housing, 3D-printed', (M, T, I, O), False, 'a device case printed in plastic (a print job)', 'holds the device (mechanical), sets the inner ambient (thermal), seals only as well as the print (ingress), may carry a window (optical); its pins cross through its panel, button and gland features'),
    (4, 'housing-injection-moulded', 'Housing, injection-moulded', (M, T, I, O), False, 'a device case moulded in plastic', 'holds the device (mechanical), sets the inner ambient (thermal), can seal well (ingress), may carry a window (optical); its pins cross through its features'),
    (4, 'housing-sheet-metal', 'Housing, sheet-metal', (M, T, E, I, S), False, 'a device case folded from sheet metal', 'holds the device (mechanical), carries heat (thermal), shields (emi), seals (ingress), and a metal case must be grounded (electrical-safety)'),
    (4, 'housing-extruded-aluminium', 'Housing, extruded aluminium', (M, T, E, I, S), False, 'a device case cut from an aluminium profile; it also works as the heat sink', 'holds the device (mechanical), doubles as the heat sink (thermal), shields (emi), seals (ingress), must be grounded (electrical-safety)'),
    (4, 'panel', 'Panel', (M, X), True, 'the face of a housing that carries buttons, sockets and lights', 'holds the controls (mechanical) and is where the device\'s inner pins reach the person (exposure)'),
    (4, 'gasket', 'Gasket', (I,), False, 'a soft seal between two housing parts', 'a body part: ingress only'),
    (4, 'window', 'Window', (O, I), False, 'a clear part of a housing that lets a display or light be seen', 'optical, and it must seal (ingress)'),
    (4, 'light-pipe', 'Light pipe', (O,), False, 'a clear rod that carries an LED\'s light to a hole in the housing', 'optical only'),
    (4, 'button-cap', 'Button cap', (M, X), True, 'the part a person presses to operate a switch on the board', 'moves a switch (mechanical) and is the person-side end of an input pin (exposure)'),
    (4, 'vent', 'Vent', (T, I), False, 'an opening that lets air through', 'a body part: thermal, and a hole in the ingress seal'),
    (4, 'fan', 'Fan', (T, M), False, 'a fan that moves air through the housing', 'a body part: thermal; held on mechanically'),
    (4, 'cable-gland', 'Cable gland', (I, M, X), True, 'a fitting that lets a cable through a housing wall without opening it to water and dust', 'seals the hole (ingress), grips the cable (mechanical), and is where field wires cross the housing (exposure)'),
    (4, 'battery-bay', 'Battery bay', (M, X, S), True, 'the pocket and contacts that hold the battery', 'holds the cells (mechanical), its contacts are the supply exposure, and it keeps cells away from other parts (electrical-safety)'),
    (5, 'din-rail', 'DIN rail', (M,), False, 'a standard metal rail that devices clip onto in a cabinet', 'a body part: mechanical only'),
    (5, 'rack', 'Rack', (M, T), False, 'a frame that holds devices in a stack', 'a body part: holds devices (mechanical), sets airflow (thermal)'),
    (5, 'wall-box', 'Wall or junction box', (M, I, S, X), True, 'a box fixed to a wall where field wiring meets the device', 'holds the device (mechanical), seals (ingress), isolates mains (electrical-safety), terminals are where field wiring meets it (exposure)'),
    (5, 'outdoor-cabinet', 'Outdoor cabinet', (M, T, I, E, S, X), True, 'a weatherproof cabinet for devices outdoors', 'all of the functions: weather (ingress), sun and cold (thermal), grounding (electrical-safety); field wiring enters it (exposure)'),
    (5, 'vehicle-mount', 'Vehicle mount', (M,), False, 'a fixing for a device in a vehicle', 'a body part: mechanical (vibration, load) only'),
    (5, 'submersible-housing', 'Submersible housing', (M, I, T, S, X), True, 'a sealed housing for use under water (aquaponics, salt water)', 'holds against pressure (mechanical), keeps water out (ingress), sheds heat to the water (thermal), insulation matters (electrical-safety), cables cross through penetrators (exposure)'),
]


def kind_name(level, slug):
    return '%s:%s' % (LEVELS[level], slug)


def rows():
    import json
    out = []
    for level, slug, title, fns, pin, words, why in KINDS:
        assert all(f in FUNCTIONS for f in fns), slug
        out.append({'name': kind_name(level, slug), 'level': LEVELS[level], 'slug': slug, 'title': title, 'level_name': LEVEL_NAMES[level],
                    'functions_json': json.dumps(list(fns)), 'pin_relevant': pin, 'description': words, 'status': 'tentative',
                    'source': SRC if slug != 'test-pad' else 'SYSTEM_HIERARCHY_TERMINOLOGY.md §11.1 (exposure features) + the UNO schematic test pads',
                    'undetermined': 'terminology only: no physics, rating or number is attached to this kind (the Embedded Device slice is not built)',
                    'notes': 'functions reasoned: %s' % why})
    return out
