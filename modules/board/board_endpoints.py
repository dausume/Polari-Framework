"""
@module board.board_endpoints
construct_board_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from board.board_api import BoardAPI


def construct_board_endpoints(polServer):
    return BoardAPI(polServer=polServer, manager=polServer.manager)
