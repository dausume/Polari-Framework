"""
ClockPeer - one class per file (design section 7); cfg-1 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The clock group in detail": peer rows).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ClockPeer(treeObject):
    """What it is: THE FAR END OF A SERIAL LINK AND ITS CLOCK - who the chip talks to over its USART and how that side times its bits: the UNO's
    ATmega16U2 running arduino-usbserial (its own 16 MHz crystal, U2X1 = 1 and UBRR1 by SERIAL_2X_UBBRVAL - board.custom.clock_skew_run.peer_divisor), an
    ideal 'exact' peer (a knob: no error at all), a USB-serial adapter by its datasheet, or another of our boards. The clock group's serial-link check
    takes the peer's divisor and clock error with the chip's own to say in which band both directions still decode.
    Related concepts: `ClockSource` (the peer's clock when it has a row), `BoardDefinition` (the board whose link this is), cmod `ConfigOption`.
    """
    plain_words = ('A clock peer is the other end of a serial line - the chip that listens and answers - and how it times its bits, so a link can '
                   'be judged from both sides, not just from the chip we program.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'usb-serial-chip', boards: str = '', clock: str = '', f_hz: float = 0.0,
                 divisor_rule: str = '', error_pct: float = 0.0, undetermined: str = '', source: str = '', notes: str = '', manager=None):
        self.name = name                  # e.g. 'uno-16u2-usbserial'
        self.title = title
        self.kind = kind                  # usb-serial-chip | exact | adapter | board
        self.boards = boards              # comma-separated BoardDefinition names whose USB link this peer is
        self.clock = clock                # a ClockSource name, or '' (exact / undetermined)
        self.f_hz = f_hz                  # the peer's clock, nominal
        self.divisor_rule = divisor_rule  # how it picks its divisor: 'arduino-usbserial' (clock_skew_run.peer_divisor) | 'exact' | 'datasheet'
        self.error_pct = error_pct        # its clock error at nominal (%): 0 for a crystal at 25 C; a knob for an adapter until its datasheet is read
        self.undetermined = undetermined  # what is not known about it, in words ('' = fully determined)
        self.source = source
        self.notes = notes
