"""
@module electrodevice.objects.layout.WireColorScheme

Row class WireColorScheme of the electrodevice module (lay-0) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class WireColorScheme(treeObject):
    """What it is: the wire colour CONVENTION of a bench — which colour a wire is by what it carries. `colors_json` maps a key to a colour NAME:
    `power` (5 V and other supply wires), `ground`, one key per pin-view signal family (gpio, pwm-timer, analog, uart, spi, i2c, interrupt, usb, clock,
    reset-programming) and `default`. The seeded scheme follows the pin view (power red, ground black, each signal family the colour the pin view paints it);
    a seeded scheme is never edited in place — COPY it (`copy_of`), then change the copy, as with score profiles. A single wire can still carry its own colour
    (a per-wire override kept beside the derived colour).
    Related concepts: `BoardJumper.colour_override` (one wire's own colour), `LayoutEdit` (a person's override on a build), the pin view's family tokens.
    """

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '', description: str = '', colors_json: str = '{}',
                 seeded: bool = False, copy_of: str = '', follows: str = '', notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name or name
        self.description = description
        self.colors_json = colors_json    # {"power": "red", "ground": "black", "pwm-timer": "orange", ...}
        self.seeded = seeded              # True = code-owned, copy before editing
        self.copy_of = copy_of            # the scheme this one was copied from
        self.follows = follows            # what the colours are derived from (the pin view's palette source)
        self.notes = notes
