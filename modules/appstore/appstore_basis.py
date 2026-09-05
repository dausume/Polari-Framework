"""
@module appstore.appstore_basis

Object model for the Polari App Store: downloadable native app
SHELLS (JavaFX/JCEF desktop, WebView mobile) that wrap the instance's
web UI. The store REFERENCES polariapps.PolariAppDefinition rows as
its content layer — an AppShellDefinition says HOW an app is
delivered as an installable shell, never WHAT the app contains.

Enrollment is the pre-registration credential story: a one-time
token, hashed at rest, that a freshly installed shell redeems for
its registration document. It is NOT a Keycloak credential — first
login stays one interactive PKCE (S256) login with login_hint
prefilled (Dustin, 2026-08-06); the token only proves "this install
was invited by an authenticated user".

@consumers
  - appstore.appstore_api / appstore_payloads / shell_project
  - polariServer defClassList (tables + CRUDE)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: What a shell can wrap: the whole instance UI, or one
#: PolariAppDefinition's slice of it.
SHELL_SCOPES = ('instance', 'app')

#: Delivery targets. 'gradle-project' is the always-available source
#: build; the rest are prebuilt binaries uploaded out-of-band (the
#: instance cannot cross-compile — honesty over magic).
PLATFORM_KEYS = ('gradle-project', 'desktop-linux-x64',
                 'desktop-windows', 'desktop-macos',
                 # android-vr: Quest 2 / Vive headsets (Android-
                 # based) — the shell registers/probes natively and
                 # RENDERS THROUGH WOLVIC (required), the WebXR
                 # browser, so the suite's XR pages actually work.
                 'android', 'android-vr', 'ios')

#: How a shell is distributed.
DISTRIBUTIONS = ('generated-project', 'prebuilt', 'both')

#: Enrollment lifecycle.
ENROLLMENT_STATUSES = ('active', 'redeemed', 'expired', 'revoked')


class AppShellDefinition(treeObject):
    """One published store entry: a way to install an app (or the
    whole instance) as a native shell."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('polari-instance-shell').
        name: str = '',
        title: str = '',
        description: str = '',
        # SHELL_SCOPES entry.
        scope: str = 'instance',
        # PolariAppDefinition.name when scope == 'app'; '' otherwise.
        app_name: str = '',
        # JSON list of PLATFORM_KEYS entries this shell targets.
        platforms_json: str = '["gradle-project"]',
        # DISTRIBUTIONS entry.
        distribution: str = 'generated-project',
        # {'brandColor': '', 'icon': '<base64 png>'} — shell chrome.
        branding_json: str = '{}',
        # Initial web-UI route; '' = the app's first page (scope=app)
        # or '/' (scope=instance).
        start_route: str = '',
        # sep-2: JSON list of edge-behavior REFERENCES the shell may
        # use (camera, device passthrough...). The definitions live
        # as rows in the app's own module (sep-5); this names them.
        capabilities_json: str = '[]',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.scope = scope
        self.app_name = app_name
        self.platforms_json = platforms_json
        self.distribution = distribution
        self.branding_json = branding_json
        self.start_route = start_route
        self.capabilities_json = capabilities_json
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


#: AppEdgeBehavior.kind vocabulary — what a shell may do at the edge.
BEHAVIOR_KINDS = ('device', 'network', 'nocode-graph')


class AppEdgeBehavior(treeObject):
    """sep-5 (decision 8): one EDGE BEHAVIOR as reusable data — what
    a shell may do beyond wrapping the webapp (attach a device, join
    a network, run a no-code graph edge-side) and with what
    configuration. Written once, referenced by ANY app whose
    AppShellDefinition.capabilities_json names it — the registration
    carries REFERENCES, never these definitions. The native half
    (Gradle capability modules, ServiceLoader) stays rare and gated
    on the declaration; `requires_native` names it so the gate can
    refuse honestly when the module is absent (§5l precedent: the
    helper holds the privilege, never the shell)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique reference key ('lora-radio-attach').
        name: str = '',
        title: str = '',
        description: str = '',
        # BEHAVIOR_KINDS entry.
        kind: str = 'device',
        # The reusable configuration (JSON object): which devices
        # (DeviceLink correspondence), which networks (ssid...),
        # which no-code graph runs edge-side.
        config_json: str = '{}',
        # Gradle capability module the shell needs ('' = pure
        # config, no native code).
        requires_native: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.kind = kind
        self.config_json = config_json
        self.requires_native = requires_native
        self.published = published
        self.is_prior = is_prior
        self.notes = notes


class ShellArtifact(treeObject):
    """One deliverable artifact record — the bytes live in MinIO (or
    are overlaid on demand); this row is the manifest + hashes."""

    @treeObjectInit
    def __init__(
        self,
        # '<shell>@<platform>@<version>'.
        name: str = '',
        shell_name: str = '',
        # PLATFORM_KEYS entry.
        platform: str = 'gradle-project',
        version: str = '',
        # 'source-archive' (srcDistTar upload the store overlays) |
        # 'prebuilt-binary' (installDist/apk/... served as-is).
        kind: str = 'source-archive',
        # MinIO location; '' until an upload is committed.
        bucket: str = '',
        object_key: str = '',
        sha256: str = '',
        size_bytes: int = 0,
        # Overlay manifest (path -> sha256) of the last download —
        # the grpcbridge stamp idiom: record what was generated, the
        # artifact itself is rebuilt deterministically.
        manifest_json: str = '{}',
        # Keycloak sub of the admin who uploaded a prebuilt.
        uploaded_by: str = '',
        uploaded_at: str = '',
        last_generated_at: str = '',
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.shell_name = shell_name
        self.platform = platform
        self.version = version
        self.kind = kind
        self.bucket = bucket
        self.object_key = object_key
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.manifest_json = manifest_json
        self.uploaded_by = uploaded_by
        self.uploaded_at = uploaded_at
        self.last_generated_at = last_generated_at
        self.is_prior = is_prior
        self.notes = notes


class ShellEnrollment(treeObject):
    """One-time enrollment token, HASHED at rest.

    The wire token is '<name>.<secret>'; only sha256(secret) is
    stored. The plaintext exists exactly once — in the mint
    response — and redemption is single-use (status flips to
    'redeemed' BEFORE the response is written)."""

    @treeObjectInit
    def __init__(
        self,
        # Public token id ('enr-<12 hex>') — safe to log.
        name: str = '',
        # sha256 hexdigest of the secret half. NEVER the secret.
        token_hash: str = '',
        shell_name: str = '',
        # InstanceDefinition.name this enrollment binds to.
        instance_name: str = '',
        # Minter identity (Keycloak sub + preferred_username) — the
        # username becomes the shell's oidc login_hint.
        user_sub: str = '',
        username: str = '',
        created_at: str = '',
        # ISO-8601 UTC; TTL clamped to [60, 86400] s, default 900.
        expires_at: str = '',
        # ENROLLMENT_STATUSES entry.
        status: str = 'active',
        redeemed_at: str = '',
        redeemed_by_platform: str = '',
        # Client-supplied deviceLabel — audit trail only, no trust.
        redeemed_evidence: str = '',
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.token_hash = token_hash
        self.shell_name = shell_name
        self.instance_name = instance_name
        self.user_sub = user_sub
        self.username = username
        self.created_at = created_at
        self.expires_at = expires_at
        self.status = status
        self.redeemed_at = redeemed_at
        self.redeemed_by_platform = redeemed_by_platform
        self.redeemed_evidence = redeemed_evidence
        self.is_prior = is_prior
        self.notes = notes


class ShellInstallation(treeObject):
    """Audit receipt written at redeem: one registered install."""

    @treeObjectInit
    def __init__(
        self,
        # 'inst-<12 hex>'.
        name: str = '',
        enrollment_name: str = '',
        shell_name: str = '',
        instance_name: str = '',
        platform: str = '',
        device_label: str = '',
        user_sub: str = '',
        registered_at: str = '',
        last_seen_at: str = '',
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.enrollment_name = enrollment_name
        self.shell_name = shell_name
        self.instance_name = instance_name
        self.platform = platform
        self.device_label = device_label
        self.user_sub = user_sub
        self.registered_at = registered_at
        self.last_seen_at = last_seen_at
        self.is_prior = is_prior
        self.notes = notes
