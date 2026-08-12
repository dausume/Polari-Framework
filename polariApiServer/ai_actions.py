#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""In-app AI action layer (Phase 4 keystone): the gated propose -> confirm ->
execute loop for the in-app assistant, mirroring the MCP server's authority
model so behavior is identical whichever surface drives it.

The assistant (a real model via tool-calling, or the deterministic '/act'
command grammar below) emits a typed PROPOSAL. Nothing runs until the user
confirms it through the panel. The kernel classifies the action's authority
level deterministically and refuses anything above the auto threshold unless an
out-of-band grant is set — the AI cannot self-approve. Every proposal and
execution is appended to a git-ignored JSON provenance log.

Executors call the node's own CRUDE endpoints over HTTP-to-self (stdlib only),
reusing the proven multipart contract.
"""

import json
import os
import secrets
import time
import urllib.request
import uuid
from pathlib import Path

_PORT = os.environ.get("BACKEND_HTTP_PORT", "3000")
_BASE = f"http://localhost:{_PORT}"
_DATA = Path(__file__).resolve().parents[1] / "data"
_PROVENANCE = _DATA / "ai_provenance.jsonl"

AUTO_MAX_LEVEL = int(os.environ.get("POLARI_AUTO_MAX_LEVEL", "3"))
ALLOW_HIGH = os.environ.get("POLARI_ALLOW_HIGH_AUTHORITY", "").strip() in ("1", "true", "yes")

_OP_LEVEL = {
    "sim_step": (2, "reversible-workspace"),
    "display_update": (3, "reversible-system"),
    "score_assert": (3, "reversible-system"),
    "connect": (3, "reversible-system"),
    # mtg-8: committing a dragged object's transform. Reversible-system:
    # it writes one row's fields and the previous value is in the
    # provenance log, so it can be put back. The DRAG itself is not
    # this — a drag is an ephemeral LiveKit preview; only the commit
    # becomes a proposal.
    "object_transform": (3, "reversible-system"),
    "storage_connect": (4, "network-service"),
    "delete": (7, "irreversible"),
}


def classify(op):
    return _OP_LEVEL.get(op, (7, "unknown-treated-as-irreversible"))


# -- HTTP-to-self executors (stdlib) -----------------------------------

def _multipart(method, path, fields):
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields.items():
        body += (f"--{boundary}\r\n"
                 f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                 f"{value}\r\n").encode()
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(_BASE + path, data=body, method=method)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return {"status": resp.status, "body": _safe_json(resp.read().decode())}


def _post_json(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(_BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return {"status": resp.status, "body": _safe_json(resp.read().decode())}


def _safe_json(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


def _exec_display_update(req):
    return _multipart("PUT", f"/{req['class']}",
                      {"polariId": req["polariId"], "updateData": json.dumps(req["updateData"])})


def _exec_create(req):
    return _multipart("POST", f"/{req['class']}",
                      {"initParamSets": json.dumps([req["params"]])})


def _exec_post_json(req):
    return _post_json(req["path"], req.get("payload", {}))


_EXECUTORS = {
    "display_update": _exec_display_update,
    "score_assert": _exec_create,
    "sim_step": _exec_post_json,
    "storage_connect": _exec_post_json,
    # A transform commit IS a field update — same executor, no second
    # write path (mtg-8).
    "object_transform": _exec_display_update,
}


class ActionKernel:
    def __init__(self):
        self._proposals = {}
        _DATA.mkdir(exist_ok=True)

    def _gate(self, level):
        if level <= AUTO_MAX_LEVEL:
            return True, f"level {level} <= auto threshold {AUTO_MAX_LEVEL}"
        if ALLOW_HIGH:
            return True, "out-of-band high-authority grant active"
        return False, f"level {level} > auto threshold {AUTO_MAX_LEVEL}; out-of-band approval required"

    def propose(self, operation, summary, request):
        level, label = classify(operation)
        pid = "act_" + secrets.token_hex(5)
        executable, reason = self._gate(level)
        self._proposals[pid] = {
            "proposal_id": pid, "operation": operation, "authority_level": level,
            "authority_label": label, "summary": summary, "request": request,
            "status": "pending",
        }
        self._record("proposed", self._proposals[pid])
        return {
            "proposal_id": pid, "operation": operation, "authority_level": level,
            "authority_label": label, "summary": summary, "request": request,
            "gate": {"executable": executable, "reason": reason}, "dry_run": True,
        }

    def execute(self, proposal_id, confirm):
        prop = self._proposals.get(proposal_id)
        if prop is None:
            return {"ok": False, "error": f"unknown proposal {proposal_id}"}
        if prop["status"] != "pending":
            return {"ok": False, "error": f"proposal already {prop['status']}"}
        if not confirm:
            return {"ok": False, "error": "confirm=true required", "proposal_id": proposal_id}
        executable, reason = self._gate(prop["authority_level"])
        if not executable:
            prop["status"] = "refused"
            self._record("refused", prop, {"reason": reason})
            return {"ok": False, "refused": True, "reason": reason,
                    "note": "The AI cannot self-approve this action."}
        executor = _EXECUTORS.get(prop["operation"])
        if executor is None:
            return {"ok": False, "error": f"no executor for {prop['operation']}"}
        try:
            result = executor(prop["request"])
            prop["status"] = "executed"
            self._record("executed", prop, {"result": result})
            return {"ok": True, "proposal_id": proposal_id, "result": result}
        except Exception as exc:  # noqa: BLE001
            prop["status"] = "failed"
            self._record("failed", prop, {"error": str(exc)})
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def provenance(self, limit=50):
        if not _PROVENANCE.exists():
            return []
        lines = _PROVENANCE.read_text().splitlines()[-limit:]
        return [json.loads(x) for x in lines if x.strip()]

    def _record(self, phase, prop, extra=None):
        entry = {"phase": phase, "at": time.time(),
                 **{k: prop[k] for k in ("proposal_id", "operation", "authority_level", "summary", "request")}}
        if extra:
            entry.update(extra)
        with _PROVENANCE.open("a") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")


kernel = ActionKernel()


# -- deterministic '/act' command grammar ------------------------------
# A power-user syntax AND the exact proposal shape a real model's tool call
# produces, so the confirm loop is testable with or without an LLM.
#
#   /act display_update <id> <field>=<value> [<field>=<value> ...]
#   /act score_assert subject=<id> context=<id> value=<v> [basis=<text>]

def parse_command(text):
    parts = text.strip().split()
    if len(parts) < 2 or parts[0] != "/act":
        return {"error": "not an /act command"}
    op = parts[1]
    if op == "display_update":
        if len(parts) < 3:
            return {"error": "usage: /act display_update <id> field=value ..."}
        display_id = parts[2]
        patch = _kv(parts[3:])
        if not patch:
            return {"error": "no field=value pairs given"}
        return kernel.propose(
            "display_update",
            f"Patch DisplayDefinition {display_id}: {list(patch.keys())}",
            {"class": "DisplayDefinition", "polariId": display_id, "updateData": patch})
    if op == "score_assert":
        kv = _kv(parts[2:])
        need = [k for k in ("subject", "context", "value") if k not in kv]
        if need:
            return {"error": f"missing: {need}"}
        return kernel.propose(
            "score_assert",
            f"Assert score {kv['value']!r} for {kv['subject']} in {kv['context']}",
            {"class": "ScoreAssertion", "params": kv})
    return {"error": f"unknown action {op!r}"}


def _kv(tokens):
    out = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v
    return out
