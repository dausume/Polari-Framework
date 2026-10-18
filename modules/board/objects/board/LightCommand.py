"""
@module board.objects.board.LightCommand

LightCommand — one class per file (design §7). fgm-6a: the backend's ledger of the commands it sent to a v2 light. NOT a wire class
(it never goes to the board): it is what the confirmation logic (board.custom.light_confirm) reads and writes.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class LightCommand(treeObject):
    """What it is: one command a screen (or a person) sent to a light that speaks LightStateV2, and what became of it. The
    answer is read only from the light's own reports: a report that names this command's number, from the same board start it was
    sent into, confirms it. A board that restarted before it answered leaves the command `unknown-resend` (it may or may not have
    been done — send it again); one that stayed silent past the timeout is `unconfirmed`, named, never quietly "done".

    Fields: `light` is the LightStateV2 row; `command_id` the number sent (1..65535, going up by one per backend start, never the
    number the board last answered); `led_on_requested` what was asked; `backend_session` the backend start that minted it;
    `device_session_at_send` the board's boot_session when it was sent; `status` is `pending` | `confirmed` | `rejected-invalid` |
    `rejected-busy` | `unknown-resend` | `unconfirmed`; `result` the board's word (`applied`...); `sent_at` / `resolved_at` UTC
    seconds; `detail` the reason in plain words.

    Related concepts: LightStateV2 (the wire struct whose command_id and last_command_id this correlates).
    """

    @treeObjectInit
    def __init__(self, name: str = '', light: str = '', command_id: int = 0, led_on_requested: bool = False,
                 backend_session: int = 0, device_session_at_send: int = 0, status: str = 'pending', result: str = '',
                 sent_at: float = 0.0, resolved_at: float = 0.0, timeout_s: float = 2.0, detail: str = '', manager=None):
        self.name = name  # '<light>#<backend_session>.<command_id>'
        self.light = light  # the LightStateV2 row's name
        self.command_id = command_id
        self.led_on_requested = led_on_requested
        self.backend_session = backend_session
        self.device_session_at_send = device_session_at_send
        self.status = status
        self.result = result
        self.sent_at = sent_at
        self.resolved_at = resolved_at
        self.timeout_s = timeout_s
        self.detail = detail
