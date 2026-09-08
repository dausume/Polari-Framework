"""
@cross-cutting
@module techtree.techtree_basis
@tags @xc:bindings

Tech Tree as data (tt-3, TECH_TREE_TOPOLOGY_PLAN Part B): a tech
tree is an EXPANSION of topology — the same node-logic graph where
the rectangular containers are TECHNOLOGIES instead of Polari
containers. Each technology carries up to four SEGMENTS (theory /
real / business / politics), filled by assignments that reference
modules (theory) or the tt-6 content objects (real / business /
politics). Completion is DERIVED — segments_present and
completion_level are computed by techtree_analysis, never hand-set
(the drift/observation idiom).

A complete baseline tree = the Open Source Economic Baseline (OSEB)
— the overall end goal of the whole Polari project.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - techtree.custom.techtree_analysis / techtree.techtree_api
  - polari-platform-angular tech-tree render mode (tt-4)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/techtree/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from techtree.objects.techtree._shared import SEGMENT_COLORS, SEGMENT_KINDS  # noqa: F401
from techtree.objects.techtree.TechTreeDefinition import TechTreeDefinition  # noqa: F401
from techtree.objects.techtree.TechNode import TechNode  # noqa: F401
from techtree.objects.techtree.TechSegment import TechSegment  # noqa: F401
from techtree.objects.techtree.TechSegmentAssignment import TechSegmentAssignment  # noqa: F401
from techtree.objects.techtree.TechDependencyEdge import TechDependencyEdge  # noqa: F401
