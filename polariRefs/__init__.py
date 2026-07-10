"""
@module polariRefs

xsim-1: ONE reference type, ONE resolution ladder (design pillar 1 of
CROSS_INSTANCE_SIM_PLAN.md). The same lazy objectRef serves local-tree,
demoted-to-DB (residency, later), shared-DB cross-instance (xsim-3) and
remote-API (xsim-6) objects — never two proxy systems.

Bare refs ({kind:'objectRef', className, name, path}) stay valid forever
and mean "local"; the optional `authority` coordinate
({instance: 'b'} | {module: 'materialsScience'}) and optional
`schemaVersion` extend the SAME shape.

Layout ([[file-size-decomposition]]):
    ref_format.py    — parse/normalize + authority keys + schema versions
    identity_map.py  — (authority, className, id)-keyed weakref map
    resolver.py      — the resolution ladder's local rungs + honest
                       refusals for the not-yet-built remote rungs
    selftest_refs.py — python3 -m polariRefs.selftest_refs
"""
