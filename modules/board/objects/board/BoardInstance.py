"""
@module board.objects.board.BoardInstance

BoardInstance — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardInstance(treeObject):
    """What it is: One board OR adapter seen plugged into a host by `pol board detect` (plan §2). Upserted by name
    '<host>:<definition>@<usb path>'. An adapter alone is 'adapter present, target unknown' until a person names the
    target wired to it (`target_board`, brd-fi). Detection never guesses: an unmatched device is listed unadmitted,
    never stored as an instance.
    Related concepts: `BoardDefinition` / `AdapterDefinition` (what it matched), `FirmwareBuild` (what was flashed).
    """

    @treeObjectInit
    def __init__(self, name: str = '', definition: str = '', definition_kind: str = 'board', state: str = '',
                 host: str = '', usb_id: str = '', usb_path: str = '', by_id_path: str = '', port: str = '',
                 serial_number: str = '', matched_by: str = '', target_board: str = '',
                 possible_targets_json: str = '[]', firmware_sha: str = '', last_flash_at: str = '',
                 last_seen_at: str = '', bridge_name: str = '', notes: str = '', manager=None):
        self.name = name
        self.definition = definition  # BoardDefinition or AdapterDefinition name
        self.definition_kind = definition_kind  # board | adapter
        self.state = state  # 'board present' | 'adapter present, target unknown' | ...
        self.host = host  # the device the USB port is on (a topology node)
        self.usb_id = usb_id  # vvvv:pppp
        self.usb_path = usb_path  # bus-port path (identity across replugs on the same port)
        self.by_id_path = by_id_path
        self.port = port  # /dev/tty*
        self.serial_number = serial_number
        self.matched_by = matched_by  # usb-id | by-id-hint
        self.target_board = target_board  # a person's answer (adapter rows)
        self.possible_targets_json = possible_targets_json  # boards whose chain names this adapter (adapter rows)
        self.firmware_sha = firmware_sha
        self.last_flash_at = last_flash_at
        self.last_seen_at = last_seen_at
        self.bridge_name = bridge_name
        self.notes = notes
