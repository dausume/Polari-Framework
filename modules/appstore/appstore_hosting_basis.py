"""
@module appstore.appstore_hosting_basis

ai-7 (Dustin): concrete remote-hosting SUGGESTIONS with PRICES —
every price carries its AS-OF DATE and source URL, because a price
without a date is a lie waiting to happen. Rows are editable data
(is_prior discipline): anyone can re-check a price and bump
price_as_of; the UI flags stale dates instead of trusting them.

Fit against the localai hosting profiles is DERIVED from the
option's declared specs (the ai-6 host_check logic — an option is
just a machine we don't own yet); options whose specs vary per
listing (marketplaces) are honestly 'unverified', never guessed.

@consumers
  - appstore.appstore_ai_api (/api/appstore/ai-tools/hosting-options)
  - polari-platform-angular /ai-hosting
  - polariServer defClassList (table + CRUDE)
  - appstore.appstore_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/appstore_hosting/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from appstore.appstore_ai_basis import host_check

from appstore.objects.appstore_hosting._shared import HOSTING_KINDS_REMOTE, SEED_REMOTE_HOSTING, _AS_OF, hosting_options_payload, option_fit  # noqa: F401
from appstore.objects.appstore_hosting.RemoteHostingOption import RemoteHostingOption  # noqa: F401
