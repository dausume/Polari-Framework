"""@module composition.objects.interface._shared — what the interface row classes share (constants, seeds, helpers); split from interface_basis.py (sap-2c)."""

DOF_AXES = ('tx', 'ty', 'tz', 'rx', 'ry', 'rz')
#: 'monolithic' (one pour / one print — promotion happened in the
#: mould) and 'magnetic' (Gridfinity cell seating, mech) added mxc-2 to
#: end the vocabulary drift noted in MECH_FREECAD_INTERCHANGE_PLAN
#: §9.1: motors/m1_composition_seed.py (ifm1-poles-core, ifm1-teeth-
#: yoke) already wrote 'monolithic' outside this tuple, and this entry
#: heals that seed without touching motors. Data only:
#: InterfaceDefinition does not validate against this tuple (it never
#: did), so nothing refused those rows before and nothing changes
#: behaviour now.
RETENTION_SCHEMES = ('snap', 'groove', 'fastener', 'adhesive',
                     'mortar', 'press', 'wound', 'monolithic',
                     'magnetic', 'none')
