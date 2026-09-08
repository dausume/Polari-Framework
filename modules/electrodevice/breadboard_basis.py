"""
@module electrodevice.breadboard_basis

ncg-5: the BREADBOARD level — the circuit-diagram no-code humans
physically recognize. A board's connectivity IS its netlist: every
tie-point row is one net (left/right of the center trench are
separate strips), the power rails run the board's length, and a
placed component's pins land ON tie points instead of abstract nets.
Larger circuits = MORE BOARDS: BoardJumper rows join nets across
boards, and a populated board can re-wrap as a .subckt with named
external pins — the circuit-world mirror of SolutionInvocation
(board-as-component).

Tie-point grammar (tiepoints_json entries):
  'r<N>L' / 'r<N>R'  row N, left/right of the trench
  'vplus' / 'gnd'    the power rails ('gnd' is SPICE ground 0)

MCU and FPGA pins need no special kind at this level: a driven pin
IS a voltage source placement ('vsource'); ncg-6 binds those sources
to a LogicBlockDesign's evaluated outputs.

@consumers
  - electrodevice.breadboard_netlist_seed (connectivity compiler)
  - polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/breadboard/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from electrodevice.objects.breadboard._shared import SEED_BREADBOARDS, SEED_JUMPERS, SEED_PLACEMENTS  # noqa: F401
from electrodevice.objects.breadboard.BreadboardDefinition import BreadboardDefinition  # noqa: F401
from electrodevice.objects.breadboard.ComponentPlacement import ComponentPlacement  # noqa: F401
from electrodevice.objects.breadboard.BoardJumper import BoardJumper  # noqa: F401
