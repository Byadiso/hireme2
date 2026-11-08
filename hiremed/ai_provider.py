"""Groq-first JSON inference with optional Gemini backup. No secrets logged."""
import json
import logging
import os
import re
import requests

LOG = logging.getLogger(__name__)


def configured_providers():
    preferred = os.getenv("AI_PROVIDER", "groq").strip().lower()
    if preferred not in ("groq", "gemini"):
        preferred = "groq"
    backup = os.getenv("AI_FALLBACK_PROVIDER", "gemini").strip().lower()
    order = [preferred] + ([backup] if backup in ("groq", "gemini") and backup != preferred else [])
    return [name for name in order if (os.getenv("GROQ_API_KEY") if name == "groq" else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")))]


def _parse_json(raw):
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I).strip()
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("AI response was not a JSON object")
    return obj


def _groq(system, user):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"], "Content-Type": "application/json"},
        json={"model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
              "messages": [{"role": "system", "content": system + "\nReturn a single valid JSON object. Never fabricate candidate facts."},
                           {"role": "user", "content": user[:25000]}],
              "temperature": 0, "response_format": {"type": "json_object"}},
        timeout=45,
    )
    response.raise_for_status()
    return _parse_json(response.json()["choices"][0]["message"]["content"])


def _gemini(system, user):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        contents=system + "\nRespond with one JSON object only. Never fabricate candidate facts.\n" + user[:25000],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
    )
    return _parse_json(response.text)


def llm_json(system, user):
    providers = configured_providers()
    if not providers:
        LOG.warning("No AI provider configured; using deterministic fallback")
        return None
    for provider in providers:
        try:
            return _groq(system, user) if provider == "groq" else _gemini(system, user)
        except Exception as exc:
            # Avoid logging request bodies, CV data, or API keys from exception strings.
            status = getattr(getattr(exc, "response", None), "status_code", None)
            LOG.warning("%s AI request failed (%s, HTTP %s); trying next provider if configured", provider, type(exc).__name__, status or "n/a")
    return None
