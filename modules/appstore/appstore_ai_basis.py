"""
@module appstore.appstore_ai_basis

ai-0: AI tools as FIRST-CLASS store citizens (AI_TOOL_LINKAGES_PLAN
decisions 1-6). An AiToolDefinition row says WHAT an AI tool is
(hosting kind, API family), WHICH Polari seams it can plug into
(its linkage claims, each honestly `proven` or `feasible`), and its
sovereignty facts (internet_required / data_leaves_isle) — never
whether it is ready RIGHT NOW: live readiness joins at read time
from the managed reasoning config (appstore_ai_api).

The linkage vocabulary is CODE (tracked), like PROVIDER_REGISTRY:
each kind names its CONSUMER (the Polari seam/knob it wires) and
whether that seam exists today (`live`) or is a planned wire
(`unbuilt`) — feasibility claims are honest, never implied working.

@consumers
  - appstore.appstore_ai_api (/api/appstore/ai-tools)
  - islemesh.islemesh_catalog (ai-2: the derived store section)
  - polariServer defClassList (table + CRUDE)
  - appstore.appstore_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/appstore_ai/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from appstore.objects.appstore_ai._shared import AI_LINKAGES, API_FAMILIES, CLOUD_HOSTING_OPTIONS, HOSTING_KINDS, LINKAGE_STATUSES, host_check, tool_report  # noqa: F401
from appstore.objects.appstore_ai.AiToolDefinition import AiToolDefinition  # noqa: F401
