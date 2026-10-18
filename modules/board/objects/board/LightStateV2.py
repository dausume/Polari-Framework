"""
@module board.objects.board.LightStateV2

LightStateV2 — one class per file (design §7). fgm-6a (FIRMWARE_GENERATION_MODULE_PLAN.md §10): the light test's wire struct
WITH command confirmation, built as a NEW class beside LightState (v1 stays pinned, the default and byte-identical).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class LightStateV2(treeObject):
    """What it is: the state of ONE light on a board, like LightState, plus the board's answer to the last command a screen sent
    it. The screen asks for a change with a COMMAND NUMBER (`command_id`); the board does (or refuses) it and says in every report
    which command it last answered (`last_command_id`) and how it went (`last_command_result`). A command counts as done only when
    a report names its number from the same board start (`boot_session`) it was sent into — a restart in between means "not known,
    send again", never "done". A press of the board's own button changes the light but leaves the last answered command alone.

    Fields: `led_on` is the light itself AND the command (the screen sets it to ask the board to switch the light). `command_id`
    is what the screen sent (0 = never; a number from 1 to 65535 the sender picks, going up by one per command); the board does
    not report it. `last_command_id` is the number of the last command the board answered (0 = none since it started) and
    `last_command_result` says how: `applied`, `rejected-invalid` (the command was malformed: no number, no light value) or
    `rejected-busy` (the board could not take it now). `toggles` counts every change since the board started; `source` says who
    made the last change (`command` or `button`); `seq` counts the reports the board has sent; `boot_session` is a number the
    board picks anew at each start; `status` is `idle` until the light first changes, then `active`.

    Related concepts: LightState (the original, which has no command numbers); LightCommand (one row per command sent: the
    backend's record of whether it was confirmed).
    """

    @treeObjectInit
    def __init__(self, name: str = '', seq: int = 0, boot_session: int = 0, led_on: bool = False, toggles: int = 0,
                 source: str = '', status: str = '', command_id: int = 0, last_command_id: int = 0,
                 last_command_result: str = '', manager=None):
        self.name = name  # the Push match key (RIG_NAME of the firmware)
        self.seq = seq  # wire frame counter
        self.boot_session = boot_session  # picked anew at every board start
        self.led_on = led_on  # the light (D6): reported by the board; set by a person to switch it
        self.toggles = toggles  # changes since the board started
        self.source = source  # command | button — who made the last change
        self.status = status  # idle | active
        self.command_id = command_id  # DOWN only: the number of the command being sent (1..65535, 0 = none)
        self.last_command_id = last_command_id  # UP: the number of the last command the board answered (0 = none since start)
        self.last_command_result = last_command_result  # UP: applied | rejected-invalid | rejected-busy
