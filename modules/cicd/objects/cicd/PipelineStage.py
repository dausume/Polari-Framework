"""
@module cicd.objects.cicd.PipelineStage

Row class PipelineStage of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PipelineStage(treeObject):
    """ONE ORDERED TESTING STAGE of a device's `CI_ISLE_STAGES` (§70 addendum; his ask 2026-09-19:
    *"We should also be able to setup Isle Testing stages, for the case where we are space limited but still
    want to test as much as we can."*).

    `CI_ISLE_STAGES=core; household; electronics,cntfet` is THREE of these rows: index 1 with no apps (the
    literal `core`), index 2 with `["household"]`, index 3 with `["electronics", "cntfet"]`. Each stage runs
    in its OWN throwaway isle, one at a time — which is the whole point of staging on a space-limited box.

    The rows are the truth and the knob string is DERIVED from them (`cicd.custom.cicd_stages.render`), so
    the ordering lives somewhere a person can edit on a page rather than inside a semicolon-separated string.

    THE RELEASE RULE rides on this list: only an app a stage TESTED and passed may ever ship, so a name
    misspelt here is an app that silently never releases. That is why the validation refuses an app with no
    `modules/<name>/polari-app.json`, an app named in two stages, and an empty stage — exactly the three
    warnings `device.sh device_validate_stages` raises, ported once into
    `cicd.custom.cicd_validate` so there is ONE rule set.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', index: int = 1, apps_json: str = '[]',
                 note: str = '', posted_by: str = ''):
        self.name = name            # the row id — <device>:<index>
        self.device = device        # PipelineDevice.name
        self.index = index          # 1-based; the order the stages run in
        self.apps_json = apps_json  # the module names tested in THIS stage; [] = core only
        self.note = note            # why this grouping (space, ordering, a dependency)
        self.posted_by = posted_by  # the `sub` or the credential name that last wrote this row
