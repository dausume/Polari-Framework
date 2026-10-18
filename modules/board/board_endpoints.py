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
from board.config_events_api import ConfigEventsAPI   # pv-4
from board.register_profile_api import RegisterProfileAPI
from board.profile_overlap_api import ProfileOverlapAPI   # pp-1
from board.custom import light_confirm   # noqa: F401  fgm-6a: registers the LightStateV2 frame observer (command confirmation)


def construct_board_endpoints(polServer):
    api = BoardAPI(polServer=polServer, manager=polServer.manager)
    api.installer = BoardInstallerAPI(polServer=polServer, manager=polServer.manager)
    api.board_object = BoardObjectAPI(polServer=polServer, manager=polServer.manager)   # brd-bo: /api/board/{board}/pins|views|conflicts|render|ingest
    api.pin_view = PinViewAPI(polServer=polServer, manager=polServer.manager)   # pv-0: /api/board/{board}/pin-view[/pins|/connections|/surfaces]
    api.config_events = ConfigEventsAPI(polServer=polServer, manager=polServer.manager)   # pv-4: /api/board/{board}/config-events (GET timeline, POST record)
    api.register_profile = RegisterProfileAPI(polServer=polServer, manager=polServer.manager)   # rp-0: /api/board/socs/{soc}/register-profile|memory-map
    api.profile_overlap = ProfileOverlapAPI(polServer=polServer, manager=polServer.manager)   # pp-1: /api/board/socs/{soc}/profile-overlap
    return api
