"""
@module cicd.custom.cicd_stages

CI_ISLE_STAGES ⇄ PipelineStage rows — the ONE parser, in python.

`polari-jenkins/device.sh` owns the shell half (`stages_list`), and this is its exact counterpart: stages
separated by `;`, apps within a stage by `,`, whitespace anywhere ignored, the literal `core` meaning "core
debs only" and therefore dropping out of a stage's app list. The two must agree, because the release rule
reads the shell's answer and a page shows this one — the selftest feeds both the same strings.

Rows are the truth and the knob string is DERIVED (`render`), so a person edits an ordered list of rows on
a page instead of a semicolon-separated string in a file.
"""


def parse(raw):
    """'core; household; gears,cntfet' → [[], ['household'], ['gears', 'cntfet']].

    An empty stage stays as an empty list (a line, not a dropped entry) exactly as `stages_list` prints an
    empty line — the validation wants to WARN about it, which it cannot do if parsing silently swallows it.
    """
    text = '' if raw is None else str(raw)
    out = []
    for chunk in text.split(';'):
        cleaned = ''.join(chunk.split())          # whitespace anywhere is ignored
        apps = [a for a in cleaned.split(',') if a and a != 'core']
        out.append(apps)
    return out


def render(stages):
    """[[], ['household'], ['gears', 'cntfet']] → 'core; household; gears,cntfet' (the device.env value).

    An empty list of stages renders as `core`: `setup/steps/06-stages.sh setup_stages_render` does the same,
    because a device with no stage at all can never release anything and the honest default is core only.
    """
    parts = [','.join(a for a in (apps or []) if a) or 'core' for apps in (stages or [])]
    return '; '.join(parts) if parts else 'core'


def rows_to_stages(rows):
    """PipelineStage rows (any object with .index and .apps_json) → the ordered list of app lists."""
    import json
    ordered = sorted(rows, key=lambda r: int(getattr(r, 'index', 0) or 0))
    out = []
    for r in ordered:
        try:
            apps = json.loads(getattr(r, 'apps_json', '[]') or '[]')
        except Exception:
            apps = []
        out.append([str(a) for a in apps if a and str(a) != 'core'])
    return out
