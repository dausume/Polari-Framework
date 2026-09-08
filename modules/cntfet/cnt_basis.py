"""
@module cntfet.cnt_basis

S1 aligned-CNT FET object layer (CNT_FET_SIMULATION_PLAN.md,
ratified D1-D18). Decomposed objects (D2b) — geometry, material,
gate stack, contact, transport model, parasitics — NEVER one giant
row; parameter ROLES are schema (D8); Rc is first-class (D9).

The S1 scope is deliberately narrow (the ratified first target):
ONE aligned semiconducting CNT — one chirality, one gate stack, one
temperature, one contact prior — DC Id-Vg and Id-Vd only. No
variability, no multi-tube aggregation (S2+); fields that will hold
those knobs later say so instead of pretending.

This module is THIN by construction (D14): no heavy deps — numpy
only in the evaluation kernels, nothing quantum-chemical. Fidelity
kernels are optional engines behind knobs; the capability endpoint
refuses honestly when one is absent.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - cntfet.custom.cnt_derive (derivation), cnt_api (knob surface)
  - cntfet.cntfet_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/cnt/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from cntfet.objects.cnt._shared import SEED_CNT_CONTACTS, SEED_CNT_DEVICES, SEED_CNT_GEOMETRIES, SEED_CNT_MATERIALS, SEED_CNT_PARASITICS, SEED_CNT_TRANSPORT, SEED_GATE_STACKS  # noqa: F401
from cntfet.objects.cnt.CNTMaterialState import CNTMaterialState  # noqa: F401
from cntfet.objects.cnt.AlignedCNTFETGeometry import AlignedCNTFETGeometry  # noqa: F401
from cntfet.objects.cnt.GateStack import GateStack  # noqa: F401
from cntfet.objects.cnt.CNTContact import CNTContact  # noqa: F401
from cntfet.objects.cnt.CNTTransportModel import CNTTransportModel  # noqa: F401
from cntfet.objects.cnt.CNTParasitics import CNTParasitics  # noqa: F401
from cntfet.objects.cnt.AlignedCNTFETDevice import AlignedCNTFETDevice  # noqa: F401
from cntfet.objects.cnt.CNTFETParameterRow import CNTFETParameterRow  # noqa: F401
from cntfet.objects.cnt.CNTCalibrationAnchor import CNTCalibrationAnchor  # noqa: F401
from cntfet.objects.cnt.CNTFETSimResult import CNTFETSimResult  # noqa: F401
