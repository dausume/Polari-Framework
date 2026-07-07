"""
@module simulations.multi_scale_profile_conformance

Conformance checking between a MultiScaleSimulationDefinition and the
MultiScaleSimulationProfile (family) it declares via `profile_ref`.

Pure read-only analysis: parses both objects' JSON blobs and reports,
slot by slot, how the msim fills the family shape. Every finding
carries the concrete config it inspected (`evidence`) and unmet shapes
become SUGGESTIONS pointing at the exact knob to fill — never
auto-applied ([[knobs-and-suggestions]]).

Finding levels:
  ok   — a required (or present optional) slot is filled.
  gap  — a REQUIRED family slot the msim does not fill (conforms=False).
  note — an optional slot unfilled, or a deviation from the family's
         default search policy. Informational; never fails conformance.
"""

import json
from typing import Any, Dict, List


def _parse(blob: str, default):
    try:
        parsed = json.loads(blob or '')
        return parsed if isinstance(parsed, type(default)) else default
    except (TypeError, ValueError):
        return default


def _finding(level: str, slot: str, message: str, evidence: Any) -> Dict:
    return {'level': level, 'slot': slot, 'message': message,
            'evidence': evidence}


def check_profile_conformance(manager, msim_def, profile) -> Dict:
    """Report how `msim_def` fills `profile`'s family shape.

    Returns {conforms, profile, msim, findings: [...], suggestions: [...]}.
    `conforms` is False only when a REQUIRED template/panel slot is
    unfilled (gaps); notes never fail conformance. Never mutates
    either object.
    """
    findings: List[Dict] = []
    suggestions: List[Dict] = []

    stages = _parse(getattr(msim_def, 'stages_json', ''), [])
    panels = _parse(getattr(msim_def, 'panels_json', ''), [])
    templates = _parse(getattr(profile, 'stage_templates_json', ''), [])
    roster = _parse(getattr(profile, 'panel_roster_json', ''), [])
    default_policy = _parse(
        getattr(profile, 'default_search_policy_json', ''), {})

    # --- Stage templates: each matched by (kind, intent) --------------
    for tpl in templates:
        want_kind = tpl.get('kind')
        want_intent = tpl.get('intent')
        required = bool(tpl.get('required'))
        slot_name = f"stage-template:{tpl.get('key', want_kind)}"
        matches = [s for s in stages
                   if s.get('kind') == want_kind
                   and (want_intent is None
                        or s.get('intent') == want_intent)]
        if not matches:
            level = 'gap' if required else 'note'
            findings.append(_finding(
                level, slot_name,
                f"No stage with kind='{want_kind}'"
                + (f", intent='{want_intent}'" if want_intent else '')
                + f" fills the family's '{tpl.get('key')}' template"
                + ('' if required else ' (optional)'),
                {'template': tpl,
                 'stageKinds': [(s.get('key'), s.get('kind'), s.get('intent'))
                                for s in stages]}))
            if required:
                suggestions.append({
                    'action': f"Add a stage of kind '{want_kind}' to "
                              f"'{getattr(msim_def, 'name', '?')}' stages_json",
                    'reason': f"The '{getattr(profile, 'name', '?')}' family "
                              f"expects a '{tpl.get('key')}' stage",
                    'evidence': {'template': tpl},
                })
            continue
        # Slot-fill inspection: does the matching stage carry the
        # config keys the template names as slots?
        stage = matches[0]
        slots = tpl.get('slots') or {}
        unfilled = [k for k in slots
                    if not stage.get(k)
                    and not (k == 'gate' and stage.get('gate'))]
        if unfilled:
            findings.append(_finding(
                'note', slot_name,
                f"Stage '{stage.get('key')}' matches the template but "
                f"leaves slot(s) {unfilled} empty",
                {'stage': stage, 'slots': slots}))
        else:
            findings.append(_finding(
                'ok', slot_name,
                f"Stage '{stage.get('key')}' fills the "
                f"'{tpl.get('key')}' template",
                {'stageKey': stage.get('key'),
                 'filledSlots': sorted(slots)}))
        # Search-policy deviations are notes, never failures.
        search_cfg = stage.get('search') or {}
        if search_cfg and default_policy:
            deviations = {
                k: {'family': v, 'stage': search_cfg.get(k)}
                for k, v in default_policy.items()
                if k in search_cfg and search_cfg.get(k) != v
            }
            if deviations:
                findings.append(_finding(
                    'note', f'{slot_name}:search-policy',
                    "Stage search knobs deviate from the family default "
                    "(allowed — deviations are informational)",
                    deviations))

    # --- Panel roster --------------------------------------------------
    panel_kinds = [p.get('kind') for p in panels]
    for slot in roster:
        want = slot.get('kind')
        required = bool(slot.get('required'))
        slot_name = f"panel:{want}"
        if want in panel_kinds:
            findings.append(_finding(
                'ok', slot_name,
                f"Page carries the family's '{want}' panel",
                {'count': panel_kinds.count(want)}))
        else:
            findings.append(_finding(
                'gap' if required else 'note', slot_name,
                f"Page lacks the family's '{want}' panel"
                + ('' if required else ' (optional)'),
                {'rosterSlot': slot, 'panelKinds': panel_kinds}))
            if required:
                suggestions.append({
                    'action': f"Add a '{want}' panel to "
                              f"'{getattr(msim_def, 'name', '?')}' panels_json",
                    'reason': slot.get('slot')
                              or f"The family's pages recur to '{want}'",
                    'evidence': {'rosterSlot': slot},
                })

    # --- Coupling / derive-lineage shapes ------------------------------
    coupling_shapes = _parse(
        getattr(profile, 'coupling_shapes_json', ''), [])
    if coupling_shapes:
        has_derive = any(s.get('derive') for s in stages)
        has_couplings = bool(
            _parse(getattr(msim_def, 'coupling_refs_json', ''), []))
        for shape in coupling_shapes:
            mechanism = shape.get('mechanism')
            present = (has_derive if mechanism == 'derive'
                       else has_couplings if mechanism == 'coupling'
                       else False)
            findings.append(_finding(
                'ok' if present else 'note',
                f"coupling:{shape.get('from')}->{shape.get('to')}",
                (f"'{mechanism}' handoff present" if present else
                 f"No '{mechanism}' handoff found for this family shape"),
                {'shape': shape, 'hasDerive': has_derive,
                 'hasCouplings': has_couplings}))

    gaps = [f for f in findings if f['level'] == 'gap']
    return {
        'conforms': not gaps,
        'profile': getattr(profile, 'name', ''),
        'msim': getattr(msim_def, 'name', ''),
        'findings': findings,
        'suggestions': suggestions,
    }
