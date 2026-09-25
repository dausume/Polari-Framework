"""
@module mathproofs.mathproofs_endpoints
construct_mathproofs_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from mathproofs.mathproofs_api import MathProofsAPI


def construct_mathproofs_endpoints(polServer):
    return MathProofsAPI(polServer=polServer, manager=polServer.manager)
