"""
@module security

Security — the App / Network / OS taxonomy as rows, every protecting system with its provenance (stock docker,
qemu, Polari) and state per scenario, and THREE security topology views with reach simulations
(SECURITY_INTERFACES_PLAN sec-i-0/1; his ask 2026-09-12: topology-based simulations that show what is being
protected, how, via what system, and who gets access through what means — one view per domain).
Requires nothing from other feature modules; reads os-security/scenarios when the suite tree is beside the
checkout, else its embedded mirror.
"""
from security.security_basis import SECURITY_CLASSES, SecurityArea, SecurityControl, SecurityDomain, SecurityScenario, SecurityThreat, SecurityTopologyEdge, SecurityTopologyNode  # noqa: F401
from security.security_seed import SECURITY_SEED_PAIRS  # noqa: F401
from security.security_page import SEED_SECURITY_PAGE_DISPLAYS  # noqa: F401
