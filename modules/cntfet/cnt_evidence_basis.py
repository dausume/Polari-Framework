"""
@module cntfet.cnt_evidence_basis

EVIDENCE + PROOF-OF-FREEDOM tracking for every FET / cell / route the
cntfet + sifet modules model (Dustin 2026-08-29: "tie in citations
and patents or public domain proof into all of these FETs and cells
… first class information … clickable … establish proof of which
ones are fully free to use").

Evidence is FIRST-CLASS ROWS (EvidenceItem, cnt_states row style):
one row per patent, publication, textbook, standard, licence or
prior-art item, each saying what it PROVES (expired / active /
prior-art-before / public-domain-textbook / open-licence /
proprietary-licence / model-source), whether it was VERIFIED (and
via what), and which records / devices / cells it supports. The
TechnologyIPRecord.evidence_json column (cnt_ip) is a JOIN onto
these names — the proof chain is a lookup, never a re-derivation.

The proof rules are DATA (PROOF_RULES, EXPIRY_RULES, SATISFIES):
    proven-free      every governing record green AND each cites
                     >=1 VERIFIED expired patent, or >=1 VERIFIED
                     dated public-domain / textbook / prior-art item
                     >= 20 years old, or (open-licence records) a
                     VERIFIED open licence; no active-claim item
    free-unverified  green records but evidence unverified or
                     < 20 y old; or an amber record with NO known
                     active claim (unsearched, not encumbered)
    encumbered       any amber/red record with an active-claim item
    unknown          a governing record has no evidence at all

JURISDICTION (Dustin 2026-08-29): UNITED STATES. Every item is US
unless a foreign patent is deliberately cited; 'proven-free' means
proven free in the US; non-US families are out of scope and are
NOT listed as gaps — every payload carries SCOPE_LINE.

DISCLAIMER on every payload: engineering FTO evidence — NOT LEGAL
ADVICE — verify with counsel before commercial use.

@consumers
  - cntfet.cnt_api (GET /api/cntfet/evidence, /evidence/{name},
    /device/{name}/proof, /cell/{cell}/proof, /proof)
  - cntfet.cnt_device_viz_seed (CURVE_BUILDERS 'proof-status';
    SEED_CNT_EVIDENCE_GRAPHS)
  - cntfet.evidence_selftest
  - polariServer (EvidenceItem registration + SEED_EVIDENCE)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt_evidence/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import datetime as _dt
import json
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet import cnt_ip_basis as ip
from cntfet.custom.cnt_citations import TAG_CITATIONS
from cntfet.cnt_power_basis import POWER_CITATIONS
from cntfet.cnt_reference_papers_seed import PAPERS
from cntfet.cnt_taxonomy_basis import TAXONOMY_CITATIONS

from cntfet.objects.cnt_evidence._shared import CITATION_ALIASES, CITATION_ITEMS, CURVE_BUILDERS, DISCLAIMER, EXPIRY_RULES, JURISDICTION, KINDS, PRIOR_ART_YEARS, PROOF_RULES, PROVES, REVIEWED_AT, ROLE_MEANING, ROLE_RULES, SATISFIES, SCOPE_LINE, SEED_BY_NAME, SEED_CNT_EVIDENCE_GRAPHS, SEED_EVIDENCE, SI_CITATIONS, SI_REFINEMENT_CITATIONS, STATUSES, STATUS_INDEX, V_GP, V_XR, _CITED_BY_CLASSES, _ROW_FIELDS, _XREF, _Y_TICKS, _add_years, _alias, _book, _build_proof_status, _cell_keys, _combine, _detail_path, _freedom_proof_core, _gp, _intended_use_of, _iso, _item, _library_proof_core, _lic, _parse, _patent, _pub, _record_status, _role, _row_mentions, _rows, _s, _satisfies, _std, _subject_records, _target, _today, age_years, all_citation_keys, citation_item, device_proof_rows, evidence_detail, evidence_index, evidence_items, expiry_estimate, freedom_proof, item_payload, item_summary, library_proof, proof_rows, provenance_summary, record_evidence, usage_block  # noqa: F401
from cntfet.objects.cnt_evidence.EvidenceItem import EvidenceItem  # noqa: F401
