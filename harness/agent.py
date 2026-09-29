"""LangChain agent factory.

Supports two providers:
    * google-genai  — Gemini API.
    * openai        — any OpenAI-compatible HTTP endpoint, including a vLLM
                      server hosting open-weights models. Pass `base_url`
                      (and `api_key` if the endpoint requires one).

The agent is LangGraph's `create_agent` (LangChain v1), bound to the tool
subset of the active phase.
"""
from __future__ import annotations

import os
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model


def build_model(model_id: str,
                *,
                provider: str = "google-genai",
                temperature: float = 0.0,
                timeout: int = 600,
                base_url: str | None = None,
                api_key: str | None = None,
                api_key_env: str | None = None,
                thinking_budget: int | None = 2048,
                include_thoughts: bool = True,
                **extra: Any):
    """Initialize a chat model via LangChain's `init_chat_model`.

    * `provider="google-genai"` talks to the Gemini API. `thinking_budget`
      and `include_thoughts` are forwarded to Gemini models only.
    * `provider="openai"` talks to any OpenAI-compatible endpoint. Pass
      `base_url` (e.g. `http://node:8000/v1` for a vLLM server) and an
      `api_key`, or the name of the env var holding it via `api_key_env`.
      Most self-hosted servers accept any non-empty key.
    """
    kwargs = dict(extra)

    if provider == "google-genai":
        if model_id.startswith("gemini-"):
            if thinking_budget is not None:
                kwargs["thinking_budget"] = thinking_budget
            if include_thoughts:
                kwargs["include_thoughts"] = True
        return init_chat_model(
            model_id,
            model_provider="google-genai",
            temperature=temperature,
            timeout=timeout,
            **kwargs,
        )

    if provider == "openai":
        if base_url is None:
            raise ValueError("provider='openai' requires base_url, e.g. "
                             "http://localhost:8000/v1")
        resolved_key = api_key
        if resolved_key is None and api_key_env:
            resolved_key = os.environ.get(api_key_env)
        if not resolved_key:
            resolved_key = "EMPTY"
        return init_chat_model(
            model_id,
            model_provider="openai",
            base_url=base_url,
            api_key=resolved_key,
            temperature=temperature,
            timeout=timeout,
            **kwargs,
        )

    raise ValueError(f"unsupported provider: {provider}")


def build_agent(model, *, tools: list):
    """Build a LangGraph ReAct-style agent bound to `tools`.

    No system prompt is passed: with tools bound, Gemini 2.5 Flash sometimes
    returned an empty AIMessage when given one, so the system content is
    inlined into the first user message instead (see history.py).
    """
    return create_agent(model=model, tools=tools)
