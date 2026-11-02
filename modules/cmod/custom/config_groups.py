"""
@module cmod.custom.config_groups

cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The words"): THE CODE-OWNED CATALOGUE of variable groups, verdicts and option levels - the words every
other configuration file reads, kept in one place so they are learned once.

  GROUPS    group -> {title, family, plain}: how a catom's variables are grouped on its page and which checks judge them. `family` is the catom
            hal_contract family it lines up with ('' for the groups the contracts do not have yet: clock, power, memory, rf).
  VERDICTS  invalid < compromise < ideal (the order is the ranking: an ideal option always ranks above a compromise)
  LEVELS    how deep an option's change goes: values (the code stays) < isotope (the code changes) < part < module-board < board
  LAYERS    the check layers, cheapest first: 1 closed form, 2 derived range, 3 simulation
"""

GROUPS = {
    'clock': {'title': 'Clock', 'family': '', 'plain': 'the clock and everything timed from it: serial speed, the tick, PWM frequency, the ADC clock'},
    'signal': {'title': 'Signal', 'family': 'signal', 'plain': 'whether a signal is read right at the other end: levels, thresholds, bus speed'},
    'drive': {'title': 'Drive', 'family': 'drive', 'plain': 'whether a pin can supply what is connected to it: current, pulls, series resistors'},
    'analog': {'title': 'Analog', 'family': 'register', 'plain': 'the ADC: its reference, prescaler, source impedance and thresholds'},
    'timing': {'title': 'Timing', 'family': 'execution', 'plain': 'when code runs: debounce windows, interrupt or poll, loop period against event rates'},
    'protocol': {'title': 'Protocol', 'family': 'protocol', 'plain': 'the shape of what is sent: frame layout, stop bits, message rates'},
    'power': {'title': 'Power', 'family': '', 'plain': 'the supply: regulator load, brown-out level, sleep modes'},
    'memory': {'title': 'Memory', 'family': '', 'plain': 'whether the chosen isotopes and values fit in flash and RAM'},
    'rf': {'title': 'Radio', 'family': '', 'plain': 'band, power and duty cycle against what the region permits'},
}

VERDICTS = ('invalid', 'compromise', 'ideal')
LEVELS = ('values', 'isotope', 'part', 'module-board', 'board')
LAYERS = {1: 'closed form', 2: 'derived range', 3: 'simulation'}


def rank(verdict):
    """invalid 0, compromise 1, ideal 2 (unknown words rank as invalid: never trusted)."""
    return VERDICTS.index(verdict) if verdict in VERDICTS else 0
