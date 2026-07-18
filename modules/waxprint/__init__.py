"""waxprint — wax 3D-printer ("magic 3D printer") simulation module.

A pellet-fed auger-screw wax extruder with two independently controlled
thermal zones, modelled end to end: pellets melt through the auger +
hotend zones (auger_melt), a bead is deposited and cools into a print
VOXEL (bead_voxel / voxel_resolution), standard printer movement patterns
are checked for viability (movement_patterns), and the condition vector
is swept across many trials to find the best print recipe subject to the
wax's thermal-safety window (print_optimizer).
"""
