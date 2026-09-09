# Appstore (`appstore`)

Polari App Store (appstore-1): installable native shells over the polariapps content layer — catalog/identity, one-time enrollment tokens (hashed at rest), overlaid Gradle source archives + prebuilt binaries from MinIO.

**Kind:** polari-app · **agent tier:** member · **requires:** polariapps

## Objects

`AiToolDefinition`, `AiToolsAPI`, `AppDebsPage`, `AppEdgeBehavior`, `AppShellDefinition`, `AppStoreAPI`, `DownloadsPage`, `ForkPin`, `OfflinePage`, `PlannerPage`, `RemoteHostingOption`, `ShellArtifact`, `ShellEnrollment`, `ShellInstallation`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `appstore_ai_basis.py`, `appstore_basis.py`, `appstore_forks_basis.py`, `appstore_hosting_basis.py`
- **api** — `appstore_ai_api.py`, `appstore_api.py`, `preview_server_api.py`
- **seed** — `appstore_seed.py`
- **page** — `app_debs_page.py`, `appstore_page.py`, `downloads_page.py`, `offline_page.py`, `planner_page.py`
- **custom** — `custom/app_deb_builder.py`, `custom/appstore_minio.py`, `custom/appstore_payloads.py`, `custom/appstore_tokens.py`, `custom/downloads_shared.py`, `custom/module_requirements.py`, `custom/offline_chunker.py`, `custom/shell_project.py`
- **selftests** — `app_debs_selftest.py`, `appstore_selftest.py`, `downloads_selftest.py`, `module_requirements_selftest.py`, `offline_chunker_selftest.py`, `offline_selftest.py`, `planner_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `appstore.appstore_page:SEED_APPSTORE_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest appstore        # in the running backend
PYTHONPATH=.:modules python3 -m appstore.app_debs_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform appstore`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
