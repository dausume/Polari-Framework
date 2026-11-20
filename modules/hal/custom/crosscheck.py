"""
@module hal.custom.crosscheck

EXISTING HALs AS CROSS-REFERENCES (hal-0; the user 2026-11-11: "we can use existing ones as a cross reference"). For each
binding of a unit, one HalCrossCheck row per fact a second, independent source also states:

  atmega328p  register address: avr-libc's <avr/io.h> (the snapshot, I/O address + 0x20 for I/O space) against the data-space
              address the datasheet prints beside the register (board.custom.register_fields_atmega328p.REGISTER_CITES).
              Two different documents, compared here on every read.
  esp32c3     every field's position was checked against ESP-IDF v5.5.5 components/soc/esp32c3/register/soc/*.h when it was read
              (rm-2b, board.custom.registers_esp32c3's docstring). That RECORDED check is cited, not re-run (the IDF headers are not
              in this repo).

Planned second sources (hal-2): ArduinoCore-avr variants/standard/pins_arduino.h (board pin -> port / bit / timer / PCINT) and
ESP-IDF soc/gpio_reg.h addresses, both read into committed, cited snapshots.
"""
from hal.custom import soc_rules as SR


def checks(res):
    """One HalCrossCheck row per binding that the chip's provider can check against a second source (provider 'crosscheck'); a chip
    with no second source gets none (said by the absence, never by another chip's rule)."""
    u = res['unit'] or {}
    soc = u.get('soc')
    if soc not in SR.PROVIDERS:
        return []
    fn = SR.PROVIDERS[soc].get('crosscheck')
    return [r for r in (fn(u, b) for b in res['bindings']) if r] if fn else []
