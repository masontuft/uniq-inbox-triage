"""Minimal OpenAI-compatible chat client (xAI Grok, Gemini, OpenAI, etc.) using only the stdlib.

Configure in .env (copy .env.example) or as env vars:
  LLM_BASE_URL  e.g. https://api.x.ai/v1
  LLM_API_KEY   your key (.env is gitignored, never committed)
  LLM_MODEL     run `python3 triage.py --list-models` to see valid ids
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


class LLMError(RuntimeError):
    pass


class LLMAuthError(LLMError):
    """Bad or missing key: retrying or moving on to the next email can't help."""


def load_env(path: Path) -> None:
    """Read KEY=VALUE lines from a .env file. Real env vars win, so a shell export still overrides it."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        # Strip whitespace and wrapping quotes: the usual cause of "incorrect API key" after a paste.
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _config(need_model: bool = True) -> tuple[str, str, str]:
    needed = ["LLM_BASE_URL", "LLM_API_KEY"] + (["LLM_MODEL"] if need_model else [])
    missing = [k for k in needed if not os.environ.get(k)]
    if missing:
        raise LLMError(f"Set these in .env (see .env.example): {', '.join(missing)}")
    return os.environ["LLM_BASE_URL"].rstrip("/"), os.environ["LLM_API_KEY"], os.environ.get("LLM_MODEL", "")


def _headers(key: str) -> dict:
    # Cloudflare-fronted APIs (Groq) block Python's default "Python-urllib" User-Agent with 403 / error 1010.
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "uniq-triage/1.0"}


def list_models() -> list[str]:
    """Ask the provider which model ids this key can use (GET /models)."""
    base, key, _ = _config(need_model=False)
    req = urllib.request.Request(f"{base}/models", headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return sorted(m["id"] for m in json.load(resp)["data"])
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            raise LLMAuthError(f"The provider rejected LLM_API_KEY (HTTP {e.code}). Check the key in .env.")
        raise LLMError(f"HTTP {e.code} listing models")


def chat_json(system: str, user: str, retries: int = 8) -> dict:
    """Send one chat turn and parse the reply as a JSON object. Retries on rate limits and bad JSON."""
    base, key, model = _config()
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode()
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{base}/chat/completions", data=body, method="POST",
            headers=_headers(key),
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                content = json.load(resp)["choices"][0]["message"]["content"]
            return json.loads(_strip_fences(content))
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in (401, 403) or "api key" in detail.lower():
                raise LLMAuthError(f"The provider rejected LLM_API_KEY (HTTP {e.code}). Check the key and re-export it.")
            last_err = LLMError(f"HTTP {e.code}: {detail}")
            if e.code not in (429, 500, 502, 503, 504):
                break
            # Free tiers rate-limit hard; wait exactly as long as asked (header, or "try again in 26.28s" in the body).
            hint = re.search(r"try again in ([\d.]+)s", detail)
            wait = e.headers.get("retry-after") or (hint and hint.group(1))
            if wait:
                time.sleep(min(float(wait), 60) + 1)
                continue
        except (json.JSONDecodeError, KeyError, urllib.error.URLError, TimeoutError) as e:
            last_err = e
        time.sleep(2 ** attempt)
    raise LLMError(f"LLM call failed: {last_err}")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return text
