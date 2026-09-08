"""
@module cntfet.cnt_ip_basis

IP / licensing / freedom-to-operate (FTO) TRACKING for the FET +
cell + silicon technologies the cntfet / sifet modules model —
as ROWS, in the cnt_states style: every technology the suite
simulates or proposes to build carries a TechnologyIPRecord saying
what kind of IP governs it, the verdict, WHY, and what "I make my
own" changes (usually: nothing about an active patent — a patent
covers make/use/sell, 35 U.S.C. §271(a); own manufacture IS
"making").

DISCLAIMER (carried on every payload as `disclaimer`):
  ENGINEERING FTO RECORD — NOT LEGAL ADVICE — verify with counsel
  before commercial use.

Verdict vocabulary mirrors the suite's licence gates
(AI-Notes/evaluations/*LICENSE_GATE.md): green = proceed
(incorporate / build); amber = proceed for research, verify before
commercial use; red = blocker (NC / active claim squarely on the
thing / GPL-incompatible). Project licence: GPLv3; NC = hard
blocker; adopted upstreams are FORKED under dausume/ pins.

Patent expiry rule used for `expiry_est`: US utility patents filed
on/after 1995-06-08 expire 20 years from the EARLIEST non-provisional
filing date (plus PTA, ignored here); patents filed before that
expire at the later of 17 years from grant or 20 years from filing
(1960s patents: long expired either way). Maintenance-fee lapses
("Expired - Fee Related") make a patent unenforceable EARLIER —
recorded as status 'lapsed' with the fetched date.

`confidence`: 'verified' = number, title, assignee, filing date and
status fetched from Google Patents / USPTO on reviewed_at;
'partially-verified' = number+title verified, dates/claims from
secondary sources; 'unverified' = representative claim NOT checked —
`verify_next` says what to search.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/ip, /device/{name}/ip)
  - cntfet.cnt_device_viz_seed (CURVE_BUILDERS 'ip-verdicts';
    SEED_CNT_IP_GRAPHS)
  - cntfet.ip_selftest
  - polariServer (TechnologyIPRecord registration + SEED_TECHNOLOGY_IP)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_ip/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.cnt_taxonomy_basis import shape_of

from cntfet.objects.cnt_ip._shared import CELL_EXTRA_RECORDS, CURVE_BUILDERS, DISCLAIMER, INTENDED_USE, INTENDED_USE_MEANING, IP_KINDS, MAKE_YOUR_OWN_RULE, REVIEWED_AT, SEED_BY_NAME, SEED_CNT_IP_GRAPHS, SEED_TECHNOLOGY_IP, SHAPE_RECORDS, STEP_RECORDS, SUBJECT_KINDS, VERDICT_GATE, VERDICT_RANK, _OWN_CODE, _OWN_MAKE_ACTIVE, _OWN_MAKE_EXPIRED, _ROW_FIELDS, _build_ip_verdicts, _dielectric_row, _find_device, _pat, _rec, _rows_from_manager, _self_manufacture_answer, _summarise, cell_ip_report, device_ip_report, ip_gate, ip_records, ip_verdict_rows, library_ip_report, record_payload, route_ip_report, subjects_for_cell, subjects_for_device, worst_verdict  # noqa: F401
from cntfet.objects.cnt_ip.TechnologyIPRecord import TechnologyIPRecord  # noqa: F401
