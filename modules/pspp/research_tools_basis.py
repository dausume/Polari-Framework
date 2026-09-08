"""
@module pspp.research_tools_basis

mtt-2 RESEARCH TOOLS — the instruments a community builds to SEE what
its materials, food, water and soil are doing. The measurement half of
the open-source economy: manufacturing tools MAKE, research tools
MEASURE. Each is a ResearchTool row a maker can build, with its parts
(reusing the accessibility tiers), difficulty, safety and the plain
reason it matters.

Seeded from Dustin's asks (open-source FTIR, a red-cabbage pH detector,
a fruit/vegetable sugar test) plus the highest-leverage additions for
this project's domains (materials / food / water / carbon):
  - a VISIBLE spectrometer (DVD grating + webcam) — the accessible
    cousin of FTIR that turns any colour assay quantitative;
  - an EC/TDS meter — dissolved minerals in water + soil (hydroponics);
  - a colorimeter — single-wavelength assays (nitrate, phosphate…);
  - a thermocouple logger — measures furnace temperature, the tool
    that lets you actually CLIMB the manufacturing furnace ladder;
  - a turbidity meter + a DIY microscope.

Honesty: difficulty + safety are cited-approximate judgements; where a
tool only CORRELATES with what a user wants (Brix vs "nutrient
density"), the row says so — a correlation, never a proof.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.pspp_api (/api/pspp/research-tools)
  - pspp.research_tools_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/research_tools/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from pspp.solgel_sourcing_basis import ACCESSIBILITY_TIERS, _tier_rank

from pspp.objects.research_tools._shared import BUILD_DIFFICULTY, SEED_RESEARCH_TOOLS, TOOL_DOMAINS, _RT, _RT_PROV, _parts, _row, research_tools, tool_dict, validate_tools  # noqa: F401
from pspp.objects.research_tools.ResearchTool import ResearchTool  # noqa: F401
