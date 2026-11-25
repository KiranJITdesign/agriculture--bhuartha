"""Agronomic AI Copilot service (OpenAI / OpenRouter compatible with deterministic fallback)."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)
_DOTENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def _get_env_or_dotenv(key: str, default: str = "") -> str:
    val = os.environ.get(key, "").strip()
    if val:
        return val
    if _DOTENV_PATH.exists():
        for line in _DOTENV_PATH.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                if k.strip() == key and v.strip():
                    return v.strip()
    return default


def _build_deterministic_reply(
    question: str,
    context: dict[str, Any],
) -> str:
    region = context.get("region_name", "Selected plot")
    mean_ndvi = context.get("mean_ndvi", "N/A")
    p50 = context.get("p50_ndvi", "N/A")
    cropland = context.get("cropland_area_ha", "0.00")
    cov = context.get("valid_pixel_pct", "0.00")
    rel_low = context.get("relative_low_area_ha", "0.00")
    abs_low = context.get("absolute_low_area_ha", "0.00")
    rain = context.get("total_rainfall_mm", "N/A")
    temp = context.get("mean_temperature_c", "N/A")
    anom = context.get("anomaly_pct")
    anom_str = f"{anom}%" if anom is not None else (context.get("anomaly_reason") or "N/A")

    q = question.lower()
    if "rain" in q or "weather" in q or "temp" in q:
        return (
            f"Weather telemetry for {region}: cumulative rainfall {rain} mm "
            f"(5-year anomaly: {anom_str}), mean 2m temperature {temp} C."
        )
    if "zone" in q or "stress" in q or "problem" in q or "low" in q:
        return (
            f"Low-greenness detection for {region} (valid coverage {cov}%): "
            f"{rel_low} ha relative localized low greenness within {abs_low} ha total low-NDVI."
        )
    return (
        f"{region}: Mean NDVI {mean_ndvi} (median p50 {p50}) across {cropland} ha cropland "
        f"({cov}% valid Sentinel-2 coverage). Relative low greenness: {rel_low} ha. "
        f"Rainfall: {rain} mm, mean temp: {temp} C."
    )


def _try_ollama(system_prompt: str, user_msg: str) -> dict[str, str] | None:
    """Try local open-source Ollama server if running on port 11434."""
    ollama_url = _get_env_or_dotenv("OLLAMA_URL", "http://127.0.0.1:11434/v1")
    ollama_model = _get_env_or_dotenv("OLLAMA_MODEL", "llama3.1")
    try:
        resp = requests.post(
            f"{ollama_url.rstrip('/')}/chat/completions",
            json={
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.2,
                "max_tokens": 300,
            },
            timeout=3,
        )
        if resp.ok:
            data = resp.json()
            answer = str(data["choices"][0]["message"]["content"]).strip()
            return {"answer": answer, "provider": f"ollama:{ollama_model}"}
    except Exception:
        return None
    return None


def ask_agronomic_copilot(question: str, context: dict[str, Any]) -> dict[str, str]:
    """
    Answer an agronomic question grounded in real Sentinel-2 & NASA POWER metrics.
    Uses OpenAI/OpenRouter when OPENAI_API_KEY is configured, local open-source Ollama
    if running, or deterministic summary.
    """
    system_prompt = (
        "You are an agronomic satellite analyst for TerraIntel. Answer concisely using ONLY "
        "the supplied Sentinel-2 NDVI, ESA WorldCover cropland, and NASA POWER weather metrics. "
        "Never invent numbers or scene IDs. State valid coverage % beside low-greenness figures."
    )
    user_msg = f"Metrics:\n{context}\n\nQuestion: {question}"

    api_key = _get_env_or_dotenv("OPENAI_API_KEY")
    if not api_key:
        ollama_res = _try_ollama(system_prompt, user_msg)
        if ollama_res is not None:
            return ollama_res
        return {
            "answer": _build_deterministic_reply(question, context),
            "provider": "deterministic (set OPENAI_API_KEY in .env or run Ollama)",
        }

    base_url = _get_env_or_dotenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = _get_env_or_dotenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.2,
                "max_tokens": 300,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = str(data["choices"][0]["message"]["content"]).strip()
        return {"answer": answer, "provider": f"openai:{model}"}
    except Exception as exc:
        logger.warning("OpenAI copilot request failed (%s); falling back to deterministic", exc)
        return {
            "answer": _build_deterministic_reply(question, context),
            "provider": "deterministic-fallback",
        }
