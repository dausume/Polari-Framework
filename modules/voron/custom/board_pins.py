"""
@module voron.custom.board_pins

The REFERENCE pin maps printer_cfg renders from — the Voron project's own
Klipper configurations (Voron-2 / Voron-Trident `firmware/klipper_configurations/
Octopus/*.cfg`, BTT's EBB36/EBB42 sample config). They are the documented
defaults for those boards, NOT a measurement of anyone's wiring: every
rendered section carries a "MUST be checked" comment. A board model with no
map here is a named refusal in printer_cfg, never a guess.
"""

#: BTT Octopus 1.1 — main board (motor slots 0..7 in the Voron reference order)
OCTOPUS_11 = {
    'stepper_x': {'step': 'PF13', 'dir': 'PF12', 'enable': '!PF14', 'uart': 'PC4', 'endstop': 'PG6'},
    'stepper_y': {'step': 'PG0', 'dir': 'PG1', 'enable': '!PF15', 'uart': 'PD11', 'endstop': 'PG9'},
    'stepper_z': {'step': 'PF11', 'dir': 'PG3', 'enable': '!PG5', 'uart': 'PC6', 'endstop': 'PG10'},
    'stepper_z1': {'step': 'PG4', 'dir': '!PC1', 'enable': '!PA0', 'uart': 'PC7'},
    'stepper_z2': {'step': 'PF9', 'dir': 'PF10', 'enable': '!PG2', 'uart': 'PF2'},
    'stepper_z3': {'step': 'PC13', 'dir': '!PF0', 'enable': '!PF1', 'uart': 'PE4'},
    # toolhead wired straight to the main board (no toolhead board)
    'extruder': {'step': 'PE2', 'dir': 'PE3', 'enable': '!PD4', 'uart': 'PE1', 'heater': 'PA2', 'sensor': 'PF4'},
    'probe': '^PG15',
    'part_fan': 'PA8', 'hotend_fan': 'PE5',
    'heater_bed': {'heater': 'PA3', 'sensor': 'PF3'},
    'controller_fan': 'PD12',
}

#: BTT EBB36 / EBB42 (pin-compatible) — toolhead board; pins are prefixed with the board's mcu_name
EBB36 = {
    'extruder': {'step': 'PD0', 'dir': 'PD1', 'enable': '!PD2', 'uart': 'PA15', 'heater': 'PB13', 'sensor': 'PA3'},
    'probe': '^PB6',
    'part_fan': 'PA0', 'hotend_fan': 'PA1',
}

MAIN_BOARD_PINS = {'btt-octopus-1.1': OCTOPUS_11}
TOOLHEAD_BOARD_PINS = {'btt-ebb36': EBB36, 'btt-ebb42': EBB36}

#: how many Z steppers each model drives (2.4: flying gantry on four; Trident: bed on three; V0/equivalent: one)
Z_STEPPERS = {'voron-2.4': 4, 'voron-trident': 3, 'voron-0': 1, 'equivalent-corexy': 1}
