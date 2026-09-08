"""
@module appstore.appstore_forks_basis

ai-9 (Dustin: "do we have forks of the projects we would need to
self-host... and a page for notating all of that"): the FORK-PIN
LEDGER — every upstream this project pins as a fork under
github.com/dausume/, as dated rows. The fork-as-pin rule exists
because upstream can relicense (the rns lesson: relicensed
GPLv3-INCOMPATIBLE 2025-04-15); a fork cannot be retroactively
changed. verified_at is the date the fork's EXISTENCE was last
checked against GitHub — the ai-7 dated-price discipline applied
to software.

Statuses are honest: 'forked' (pin exists, verified),
'delete-pending' (forked in error, awaiting Dustin's delete — the
CLI token lacks delete_repo), 'not-pinned' (a dependency we rely
on WITHOUT our own pin yet — named so the gap is visible, never
implied covered).

@consumers
  - appstore.appstore_ai_api (/api/appstore/ai-tools/fork-pins)
  - polari-platform-angular /ai-hosting (the software section)
  - polariServer defClassList (table + CRUDE)
  - appstore.appstore_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/appstore_forks/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from appstore.objects.appstore_forks._shared import FORK_ROLES, FORK_STATUSES, SEED_FORK_PINS, _VERIFIED, _pin, fork_pins_payload  # noqa: F401
from appstore.objects.appstore_forks.ForkPin import ForkPin  # noqa: F401
