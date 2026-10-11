"""
@module board.objects.board.LightState

LightState — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class LightState(treeObject):
    """What it is: the state of ONE light on a board and how it last changed — the single struct of the light test
    (a person can turn the light on or off from a Polari screen, and the board's own pushbutton does the same; either way
    the board reports the new state back up). One row per bound board.

    Fields: `led_on` is the light itself AND the command (the same idiom the sim rig's led_on uses): the board reports
    the light's real state in it, and setting it from the screen asks the board to switch the light. `toggles` counts every
    change since the board started; `source` says who made the last change — `command` (the screen) or `button` (the
    pushbutton on the board); `seq` counts the frames the board has sent; `boot_session` is a number the board picks anew
    each time it starts, so a restart is never mistaken for a lost frame; `status` is `idle` until the light first changes,
    then `active`.

    Related concepts: ButtonClockState (the bigger clock-and-button sample this replaces as the demo); SimRigState (whose
    led_on works the same way).
    """

    @treeObjectInit
    def __init__(self, name: str = '', seq: int = 0, boot_session: int = 0, led_on: bool = False, toggles: int = 0,
                 source: str = '', status: str = '', manager=None):
        self.name = name  # the Push match key (RIG_NAME of the firmware)
        self.seq = seq  # wire frame counter
        self.boot_session = boot_session  # picked anew at every board start
        self.led_on = led_on  # the light (D6): reported by the board; set by a person to switch it
        self.toggles = toggles  # changes since the board started
        self.source = source  # command | button — who made the last change
        self.status = status  # idle | active
