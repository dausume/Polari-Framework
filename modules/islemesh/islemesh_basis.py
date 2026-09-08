"""
@module islemesh.islemesh_basis

Object model for the isle-mesh convergence (mac-1): the polari-side
rows that ACCEPT isle-mesh's data so the topology-idiom pages can
show the isle coming online layer by layer (Dustin 2026-08-07 —
the visualization is the verification instrument for the arc).

Authority split (MESH_APP_CONVERGENCE_HANDOFF §7): isle-mesh is
authoritative over NETWORKING — these rows are polari's ACCEPTED
COPY of what isle reports (via /api/islemesh/ingest/*), plus the
mac-1 mesh-app model (one app, many realizations). Rows are
ingest-owned: `pol isle sync` (real) or `pol isle mock` (flagged)
replace them wholesale per device; nothing here is hand-curated.

Every class carries `is_mock`: real isle data NEVER sets it — only
the mock feed does — and the summary API turns any live mock row
into a large MOCK NETWORK banner (islemesh_constants.MOCK_BANNER).

@consumers
  - islemesh.islemesh_api (ingest + read surface)
  - polariServer defClassList (tables + CRUDE)
  - islemesh.islemesh_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/islemesh/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from islemesh.objects.islemesh.IsleDevice import IsleDevice  # noqa: F401
from islemesh.objects.islemesh.IsleUplink import IsleUplink  # noqa: F401
from islemesh.objects.islemesh.IsleApp import IsleApp  # noqa: F401
from islemesh.objects.islemesh.IsleAppService import IsleAppService  # noqa: F401
from islemesh.objects.islemesh.MeshAppRealization import MeshAppRealization  # noqa: F401
from islemesh.objects.islemesh.IsleProtocolPermit import IsleProtocolPermit  # noqa: F401
from islemesh.objects.islemesh.IsleCatalogEntry import IsleCatalogEntry  # noqa: F401
from islemesh.objects.islemesh.IsleEngine import IsleEngine  # noqa: F401
from islemesh.objects.islemesh.IsleIngestReceipt import IsleIngestReceipt  # noqa: F401
