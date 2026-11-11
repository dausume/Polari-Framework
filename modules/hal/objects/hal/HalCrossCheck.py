"""
@module hal.objects.hal.HalCrossCheck

HalCrossCheck — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HalCrossCheck(treeObject):
    """One comparison of a fact the HAL uses against a second, independent source (hal-0).

    What it is: existing HALs and vendor headers used as CROSS-REFERENCES, never as the model (the user, 2026-11-11). For the
    ATmega328P: avr-libc's register address (I/O space + 0x20) against the data-space address the datasheet prints. For the
    ESP32-C3: the TRM fields were checked field by field against ESP-IDF v5.5.5's soc headers when they were read (rm-2b);
    that recorded check is cited, not re-run. `result` pass | fail | recorded | no-second-source.
    Related concepts: HalBinding (what it checks), HalCodeUnit.
    How it is derived: hal.custom.crosscheck.
    """

    @treeObjectInit
    def __init__(self, name: str = '', unit: str = '', subject: str = '', first: str = '', first_source: str = '', second: str = '', second_source: str = '', result: str = '', why: str = '', notes: str = '', manager=None):
        self.name = name
        self.unit = unit
        self.subject = subject
        self.first = first
        self.first_source = first_source
        self.second = second
        self.second_source = second_source
        self.result = result
        self.why = why
        self.notes = notes
