#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""Tool layer for the in-app AI assistant's model tool-calling loop (Phase 4).

Provider-neutral tool specs the reasoning loop hands to a real model, plus a
`dispatch` that runs them:

  - READ tools execute immediately (level 0) so the model can gather context.
  - PROPOSE tools DO NOT act — they create a gated, dry-run proposal via the
    action kernel and hand it back to the caller, which surfaces it to the user
    as a confirmation card. The model is told the proposal is pending, so it
    never assumes a change was applied.

Same gate, same proposals, same provenance as the '/act' command path and the
MCP server — the model is just another source of proposals.
"""

import json
import urllib.request

try:
    from polariApiServer.ai_actions import _BASE  # server (package) path
except ImportError:
    from ai_actions import _BASE  # standalone / same-dir path


TOOL_SPECS = [
    {"name": "list_displays", "kind": "read",
     "description": "List display definitions (id, name, description). Read-only.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "read_class", "kind": "read",
     "description": "Read instances of a Polari class by name (e.g. 'ScoreTerm', "
                    "'DisplayDefinition'). Read-only.",
     "input_schema": {"type": "object",
                      "properties": {"class_name": {"type": "string"}},
                      "required": ["class_name"]}},
    {"name": "list_modules", "kind": "read",
     "description": "List Polari modules and their status. Read-only.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "propose_display_update", "kind": "propose",
     "description": "PROPOSE an incremental edit to a display. Does NOT apply — creates a "
                    "gated proposal the user must confirm. Read the display first.",
     "input_schema": {"type": "object",
                      "properties": {"display_id": {"type": "string"},
                                     "patch": {"type": "object"}},
                      "required": ["display_id", "patch"]}},
    {"name": "propose_score_assertion", "kind": "propose",
     "description": "PROPOSE asserting a score for a subject in a context. Does NOT apply — "
                    "creates a gated proposal the user must confirm.",
     "input_schema": {"type": "object",
                      "properties": {"subject": {"type": "string"},
                                     "context": {"type": "string"},
                                     "value": {},
                                     "basis": {"type": "string"}},
                      "required": ["subject", "context", "value"]}},
]

_BY_NAME = {t["name"]: t for t in TOOL_SPECS}


def anthropic_tools():
    return [{"name": t["name"], "description": t["description"],
             "input_schema": t["input_schema"]} for t in TOOL_SPECS]


def openai_tools():
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": t["input_schema"]}} for t in TOOL_SPECS]


def _get_trim(path, limit=3000):
    try:
        with urllib.request.urlopen(_BASE + path, timeout=15) as resp:
            body = resp.read().decode()
    except Exception as exc:  # noqa: BLE001
        return f"(read failed: {exc})"
    return body if len(body) <= limit else body[:limit] + "…<trimmed>"


def dispatch(name, tool_input, proposals_out):
    """Run a tool. Read tools return data; propose tools append a gated proposal
    to `proposals_out` and return a 'pending confirmation' marker."""
    spec = _BY_NAME.get(name)
    if not spec:
        return f"unknown tool {name!r}"
    tool_input = tool_input or {}

    if spec["kind"] == "read":
        if name == "list_displays":
            return _get_trim("/DisplayDefinition")
        if name == "list_modules":
            return _get_trim("/modules")
        if name == "read_class":
            cls = str(tool_input.get("class_name", ""))
            if not cls or "/" in cls or " " in cls:
                return "invalid class_name"
            return _get_trim(f"/{cls}")
        return f"unhandled read tool {name!r}"

    # propose tools — never execute; create a gated dry-run proposal
    try:
        from polariApiServer import ai_actions  # server (package) path
    except ImportError:
        import ai_actions  # standalone / same-dir path
    if name == "propose_display_update":
        did = tool_input.get("display_id")
        patch = tool_input.get("patch") or {}
        if not did or not patch:
            return "need display_id and a non-empty patch"
        prop = ai_actions.kernel.propose(
            "display_update",
            f"Patch DisplayDefinition {did}: {list(patch.keys())}",
            {"class": "DisplayDefinition", "polariId": did, "updateData": patch})
    elif name == "propose_score_assertion":
        params = {k: tool_input.get(k) for k in ("subject", "context", "value", "basis")
                  if tool_input.get(k) is not None}
        prop = ai_actions.kernel.propose(
            "score_assert",
            f"Assert score {params.get('value')!r} for {params.get('subject')}",
            {"class": "ScoreAssertion", "params": params})
    else:
        return f"unhandled propose tool {name!r}"

    proposals_out.append(prop)
    return (f"Proposed (id={prop['proposal_id']}, authority level {prop['authority_level']}). "
            "This is NOT applied — it is awaiting the user's confirmation. Do not assume it took effect.")
