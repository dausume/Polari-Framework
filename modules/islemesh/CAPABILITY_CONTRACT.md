# Capability evidence and target reports (schema 1)

This is a read-only evaluator and reporting API. It does not install anything,
reserve resources, authorize a remote operation, or attest a reporting agent.
The existing authenticated/authorized ingest deployment must govern who can
report for a device. Host execution must independently revalidate requirements.

## Evidence

`POST /api/islemesh/ingest/device` accepts an optional `capability_evidence`:

```json
{
  "device": "worker-host",
  "capability_evidence": {
    "schema_version": 1,
    "facts": {
      "runtime.compose.usable": {
        "status": "observed",
        "value": true,
        "source": "host-probe:compose-version",
        "observed_at": "2026-10-30T00:00:00Z"
      }
    }
  }
}
```

Each observation has its own clock and source. `status: error` denotes a failed
probe, not an absent capability. A boolean check requires an actual JSON boolean;
numeric budgets use finite numbers, not strings or booleans. Source identifiers
must describe actual checks; these example values are not production evidence.
A capability report is replaced as a unit when explicitly supplied. Legacy
registry/device ingestion does not refresh capability observation timestamps.
Mock/real transitions clear old reports. Evidence older than 300 seconds or more
than 30 seconds in the future cannot establish readiness. The device's general
`last_seen` and report-receipt times are not health proofs.

## Requirements

`IsleCatalogEntry.requirements_json` is a curated map keyed by action:
`use`, `launcher`, `host`, `module`. Each action has a schema-1 descriptor:

```json
{
  "use": {
    "schema_version": 1,
    "kind": "polari-app",
    "action": "use",
    "complete": false,
    "needs": [
      {"dep": "isle.dns.usable", "scope": "device", "check": "present"},
      {"dep": "app.electronics.frontend.healthy", "scope": "isle",
       "group": "electronics-provider", "check": "present"},
      {"dep": "app.electronics.modules.compatible", "scope": "isle",
       "group": "electronics-provider", "check": "present"}
    ]
  }
}
```

The example is intentionally incomplete: application-specific authorization,
TLS/access, compatibility and dependency closure also need to be declared.
`complete: true` is a catalog-author assertion that the FULL requirements for
that particular action/version are included, not something the frontend or a
host probe may infer. App-specific descriptors and trustworthy probe producers
must be implemented/curated before enabling a real app's ready classification.
Unknown or missing descriptors remain unknown. No descriptors are automatically
seeded from broad app kinds, running agents, or historical deployments.

`hardware-app` requires an explicit `realization` (`kvm` or `bridge`) in both
catalog row and descriptor. Future realizations require an explicit extension.
For numeric requirements use `check: min`, a numeric `value`, and optionally
`failure: resource-limited`; equality uses `check: equals` with exact scalar type.
Failures may be `needs-setup`, `unsupported`, `resource-limited`, or
`policy-restricted`. The latter must come from separately authorized policy
evidence; it is not inferred from a role label. All unmet checks remain visible.

Device-scoped requirements must hold on the chosen target. Isle-scoped needs
with the same `group` must all hold on ONE provider. Different groups may use
different providers. The primary Polari provider need not be the infrastructure
core or the requesting client. Aggregate resource demand before evaluation;
duplicate dependencies are rejected rather than accidentally counting the same
free memory twice. This is not a multi-component resource scheduler. Split
placement graphs, exclusive reservations, schema migrations and primary-node
cutover remain separate planning/execution work.

## Read APIs

- `GET /api/islemesh/devices`: accepted observations, receipt times, mock flags.
- `GET /api/islemesh/catalog/{entry}/targets?action=host`: target checks and
  provider candidates for one app. Default action is `host`.
- `GET /api/islemesh/gaps?action=host`: same evaluation for published catalog
  entries. `action=use` evaluates access separately.

Responses carry schema version, evaluation time, status, target details and
`revalidation_required: true`. Ready means the declared requirements were met
by accepted recent reports, not that an app is installed/running or that an
installation is authorized. The current UI labels this explicitly.

A ready target yields an Isle-wide ready result. Unknown alternatives prevent
an unsupported-everywhere conclusion. No real targets means unknown; mocks
never count as providers. Invalid descriptors/facts fail conservatively.

## Validation and remaining integration

`python3 modules/islemesh/test_capabilities.py` runs pure evaluator fixtures and
actual route methods against in-memory tables. Runtime persistence/schema
upgrade, production ingest authorization, probe authenticity, capability
collector delivery and curated descriptor closure still require integration
proof. Existing installs without new evidence safely remain unknown.

## Dated results

Old, valid observations retain their verdict in `last_reported_status`, including
failed checks. Their original `observed_at` is retained; `evaluated_at` is only
the time this report was generated. The UI shows both and requests revalidation
before installation. No observation is labelled “Not reported yet”; partial
evidence is “Not fully reported; checks still needed”. Future clocks, malformed
values and probe errors cannot establish a historical pass. These are evaluations
of the last stored facts against current requirements, not an audit history.

The read-only CLI collector emits individually dated observations and publishes
only when explicitly requested, through verified HTTPS. The initial whoami and
Polari access descriptors check HTTP access only, not authenticated application
functions. The board-engines hosting descriptor is preliminary and remains
incomplete until the Electronics owner reviews the full deployment requirements.
