#    Copyright (C) 2020  Dustin Etts
#    GNU GPLv3 — see LICENSE.

"""Reasoning-provider selection + authentication automation (Phase 4).

Turns provider choice from a single env var into a managed capability: a
registry of providers with their auth requirements, automatic detection of
what's installed and credentialed, a persisted active selection, and a
validation probe. Secrets never enter the object tree, prompts, or provenance —
they live only in a restricted-permission, git-ignored secret file (or the
process environment), and are never returned by any read.

  registry   what each provider is + what auth it needs (CODE — tracked)
  config     the active selection + non-secret settings (data/ — git-ignored)
  secrets    api keys, if entered locally (data/, chmod 600 — git-ignored)

The AI/MCP layer may read status, propose a selection, and trigger validation.
It must NOT be the channel a secret is entered through — a human sets the key
via the backend directly, keeping it out of AI context and the audit log.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

_DATA = Path(__file__).resolve().parents[1] / "data"
_CONFIG_FILE = _DATA / "reasoning_config.json"     # non-secret, git-ignored
_SECRET_FILE = _DATA / "reasoning_secrets.json"    # secret, chmod 600, git-ignored

# The registry is code (tracked). Each provider declares how it authenticates
# and what its SDK is, so detection is automatic. `secret_env` is the env var
# the SDK reads; `base_url` marks providers that also need an endpoint (local
# vLLM / Ollama / OpenRouter / a LiteLLM proxy — any OpenAI-compatible server).
PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
    "null": {
        "sdk": None, "secret_env": None, "needs_base_url": False,
        "default_model": None,
        "description": "Deterministic node-aware responder. No LLM, always ready.",
    },
    "anthropic": {
        "sdk": "anthropic", "secret_env": "ANTHROPIC_API_KEY", "needs_base_url": False,
        "default_model": "claude-opus-4-8",
        "description": "Claude via the anthropic SDK. Auth: ANTHROPIC_API_KEY or an "
                       "`ant auth login` profile.",
    },
    "openai": {
        "sdk": "openai", "secret_env": "OPENAI_API_KEY", "needs_base_url": False,
        "default_model": "gpt-4o",
        "description": "OpenAI via the openai SDK. Auth: OPENAI_API_KEY.",
    },
    "openai_compatible": {
        "sdk": "openai", "secret_env": "OPENAI_API_KEY", "needs_base_url": True,
        "default_model": None,
        "description": "Any OpenAI-compatible endpoint (local vLLM/Ollama, OpenRouter, "
                       "a LiteLLM proxy, or a future local open-weight server). Needs a "
                       "base_url; key optional for local servers.",
    },
}


# -- store helpers -----------------------------------------------------

def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict[str, Any], secret: bool = False) -> None:
    _DATA.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    if secret:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _config() -> dict[str, Any]:
    cfg = _read_json(_CONFIG_FILE)
    cfg.setdefault("active", os.environ.get("POLARI_REASONING_PROVIDER", "null"))
    cfg.setdefault("settings", {})
    return cfg


# -- detection ---------------------------------------------------------

def sdk_installed(name: str) -> bool:
    spec = PROVIDER_REGISTRY.get(name, {})
    mod = spec.get("sdk")
    if not mod:
        return True  # null needs no SDK
    try:
        __import__(mod)
        return True
    except Exception:  # noqa: BLE001
        return False


def get_secret(name: str) -> Optional[str]:
    """Resolve a provider's secret from the local secret file, then the env.
    Never logged, never returned to callers other than provider construction."""
    secrets = _read_json(_SECRET_FILE)
    if name in secrets and secrets[name]:
        return secrets[name]
    spec = PROVIDER_REGISTRY.get(name, {})
    env = spec.get("secret_env")
    if env and os.environ.get(env):
        return os.environ[env]
    return None


def _settings(name: str) -> dict[str, Any]:
    return _config().get("settings", {}).get(name, {})


def has_credential(name: str) -> bool:
    spec = PROVIDER_REGISTRY.get(name, {})
    if name == "null":
        return True
    if get_secret(name):
        return True
    # anthropic can auth via an `ant` profile with no explicit key
    if name == "anthropic":
        return sdk_installed("anthropic")  # SDK resolves profile at call time
    # openai_compatible: the key is OPTIONAL (the provider sends
    # 'not-needed' when only a base_url is given — local servers
    # ignore it). A keyed endpoint (OpenRouter) that refuses shows
    # up honestly in the validate probe, not here.
    if name == "openai_compatible":
        return True
    return False


def provider_status(name: str) -> dict[str, Any]:
    spec = PROVIDER_REGISTRY.get(name, {})
    installed = sdk_installed(name)
    cred = has_credential(name)
    settings = _settings(name)
    needs: list[str] = []
    if not installed:
        needs.append(f"pip install {spec.get('sdk')}")
    # openai_compatible's key is optional — never listed as a need
    # (ai-1: a bound local server must be able to show ready).
    if (name not in ("null", "anthropic", "openai_compatible")
            and not get_secret(name)):
        needs.append(f"set {spec.get('secret_env')} (or enter it via the backend)")
    if spec.get("needs_base_url") and not settings.get("base_url"):
        needs.append("set base_url")
    ready = installed and cred and not (spec.get("needs_base_url") and not settings.get("base_url"))
    return {
        "name": name,
        "description": spec.get("description"),
        "sdk_installed": installed,
        "has_credential": cred,          # boolean only — never the value
        "needs_base_url": bool(spec.get("needs_base_url")),
        "settings": {k: v for k, v in settings.items() if k != "api_key"},
        "default_model": spec.get("default_model"),
        "ready": ready,
        "needs": needs,
    }


def all_status() -> dict[str, Any]:
    cfg = _config()
    return {
        "active": cfg.get("active"),
        "active_via_env": bool(os.environ.get("POLARI_REASONING_PROVIDER")),
        "providers": [provider_status(n) for n in PROVIDER_REGISTRY],
    }


# -- mutation ----------------------------------------------------------

def set_active(name: str, settings: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if name not in PROVIDER_REGISTRY:
        raise ValueError(f"unknown provider {name!r}")
    cfg = _read_json(_CONFIG_FILE)
    cfg.setdefault("settings", {})
    cfg["active"] = name
    if settings:
        merged = {**cfg["settings"].get(name, {}), **{k: v for k, v in settings.items() if k != "api_key"}}
        cfg["settings"][name] = merged
    _write_json(_CONFIG_FILE, cfg)
    return all_status()


def set_secret(name: str, secret: str) -> dict[str, Any]:
    """Store a provider secret locally (chmod 600). Returns status only — never
    the secret. Intended to be called by the human/backend, NOT via the AI."""
    if name not in PROVIDER_REGISTRY:
        raise ValueError(f"unknown provider {name!r}")
    secrets = _read_json(_SECRET_FILE)
    secrets[name] = secret
    _write_json(_SECRET_FILE, secrets, secret=True)
    return provider_status(name)


def active_config() -> dict[str, Any]:
    cfg = _config()
    name = cfg.get("active", "null")
    return {"provider": name, "settings": _settings(name)}


def validate(name: str, build_fn) -> dict[str, Any]:
    """Attempt to construct the provider and make a tiny probe call. `build_fn`
    is provided by reasoning_provider (avoids a circular import). Returns
    {ok, detail} — never a secret."""
    status = provider_status(name)
    if not status["ready"]:
        return {"ok": False, "detail": f"not ready: {', '.join(status['needs']) or 'unknown'}"}
    try:
        provider = build_fn(name)
        result = provider.respond("ping", {"class_counts": {}, "object_types": 0})
        ok = bool(result.get("reply"))
        return {"ok": ok, "detail": f"{name} responded" if ok else "no reply"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}
