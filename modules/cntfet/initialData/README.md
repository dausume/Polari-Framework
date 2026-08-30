# cntfet initial data (module data convention)

Plain-JSON rows this module needs that **code cannot regenerate**, loaded
at boot, by `POST /modules/seed {"moduleId":"cntfet"}`, and served by
`GET /modules/cntfet/initial-data` so another instance can install them
from this API instead of a git pull (`moduleService/json_seeds.py`).
Customized rows (`is_prior` False) are never clobbered.

| file | why it is here |
|---|---|
| `CellCharacterizationRun.json` | characterized cell libraries (Liberty text + grids) — need the ngspice/OpenVAF/OpenSTA engines worker, ~40 min per library; latest run per (device, cell) only |
| `AlignedCNTFETDevice.json` | derived VS parameters, `derived_at`, provenance |
| `OpenCellLibrary.json`, `FunctionalBlock.json` | admission / proof results |

(`SiliconMOSFET.json` lives in `modules/sifet/initialData/`.)

**Deliberately NOT here** (`EXCLUDED` in `cnt_snapshot.py`): basis rows,
anchors, evidence, IP, targets, ladder nodes, cell definitions (seeds in
code); `CNTFETSimResult` / `FETFieldSample` (a POST regenerates them in
seconds); `cnt-engines/vendor` (binaries — `fetch-vendor.sh`).

Refresh only when a library or derivation actually changed (each refresh
is ~0.8 MB of git history): `polari-cli/shells/snapshot-cntfet-data.sh`.
Check: `cd modules && PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_snapshot`
