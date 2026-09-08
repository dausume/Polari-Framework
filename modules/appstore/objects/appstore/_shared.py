"""@module appstore.objects.appstore._shared — what the appstore row classes share (constants, seeds, helpers); split from appstore_basis.py (sap-2c)."""

SHELL_SCOPES = ('instance', 'app')
PLATFORM_KEYS = ('gradle-project', 'desktop-linux-x64',
                 'desktop-windows', 'desktop-macos',
                 # android-vr: Quest 2 / Vive headsets (Android-
                 # based) — the shell registers/probes natively and
                 # RENDERS THROUGH WOLVIC (required), the WebXR
                 # browser, so the suite's XR pages actually work.
                 'android', 'android-vr', 'ios')
DISTRIBUTIONS = ('generated-project', 'prebuilt', 'both')
ENROLLMENT_STATUSES = ('active', 'redeemed', 'expired', 'revoked')
BEHAVIOR_KINDS = ('device', 'network', 'nocode-graph')
