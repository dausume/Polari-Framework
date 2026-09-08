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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/appstore/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.objects.appstore._shared import BEHAVIOR_KINDS, DISTRIBUTIONS, ENROLLMENT_STATUSES, PLATFORM_KEYS, SHELL_SCOPES  # noqa: F401
from appstore.objects.appstore.AppShellDefinition import AppShellDefinition  # noqa: F401
from appstore.objects.appstore.AppEdgeBehavior import AppEdgeBehavior  # noqa: F401
from appstore.objects.appstore.ShellArtifact import ShellArtifact  # noqa: F401
from appstore.objects.appstore.ShellEnrollment import ShellEnrollment  # noqa: F401
from appstore.objects.appstore.ShellInstallation import ShellInstallation  # noqa: F401
