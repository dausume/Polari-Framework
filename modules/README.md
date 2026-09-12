# Polari modules and apps — the standard format (developer reference)

This is the reference for anyone writing or generating a Polari module or
app: what the kinds mean, what every directory and file is for, what the
manifest declares, and the rules the linter and `pol modules conform` check.
The design history is in `AI-Notes/designs/STANDARD_POLARI_APP.md`; this
file is the contract.

## 1. Words

| word | meaning |
|---|---|
| **module** | one Python package under `modules/<id>/` holding rows (object classes), an API, seeds, pages, and a selftest, described by its manifest `polari-app.json`. The unit of code, packaging (module debs) and testing. |
| **app** | what a module (or a set of modules) IS to a user, declared by `app.kind` in the manifest (§2). Every module is an app of some kind; most are `polari-app`. |
| **suite app** | a purpose-oriented composition of apps of ANY kind (Polari modules, isle containers, KVM guests, extensions), too big for one computer by design: parts with placement needs + the object contracts the parts pass through Polari. Declared as rows (`SuiteAppDefinition`, `SuitePart`, `SuiteContract`) by a module of kind `suite-app` (e.g. `printing_suite`). |
| **row / object** | a `treeObject` subclass. Every row class gets a table, CRUDE endpoints and a place on the object tree automatically. Every capability maps to a row; nothing lives only in code. |
| **store row** | an `IsleCatalogEntry`: what the isle's store lists and installs (`isle store install <name>`), with a kind of its own (§2b) and an install plan of host commands. |

## 2. App kinds (`app.kind` in `polari-app.json`)

| kind | what it means | needs | example |
|---|---|---|---|
| `library` | rows and pure code other modules use; no pages/API of its own | — | `hardwareapps`, `suiteapps`, `composition` |
| `polari-app` | pages + API inside a Polari instance (the common kind) | a Polari instance | `gears`, `nutrition`, `hwmap` |
| `isle-app` | a CONTAINER app deployed behind the isle agent (compose/image at `<name>.isle`), with its rows in a module | an isle member | `kirimoto` (the slicer), the engine workers |
| `hardware-app` | a QEMU/KVM GUEST the isle defines and starts, owning real hardware through passthrough; rows render its libvirt domain + guest configuration | the **hardware tier** (a device with cpu-virt + /dev/kvm + libvirt) | `isle_relay`, `isle_guestnet`, `voron` |
| `hardware-extension-app` | functionality pushed INTO a running hardware app it `extends`; it has no guest of its own | the host guest running | `reticulum` (extends `isle-relay`), `printcam` (extends `voron-printer`) |
| `suite-app` | the composition kind (§1) | its parts' needs, resolved by placement | `printing_suite` |

**2b. Store-row kinds** (`IsleCatalogEntry.kind`, what `isle store` installs): `mesh-app` (a container app), `polari-app` (a launcher for a Polari page/app), `polari-instance` (another Polari), `polari-module` (a module deb), `isle-vpn` (the VPN app family), `hardware-app`, `hardware-extension-app`. A module of kind `isle-app` or `hardware-app` seeds its own store row (`SEED_<X>_CATALOG` in its basis index).

**2c. Agent tiers** (`app.agentTier`): `reach` (any device that can see the isle), `member` (runs the isle agent — the default), `hardware` (member + libvirt/KVM; hardware kinds require it), `core` (the isle core itself).

## 3. The directory layout and what each entry is for

```
modules/<id>/
  polari-app.json        THE MANIFEST — the only file the core reads to learn the module (§4)
  README.md              what it is, its objects, its pages, how to run its selftest (generated first, then yours)
  __init__.py            """@module <id>""" docstring + `from <id>.<id>_basis import *`
  objects/               ROW CLASSES, ONE CLASS PER FILE, in taxonomy folders of any depth
    <group>/__init__.py      re-exports the group's classes AND explains the taxonomy in its docstring
    <group>/<ClassName>.py   one treeObject class, named as the file; its docstring = the explanation (§5)
    <group>/_shared.py       constants/seeds several classes of the group share (produced by the splitter)
  <id>_basis.py          the INDEX of rows: re-exports every class from objects/ and holds the seed lists
                         (SEED_*), <ID>_SEED_PAIRS and <ID>_CLASSES; may also hold the store rows (SEED_<ID>_CATALOG)
  <id>_api.py            class <Id>API(treeObject): the Falcon routes under /api/<id>/… registered in __init__
  <id>_endpoints.py      (optional) def construct(polServer) when the API needs assembly beyond one class
  <id>_seed.py           no-code rows: Analysis/Solution/Table/Graph definitions — upserted by name, never insert-by-name
  <id>_page.py           SEED_<ID>_PAGE_DISPLAYS: /display/<route> pages built ONLY from module_pages_seed
                         helpers (_page/_row/_table/_sapi) — no raw JSON panel, ever
  <id>_catalog.py        (optional) store rows + install_plan for app kinds this module ADDS to the store
  <id>_remote.py         (optional) the resolution ladder for an external engine/sidecar (URL knob → topology → refusal)
  <id>_selftest.py       THE selftest (required); more as <topic>_selftest.py; prints "X/Y checks passed", exits 0/1
  custom/                everything that fits no concept file: engines, analyses, renderers, provisioners, scanners.
                         Module-name prefixes are welcome here (gear_kinematics.py); subfolders allowed
  initialData/<Class>.json   non-regenerable data rows (schema module-initial-data/1), loaded at boot and served
                         by /modules/<id>/initial-data; never data you can derive
```
Rules the tooling enforces: every top-level `.py` ends in its concept
postfix (the list above) or lives in `objects/` or `custom/`; no other
top-level subdirectories; a row class lives in `objects/`, one per file,
file named as the class; the index re-exports so every import keeps
working. `pol modules conform <id>` reports deviations; it never blocks.

## 4. The manifest, field by field (`polari-app.json`, schema `polari-app/1`)

| field | meaning |
|---|---|
| `id`, `package`, `title`, `description`, `version` (semver from the repo's VERSION), `kind` (provenance: official / vendor / self), `wave`, `repo` | identity; `repo` is the module's own public repository |
| `app.kind` | §2 |
| `app.family` | an app family the module belongs to (e.g. `isle-vpn`) |
| `app.extends` | for `hardware-extension-app`: the hardware app it extends |
| `app.catalogKinds` | store-row kinds this module ADDS (e.g. vpn adds `isle-vpn`) |
| `app.agentTier` | §2c |
| `requires.modules` | other modules it imports (the registry + the loader agree with this) |
| `requires.libraries` | declared pip deps (the packaging scan measures the real closure; a mismatch is a finding) |
| `requires.engines` | `{name, kind: python|system|image, probe}` — external engines it resolves |
| `files.<concept>` | every file by concept (§3) — the tools never guess from names |
| `classes` | every row class (from objects/) |
| `imports` | `[["<id>.<file>", ["Symbol", …]], …]` — what the core imports (must stay inside the package) |
| `endpoints` | `"<id>.<file>:<function>"` — the API constructor |
| `seedPairs`, `pages`, `derivedSeeds`, `initialData`, `selftests` | where the seeds, the pages, derived seeds, data and tests live |
| `featureModule`, `coreRequired`, `legacyDynamicModule` | loader facts (optional module / must always load / legacy `initialize()` shape) |
`python3 -m moduleService.manifests generate <id>` refreshes a manifest from
the code (a hand-set `app` block, title, description and version survive).

## 5. Row rules (what a class file must do)
- `class X(treeObject)` with `@treeObjectInit`; first field `name: str = ''`;
  typed defaults for every field; `is_prior: bool = True` on seeded rows.
- The class docstring has three parts: **What it is** (the concept this row
  records), **Related concepts** (the rows it points at / is pointed at
  by), **How it is measured or derived** (where the numbers come from —
  cite or derive, never type a number without provenance).
- Every capability is a knob with an honest refusal: an absent dependency
  is a named reason (`{'ok': False, 'error': …, 'suggestion': …}`), never
  a guess; measurements carry `observed_at`; mocks carry `is_mock`.
- Nothing arriving from outside (a mesh, a push, a file) mutates rows
  directly; it becomes a proposal or a replace-per-device ingest.

## 6. Suite apps (rows, not files)
- `SuiteAppDefinition`: the purpose. `SuitePart`: one member app (`app` = a
  module id or a store-row name, `kind` = §2, `role` design | material |
  mold | slice | control | measure | map | network | support, `placement`
  any | core | hardware | node | same-as, `required`, `order`).
  `SuiteContract`: one row class a producer part hands a consumer part
  (`object_class` must exist in `owner_module`'s manifest).
- Placement is computed (`/api/suiteapps/<name>`) against the devices, the
  hardware map and the coverage budget; verdicts are placed /
  needs-hardware-tier / needs-node / unplaceable, each with its reason.

## 7. The tools
| verb | does |
|---|---|
| `pol modules new <id> [--kind …]` | scaffold a module in this shape with a passing selftest |
| `pol modules add-object <id> <Class> [--under a/b] [--base X] [--fields "a:str,b:float=0.0"]` | one per-class file + re-exports + index line |
| `pol modules conform [<id>…]` | report deviations from §3/§4 (never a gate) |
| `pol modules manifests generate|readme|list|selftest` | refresh manifests / first READMEs / the contract selftest |
| `pol modules selftest <id>` | run the module's selftests in the running backend |
| `pol modules testplan …` | which apps test which modules under the standard-computer budget |
| `pol hwmap …` | what hardware a device has and what a KVM app can take |
The linter (`pol dev lint`, rule ids PA-100…700) and `pol dev admit` are the
dev-tools plan (`AI-Notes/plans/POLARI_DEV_TOOLS_PLAN.md`).

## 8. Checklist for a new module
1. `pol modules new <id>` → edit the manifest's `title`, `description`, `app.kind`.
2. Add rows with `add-object` (one class per file, docstring in three parts); seeds by name; `initialData/` only for non-regenerable data.
3. Pages from the helpers only; API under `/api/<id>/`; refusals named.
4. `pol modules conform <id>` clean; selftest prints `X/Y checks passed`.
5. If the module is an isle-app / hardware-app: seed its store row (+ the guest row for hardware) and declare `hardware_needs_json`.
6. Register it (registry row + the core tables — until they are generated from manifests, `conform` names what is missing).

## 9. Working on ONE module or app as its own project (`pol project`)

A Polari Developer does not need the suite checkout. A module is its own
repository, opened alone in VS Code / VSCodium; every tool runs inside the
Polari backend image with the project directory mounted as
`modules/<id>`, and deploys talk to an instance's API.

```
pol project init <id> [--kind polari-app|library|isle-app|hardware-app]   scaffold + .vscode + .polari/project.json + git init
pol project lint            the standard's conformance report
pol project test            run the project's *_selftest.py in the image
pol project up | down | logs | status     a LOCAL lean Polari (http://127.0.0.1:3300) with the module mounted
pol project deploy          local: admit the mounted module; remote (--api URL): fetch-admit from the project's git remote
pol project update          the same, said plainly (re-fetch + re-admit)
pol project build [--offline]   the module deb into ./dist
pol project remove [--api URL]  put-away on the instance
pol project open            codium/code .
```
`.polari/project.json` holds the id, the image (`prf-backend:staging` today,
the GHCR tag once published) and the default instance; `POLARI_API` /
`POLARI_IMAGE` override. The `.vscode/` files name the Open VSX extension
ids (Python, Pyright, Ruff, YAML, Mermaid) and tasks that call these verbs,
so the loop is the same in VS Code, VSCodium and code-server. Deploying to
a remote instance requires the project pushed to its git remote (the
instance fetches it); the local instance mounts it directly.

**How a standalone module comes online (manifest admission, sap-3 first
slice).** The instance's core tables (`feature_imports.py`,
`module_endpoints.py`, the seed-pairs literal and the page concat in
`polariServer.py`) do not know a project module. `POST /modules/<id>/admit`
therefore reads the module's `polari-app.json`
(`polariApiServer/manifest_admission.py`): every file under `files.*` is
imported and the treeObject classes the module defines become its tables
(`*API` classes are never tabled); `endpoints`
(`<pkg>.<pkg>_endpoints:construct_<pkg>_endpoints`) is registered and
called once; `seedPairs` (`<pkg>.<pkg>_seed:<PKG>_SEED_PAIRS`, a list of
`(class_name, cls, rows)`) and `pages` are upserted by name once the tables
exist. Broken code is a refusal naming the exception, never a silent skip.
So a project module needs those two conventions the scaffold writes for it:
a `<pkg>_endpoints.py` with one `construct_<pkg>_endpoints(polServer)` and a
`<PKG>_SEED_PAIRS` list in `<pkg>_seed.py`. Modules the tables DO declare
never enter this path.

`pol project build` writes the deb to `dist/pool/` (the builder's pool,
pointed at `./dist`), registering the module as kind `self` in a writable
copy of the image's registry (`dist/.registry.json`); the image itself is
never written. Set `POLARI_TOOLS_DIR=<a polari-framework checkout>` to run
the tools (moduleService + polariApiServer) from the host instead of the
image — for people developing the tools themselves.

## 10. The registrar — one record per module, one health check

Every loading path (lazy boot worker, live admission, manifest admission,
put-away) updates the **module registrar**
(`moduleService/module_registrar.py`) as a module moves

```
declared → loading → verified: online | degraded
                     failed | blocked | invalid        disabled | put-away
```

What a module MUST bring online is read from its declaration, never
from what a loader claims: the `polari-app.json` gives the classes,
the endpoints constructor, the routes its api/endpoints files pass to
`add_route`, the seed pairs, the pages and the selftests (a module
without a manifest falls back to the core tables; core packages are
declared from their registered classes). `verify()` then checks each
piece against the LIVE server — class typed, CRUDE route in the router,
constructor ran, declared routes in the router, seed rows and pages
present by name. All structural pieces live = `online`; anything
missing = `degraded` with the missing names in the record; an exception
while loading = `failed`; a declaration that does not hold (unreadable
manifest, unresolvable endpoint reference) = `invalid`. Selftests are
informational: `POST /api/modules/health/<m>/confirm {piece: "selftest",
ok, detail}` records a result on the same record.

Read it:

```
GET  /api/modules/health[?brief=1]      ok + counts by state + every module's record
GET  /api/modules/health/<module>       expected / confirmed / missing per piece
POST /api/modules/health/<module>/verify   re-check now
pol modules health [--api URL] [<module>] [--verify]
/display/module-health                   the page (ModuleRegistration rows + summary)
```

`ok` is false while any module is degraded, failed, blocked or invalid.
The record is mirrored to a `ModuleRegistration` row per module per
instance, so the state survives a restart and is a table like any other.

## 11. The security stanza — what the app may touch

Every `polari-app.json` carries a `security` stanza (the scaffold and
`manifests generate` add the deny-all default; a hand-tuned stanza survives
regeneration). `os-security/render.py` turns it into the app's AppArmor
profile, seccomp allow-list and the compose/stack security fragment
(`security_opt`, `cap_drop: [ALL]` + declared `cap_add`, `read_only`,
`tmpfs`) — see `os-security/README.md` and ISLE_HARDENING_PLAN.md.

```json
"security": {
  "profile": "web-app",        // web-app | worker | gateway | vpn-gateway | hardware-extension
  "writable": ["/data"],       // the ONLY writable paths; everything else is read-only
  "network": ["isle"],         // isle | internet | none
  "capabilities": [],          // allow-list only: NET_ADMIN NET_BIND_SERVICE CHOWN SETUID SETGID DAC_READ_SEARCH
  "devices": [],               // /dev paths, only for hardware-extension (hardware lives in a guest)
  "ports": [3000]              // listening ports inside the container
}
```

`pol modules conform` refuses values outside those lists. Declare the least:
an app that needs nothing special keeps the default and still runs; an app
that declares `NET_ADMIN` gets it and nothing more.

## 12. Tiers and image variants (2026-09-12)

Every module in the register carries a `tier`: **core** — what makes Polari a networking and app system (polariapps, appstore, islemesh, terms, vpn, isle_relay, isle_guestnet, reticulum, mqttbridge, grpcbridge, scoring, hardwareapps, suiteapps, hwmap, testing, and resources/xr which the core requires) — or **optional** (the sciences, household and meals, scoring, video, …), which only some users need. A core module may never require an optional one (`pol modules deps` checks). The backend image is built in two variants from the same Dockerfile (`--build-arg POLARI_MODULE_SET=core|all`): the **core** image carries only core modules plus the register, so an optional module is fetched from its `polari-module-*` repository on admission (`POST /modules/<m>/fetch-admit`, dependencies first); the **all-official** image carries every official module. Release tags: `polari-vYYYY.MM.DD-core`, `polari-vYYYY.MM.DD-all` (the plain tag is the all variant). Every other image of a release carries both suffixes with identical content so a stack pulls one tag.
