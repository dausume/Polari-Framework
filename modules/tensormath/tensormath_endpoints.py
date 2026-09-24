"""
@module tensormath.tensormath_endpoints
construct_tensormath_endpoints(polServer) — the endpoint constructor (manifest `endpoints`); admission calls it once.
"""
from tensormath.tensormath_api import TensorMathAPI


def construct_tensormath_endpoints(polServer):
    return TensorMathAPI(polServer=polServer, manager=polServer.manager)
