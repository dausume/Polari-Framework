"""
@module cmod.objects.cmod.PurposeObservation

PurposeObservation — one class per file (design §7). FIRMWARE_GENERATION_MODULE_PLAN.md §7.8.2 / §8.3 (his ruling 2026-10-15:
"storing runtime fulfillment and health per deployed device").
"""
from objectTreeDecorators import treeObjectInit, treeObject


class PurposeObservation(treeObject):
    """What it is: what ONE deployed board (a `BoardInstance`) has been seen to do for ONE Purpose — whether it is fulfilling it
    (`fulfillment`: unknown | satisfied | at-risk | violated) and how healthy it is (`health`: unknown | healthy | degraded |
    failed), why, when, and the evidence (the frame or event that decided it). `name` is '<purpose>@<board_instance>', so a new
    observation of the same pair is an upsert, never a growing pile. Written by the BACKEND from relayed state, never by a
    person (a person who disagrees records a `DerivedOverride`, which stays beside it). The Purpose's own summary ("on each
    device") is DERIVED from these rows — the weakest device — and never stored on the Purpose.
    Related concepts: `CapabilityDefinition` (the Purpose), `BoardInstance`, `DerivedOverride`.
    """

    plain_words = ('A Purpose observation says what one deployed board has been seen to do for one Purpose: whether it is '
                   'doing it, how healthy it is, why, when, and the report that decided it. Only the backend writes it.')

    FULFILLMENTS = ('unknown', 'satisfied', 'at-risk', 'violated')
    HEALTHS = ('unknown', 'healthy', 'degraded', 'failed')

    @treeObjectInit
    def __init__(self, name: str = '', purpose: str = '', board_instance: str = '', fulfillment: str = 'unknown',
                 health: str = 'unknown', why: str = '', observed_at: str = '', evidence: str = '', notes: str = '', manager=None):
        self.name = name                      # '<purpose>@<board_instance>'
        self.purpose = purpose                # a CapabilityDefinition name
        self.board_instance = board_instance  # the deployed BoardInstance this was seen on
        self.fulfillment = fulfillment        # unknown | satisfied | at-risk | violated
        self.health = health                  # unknown | healthy | degraded | failed
        self.why = why
        self.observed_at = observed_at        # ISO timestamp
        self.evidence = evidence              # the frame / event that decided it (a short description or id)
        self.notes = notes
