"""
@module grpcbridge.hosted_basis

sim-2: hosted bridges as DATA - one HostedBridge row per generated bridge running beside a twin session on the bridge-engines worker. Observed, never seeded
(a bridge is started, not shipped). The class lives under objects/hosted/; this file re-exports it.

@consumers
  - grpcbridge.custom.hosted_bridges (the start / list / stop logic)
  - grpcbridge.hosted_bridges_api (the doors)
"""
from grpcbridge.objects.hosted.HostedBridge import HostedBridge  # noqa: F401
