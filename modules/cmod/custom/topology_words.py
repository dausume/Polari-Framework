"""
@module cmod.custom.topology_words

bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2): THE WORDS of the Hardware Event topology, in one place, each with its plain meaning, so the
pages and the doors say the same thing. Nothing here computes.
"""
NODE_KINDS = {
    'root': 'plugged in: the hardware as delivered, its USB in the bridge host; powered, enumerated, the bootloader answering; no structs yet',
    'flashed': 'the firmware is on the chip: the flash tool verified the hex, and its sha256 is the Firmware Solution\'s build',
    'boot': 'reset after the flash, the HAL\'s init done: the pin modes set, every struct at its init value',
    'state': 'a state a person or an AI defined: requirements on named struct fields, met together',
}
EDGE_KINDS = {
    'flash': 'the USB flashes the firmware until the flash tool\'s verify completes',
    'init': 'reset, then the firmware\'s init runs',
    'trigger': 'a Hardware Event starts it: an actuation or an external signal',
    'cascade': 'no outside trigger: the previous node\'s change makes code run that produces the next',
}
REQUIREMENT_KINDS = {
    'exact': 'the field equals this value',
    'range': 'the field is inside lo..hi (inclusive)',
    'set': 'the field is one of these values (comma-separated)',
    'written': 'the field was written during the edge (its value is not judged)',
}
EVENT_KINDS = {'actuation': 'a sensor or trigger change a person, the environment or time can cause',
               'external-signal': 'something received from outside the boards: a command through a bridge, a frame from another board or a harness, a message'}
EVENT_SOURCES = ('person', 'environment', 'time', 'polari', 'board', 'harness', 'network')
COLLATERAL_KINDS = {'pin-level': 'a pin\'s logic level (the twin\'s pin trace)', 'net-current': 'a net\'s current (ngspice)',
                    'temperature': 'a part\'s temperature rise (the Cauer ladder)', 'frame': 'a frame\'s bytes on the wire', 'timing': 'the time from the edge\'s start to the change'}
ENGINES = ('twin', 'ngspice', 'cauer', 'scope')
STEP_KINDS = {
    'cycle': 'one CPU clock cycle: 1 / f_clk',
    'loop-period': 'one pass of the main loop, measured on the twin (the poll period)',
    'bit-time': 'one UART bit at the link\'s actual rate',
    'pwm-period': 'one PWM period',
    'adc-conversion': 'one ADC conversion (13 ADC clocks on the ATmega328P)',
    'bus-transaction': 'one bus transaction (I2C / SPI / 1-Wire)',
    'knob': 'no derived or cited number yet: a labelled knob',
}
STEP_BASES = ('derived', 'cited', 'knob', 'person')
NODE_BASES = {'person': 'defined by a person', 'ai': 'defined by an AI through the doors', 'proposed': 'proposed from a run that diverged: the reached values; dashed and unnamed until accepted'}
CHECK_KINDS = {'timing': 'the edge reaches its node within bound_s of its stimulus', 'field-tolerance': 'a field ends within value +/- tolerance', 'field-range': 'a field ends within lo..hi'}
CONFIRMATION_BY = {'twin': 'a simulated run met the requirements with every check passing', 'hardware': 'a record from a real board met the requirements', 'person': 'attested in words'}
RUN_OUTCOMES = ('reached', 'checks-failed', 'not-reached', 'diverged', 'blocked')
SAMPLE_KINDS = {'enumerable': 'every value the field can take is listed', 'samples': 'the field cannot be enumerated; these are the declared test values'}
