"""
@module board.objects.board.FirmwareVariant

FirmwareVariant — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FirmwareVariant(treeObject):
    """What it is: A named firmware RECIPE over a board's template (brd-fi, plan §7a): which app of the template it
    runs, which classes it speaks (each gets its generated header), which features are compiled in (LED / PWM / ADC /
    commands), its knobs (telemetry Hz, LED pin, PWM pin, ADC channel, the TMP36 formula or the raw ADC count, blink
    period, rig name, device id) and extra build defines. `pol board gen uno --variant <name>` renders it into a
    project → a FirmwareBuild row. The point (his words): "test different kinds of things on the arduino uno to see
    if it works" — each variant is one such thing, with what to watch for when it runs.
    Related concepts: `FirmwareBuild.variant`, `BoardDefinition`, the per-class packet headers (c_twin).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board_definition: str = '', title: str = '', purpose: str = '', app: str = '',
                 classes_json: str = '[]', features_json: str = '{}', knobs_json: str = '{}', build_flags_json: str = '[]',
                 what_to_watch: str = '', twin_stimulus_json: str = '{}', origin: str = 'seeded', notes: str = '',
                 manager=None):
        self.name = name  # uno-sim-rig | uno-blink-only | uno-adc-sweep | uno-echo | a person's own
        self.board_definition = board_definition
        self.title = title
        self.purpose = purpose  # what it tests, in plain words
        self.app = app  # the template app copied as main.c: sim_rig | blink | analog | echo
        self.classes_json = classes_json  # ordered class list (order = msg_type)
        self.features_json = features_json  # {led, pwm, adc, commands}
        self.knobs_json = knobs_json  # {telemetry_hz, led_pin, pwm_pin, adc_channel, temp_formula, blink_ms, rig_name, device_id, usart_u2x}
        self.build_flags_json = build_flags_json  # extra NAME=number defines rendered into board_config.h
        self.what_to_watch = what_to_watch  # the effect to look for once it runs
        self.twin_stimulus_json = twin_stimulus_json  # what the simavr twin drives (adc0_mv, adc_mv per channel)
        self.origin = origin  # seeded | person
        self.notes = notes
