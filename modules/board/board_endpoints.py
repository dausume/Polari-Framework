"""
@module board.board_endpoints
construct_board_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
brd-fi: the firmware installer's doors (board.installer_api) are constructed beside the board API; brd-bo: the board object's
(board.board_object_api).
"""
from board.board_api import BoardAPI
from board.installer_api import BoardInstallerAPI
from board.board_object_api import BoardObjectAPI
from board.pin_view_api import PinViewAPI
from board.chip_ladder_api import ChipLadderAPI   # chp-0
from board.bench_api import BenchAPI   # bench-0
from board.config_events_api import ConfigEventsAPI   # pv-4
from board.board_twins_api import BoardTwinsAPI   # sim-1
from board.register_profile_api import RegisterProfileAPI
from board.profile_overlap_api import ProfileOverlapAPI   # pp-1
from board.maintenance_api import MaintenanceAPI   # c3-derive: retire stored rows the code now derives
from board.firmware_state_api import FirmwareStateAPI   # fst-1: /api/firmware-state/{config}[/fields|/enums|/findings|/live]
from board.custom import light_confirm   # noqa: F401  fgm-6a: registers the LightStateV2 frame observer (command confirmation)


def construct_board_endpoints(polServer):
    api = BoardAPI(polServer=polServer, manager=polServer.manager)
    api.installer = BoardInstallerAPI(polServer=polServer, manager=polServer.manager)
    api.board_object = BoardObjectAPI(polServer=polServer, manager=polServer.manager)   # brd-bo: /api/board/{board}/pins|views|conflicts|render|ingest
    api.pin_view = PinViewAPI(polServer=polServer, manager=polServer.manager)   # pv-0: /api/board/{board}/pin-view[/pins|/connections|/surfaces]
    api.chip_ladder = ChipLadderAPI(polServer=polServer, manager=polServer.manager)   # chp-0: /api/board/chip-ladder[/levels|/emulators]
    api.bench = BenchAPI(polServer=polServer, manager=polServer.manager)   # bench-0: /api/board/benches[...], /api/board/bench-options/...
    api.config_events = ConfigEventsAPI(polServer=polServer, manager=polServer.manager)   # pv-4: /api/board/{board}/config-events (GET timeline, POST record)
    api.twins = BoardTwinsAPI(polServer=polServer, manager=polServer.manager)   # sim-1: /api/board/twins (+ /{name}, /inject, /events): twin sessions
    api.register_profile = RegisterProfileAPI(polServer=polServer, manager=polServer.manager)   # rp-0: /api/board/socs/{soc}/register-profile|memory-map
    api.profile_overlap = ProfileOverlapAPI(polServer=polServer, manager=polServer.manager)   # pp-1: /api/board/socs/{soc}/profile-overlap
    api.maintenance = MaintenanceAPI(polServer=polServer, manager=polServer.manager)   # c3-derive: /api/board/maintenance/retire-derived-rows
    api.firmware_state = FirmwareStateAPI(polServer=polServer, manager=polServer.manager)   # fst-1: a firmware's state objects, derived
    return api
