#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""Reasoning-capability provider layer (Phase 4).

A provider-agnostic seam for the in-app AI assistant. Which backend answers is
a routing/config decision, never baked into the app: selection is via the env
var POLARI_REASONING_PROVIDER (default 'null'). Every provider receives the same
node context and returns the same envelope, so the assistant behaves identically
whether it is backed by a null (no-LLM) responder, a hosted frontier model, or a
future local/open-weight model.

  null       deterministic, node-aware replies with no LLM — works out of the box
  anthropic  Claude via the anthropic SDK (needs the SDK + a credential)

Add providers here (openai, litellm, local vLLM, ...) without touching the API
or the frontend. This is the reasoning slice of the capability manager.
"""

import os

# Kept in sync with polari-mcp/ai_conventions.json — the standard the AI follows.
GATED_CAPABILITIES = [
    {"area": "topology", "intent": "report modules, connections, and instance shape (read-only)"},
    {"area": "nocode_playthrough", "intent": "inspect solutions/simulations and step runs (gated)"},
    {"area": "connectors", "intent": "propose connectors between elements (gated, confirm)"},
    {"area": "displays", "intent": "propose incremental display edits + event bindings (gated, confirm)"},
    {"area": "navigation", "intent": "report where things are by id/class (advice)"},
]

_MUTATION_RULE = (
    "Mutations are two-step and gated: I propose a change (dry-run), and nothing "
    "is applied until you confirm. I cannot self-approve high-authority actions, "
    "and every change is written to a JSON provenance log."
)


class NullReasoningProvider:
    """No-LLM fallback: a deterministic, node-aware assistant. Real enough to
    build and test the whole in-app path against; swap in a real provider by
    setting POLARI_REASONING_PROVIDER + a credential."""

    name = "null"

    def __init__(self, note=None):
        self.note = note

    def respond(self, message, node_context, history=None):
        counts = node_context.get("class_counts", {})
        awareness = ", ".join(f"{k}={v}" for k, v in counts.items()) or "no classes reported"
        reply = (
            "AI assistant (no-LLM mode — set POLARI_REASONING_PROVIDER + a credential "
            "to enable full reasoning).\n"
            f"You said: {message!r}\n"
            f"Node awareness: {awareness}; {node_context.get('object_types', 0)} object types.\n"
            f"{_MUTATION_RULE}\n"
            "I can report topology/modules/displays and prepare gated proposals for "
            "display edits, event bindings, connectors, and simulation steps."
        )
        out = {"reply": reply, "capabilities": GATED_CAPABILITIES, "mode": "deterministic"}
        if self.note:
            out["provider_note"] = self.note
        return out


class AnthropicReasoningProvider:
    """Claude via the anthropic SDK. Constructed only if the SDK imports and a
    credential resolves; otherwise routing falls back to null."""

    name = "anthropic"

    def __init__(self, api_key=None, model=None):
        import anthropic  # raises if not installed -> caller falls back to null
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model or os.environ.get("POLARI_REASONING_MODEL", "claude-opus-4-8")

    def _system(self, node_context):
        counts = node_context.get("class_counts", {})
        awareness = ", ".join(f"{k}={v}" for k, v in counts.items())
        return (
            "You are the in-app AI assistant for Polari, a research operating "
            "environment. Follow the Polari MCP conventions: inspect before you "
            "write; every interface mutation is a two-step gated proposal the human "
            "confirms; you cannot self-approve high-authority actions; every change "
            "is audited. Help with no-code, displays, connectors, topology, and "
            f"navigation. Current node awareness: {awareness}."
        )

    def respond(self, message, node_context, history=None):
        try:
            from polariApiServer import ai_tools
        except ImportError:
            import ai_tools
        tools = ai_tools.anthropic_tools()
        system = self._system(node_context)
        msgs = []
        for turn in (history or []):
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                msgs.append({"role": turn["role"], "content": turn["content"]})
        msgs.append({"role": "user", "content": message})
        proposals, text = [], ""
        for _ in range(6):  # read tools auto-run; propose tools pause for the user
            resp = self.client.messages.create(
                model=self.model, max_tokens=1024, system=system, tools=tools, messages=msgs)
            text = "".join(getattr(b, "text", "") for b in resp.content
                           if getattr(b, "type", None) == "text")
            msgs.append({"role": "assistant", "content": resp.content})
            if getattr(resp, "stop_reason", None) != "tool_use":
                break
            results = []
            for b in resp.content:
                if getattr(b, "type", None) == "tool_use":
                    out = ai_tools.dispatch(b.name, b.input, proposals)
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            msgs.append({"role": "user", "content": results})
        return {"reply": text or "(no text response)", "proposals": proposals,
                "capabilities": GATED_CAPABILITIES, "mode": "model", "model": self.model}


class OpenAIReasoningProvider:
    """OpenAI or any OpenAI-compatible endpoint (local vLLM/Ollama, OpenRouter, a
    LiteLLM proxy, a future local open-weight server) via the openai SDK."""

    name = "openai"

    def __init__(self, api_key=None, model=None, base_url=None):
        import openai  # raises if not installed
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        elif base_url:
            kwargs["api_key"] = "not-needed"  # local servers ignore it
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)
        self.model = model or "gpt-4o"

    def respond(self, message, node_context, history=None):
        try:
            from polariApiServer import ai_tools
        except ImportError:
            import ai_tools
        tools = ai_tools.openai_tools()
        counts = node_context.get("class_counts", {})
        awareness = ", ".join(f"{k}={v}" for k, v in counts.items())
        system = (
            "You are the in-app AI assistant for Polari. Inspect before you write; every "
            "interface mutation is a two-step gated proposal the human confirms; you cannot "
            f"self-approve high-authority actions. Node awareness: {awareness}."
        )
        msgs = [{"role": "system", "content": system}]
        for turn in (history or []):
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                msgs.append({"role": turn["role"], "content": turn["content"]})
        msgs.append({"role": "user", "content": message})
        proposals, text = [], ""
        for _ in range(6):
            resp = self.client.chat.completions.create(
                model=self.model, max_tokens=1024, messages=msgs, tools=tools)
            msg = resp.choices[0].message
            text = msg.content or text
            calls = msg.tool_calls or []
            msgs.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": c.id, "type": "function",
                                         "function": {"name": c.function.name,
                                                      "arguments": c.function.arguments}}
                                        for c in calls]})
            if not calls:
                break
            import json as _json
            for c in calls:
                try:
                    args = _json.loads(c.function.arguments or "{}")
                except ValueError:
                    args = {}
                out = ai_tools.dispatch(c.function.name, args, proposals)
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": out})
        return {"reply": text or "(no text response)", "proposals": proposals,
                "capabilities": GATED_CAPABILITIES, "mode": "model", "model": self.model}


def build_provider(name):
    """Construct a provider by name from the managed config (raises on failure).
    Used by get_provider (with fallback) and by config.validate (probe)."""
    try:
        from polariApiServer import reasoning_config as rc  # server (package) path
    except ImportError:
        import reasoning_config as rc  # standalone / same-dir path
    settings = rc._settings(name)
    secret = rc.get_secret(name)
    model = settings.get("model") or rc.PROVIDER_REGISTRY.get(name, {}).get("default_model")
    if name in ("", "null", "none"):
        return NullReasoningProvider()
    if name == "anthropic":
        return AnthropicReasoningProvider(api_key=secret, model=model)
    if name in ("openai", "openai_compatible"):
        return OpenAIReasoningProvider(api_key=secret, model=model, base_url=settings.get("base_url"))
    raise ValueError(f"unknown provider {name!r}")


def get_provider():
    """Route to the active provider from the managed config (env overrides),
    falling back to null on any failure so the assistant is always available."""
    try:
        try:
            from polariApiServer import reasoning_config as rc  # server (package) path
        except ImportError:
            import reasoning_config as rc  # standalone / same-dir path
        name = (os.environ.get("POLARI_REASONING_PROVIDER") or rc.active_config()["provider"] or "null").strip().lower()
    except Exception:  # noqa: BLE001
        name = os.environ.get("POLARI_REASONING_PROVIDER", "null").strip().lower()
    if name in ("", "null", "none"):
        return NullReasoningProvider()
    try:
        return build_provider(name)
    except Exception as exc:  # noqa: BLE001
        return NullReasoningProvider(note=f"provider {name!r} unavailable ({exc}); using null")

