"""
@module pspp.digitized_datasets_basis

Digitized source figures/tables as DATA rows (plan invariant I6) —
loading a book figure is data entry, not a code change, and every
curve carries its citation. One generic engine
(pspp.custom.dataset_interpolation) reads every row; extrapolation defaults
to UNSUPPORTED.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.custom.dataset_interpolation (the one reader)
  - pspp.datasets_seed (geopolymer book Ch.5 transcriptions)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/digitized_datasets/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from pspp.objects.digitized_datasets._shared import dataset_dict, dataset_index  # noqa: F401
from pspp.objects.digitized_datasets.DigitizedDataset import DigitizedDataset  # noqa: F401
