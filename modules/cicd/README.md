# cicd — the build pipeline's settings, as rows

His ask, 2026-09-19: *"We may want a CICD app as well that is always enabled
with the pipeline that can allow us to read and modify the settings of the
pipeline."*

**Polari is the source of truth for the pipeline's configuration.**
`polari-jenkins/device.env` is the fallback, and it is rewritten from these
rows by `cicd-sync.sh pull` at the top of every Jenkinsfile. When the core
does not answer, the device keeps the file it has and says so on one line —
a pipeline that stalled because a web service was down would be worse than
one that used yesterday's knobs and told you.

## Two modes (his addendum, 2026-09-19)

> *"some people will also be using this pipeline as a way to maintain their
> own Polari Apps and will only be testing the one app they are developing."*

| | `suite` | `app` |
|---|---|---|
| what is built | the whole Polari suite | ONE Polari app (`CI_APP_NAME`, from `CI_APP_REPO`) |
| the core | built here | **pulled**, never rebuilt — `CI_CORE_SOURCE=release:<tag>` or `release:latest` (`build` is the escape hatch) |
| stages default to | `core` | `core; <app>` |
| the release is | the suite's artifacts | that app's deb alone |
| published to | upstream Polari's routes | **the developer's own** (`PipelineRoute.target`) — a fork is never republished under an upstream name |
| the record says | the version it built | `tested_against`: the CORE release the app passed against |

The release rule is unchanged in both: only what a stage TESTED, and passed,
may ship.

## The rows

| class | who writes it |
|---|---|
| `PipelineDevice` | a person (admin), on its own page. The device REPORTS readiness back. |
| `PipelineStage` | a person — the ordered list that decides what can ever be released |
| `PipelineRoute` | `enabled` is Polari's knob; `armed` (the secret is present) is the device's reading |
| `PipelineSecretPresence` | the device — a NAME and a boolean, never a value |
| `PipelineRun` | the pipeline, at a build's start and end |
| `IsleTestResult` | the pipeline, per run × stage |
| `ReleaseRecord` | the pipeline — what shipped, and what did not, with the reason |

## The doors

    GET  /api/cicd                  everything for one device in ONE read (settings + stages + routes +
                                    readiness + the rendered device.env) — what `cicd-sync.sh pull` calls
    GET  /api/cicd/device           the settings and their validation
    POST /api/cicd/device           ADMIN — change them (the same rules device.sh applies)
    POST /api/cicd/device/token     ADMIN — mint the posting-only token. SHOWN ONCE; only sha256 is stored.
    POST /api/cicd/stages           ADMIN — replace the ordered testing stages
    POST /api/cicd/routes/{name}    ADMIN — {"enabled": true|false} (and optionally {"target": …})
    POST /api/cicd/ingest           THE MIRROR — the posting-only token; five kinds; a value-shaped field is
                                    a 400 and nothing is stored
    GET  /api/cicd/runs  /results  /releases

## Two credentials, deliberately different

* **A person, to change a setting** — `ADMIN_ROLES` (`admin`, `polari-admin`),
  identified by their opaque Keycloak `sub` alone (his PII rule D18-1).
* **The pipeline, to mirror a run in** — a per-device posting-only token. It
  may reach `POST /api/cicd/ingest` and nothing else: it cannot read or
  change a setting, cannot mint another, and is **not a Jenkins credential**.
  Nothing in this module starts, stops or reads a build; the mirror flows one
  way, inward.

A token is chosen over a Keycloak service account because a pipeline device
commonly points at a LEAN core where `POL_PROD_AUTH=off` and there is no
Keycloak at all. A credential that only existed when Keycloak did would work
on one deployment and silently not on another.

## Pages — configured, no new component

`/display/cicd`, `/display/cicd-stages`, `/display/cicd-runs`,
`/display/cicd-releases`. Every item is `class-rows-table` or
`api-structured-panel`; **editing happens on the rows' own tables**, through
CRUDE, gated by the `cicd-settings` permission profile (`cicd_seed`). No
Angular was written for any of it.

## Admission — "always enabled with the pipeline"

`polari-cli/prod-profiles/pipeline-device.env` — its `POL_PROD_MODULES` ends
in `,cicd`, so a pipeline device's core admits this module by construction:

    pol prod profile use pipeline-device --apply

`pol jenkins doctor` checks it live: a core that answers but has no
`/api/cicd` reports **`cicd module` — NOT admitted**, and names that command
as the fix. Elsewhere the module is harmless: it seeds no device, no run and
no release, and every door answers honestly that this instance has no
pipeline device.

## Selftest

    cd polari-rf-node/polari-framework && PYTHONPATH=.:modules python3 modules/cicd/cicd_selftest.py

and the shell half:

    bash polari-jenkins/selftest.sh
