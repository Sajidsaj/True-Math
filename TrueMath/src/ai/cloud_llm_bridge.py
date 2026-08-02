"""
Module Name: cloud_llm_bridge
Purpose: Talk to cloud LLM providers (Groq, then OpenRouter as fallback)
         using their OpenAI-compatible chat-completions endpoints, instead
         of a local Ollama server. This removes all local RAM/CPU load from
         the "AI brain" — nothing heavy runs on the user's machine anymore.
Responsibilities:
  - Try each configured provider in priority order until one succeeds.
  - Expose the same prompt_ai(system_prompt, math_context) interface the
    orchestrator already used for the old LocalLLMBridge, so it's a drop-in
    replacement.
Dependencies: urllib (no extra pip packages needed)
Integration Notes: If neither provider has an API key configured, prompt_ai
                    simply returns None (same graceful-fallback behavior as
                    before) — the app still runs using its built-in
                    non-LLM hypothesis generator, it just won't crash.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

import certifi

from src.core.sys_logger import get_logger

logger = get_logger("CloudLLMBridge")

# Uses certifi's CA bundle explicitly rather than relying on the system's
# default certificate store — some Windows Python installs have a missing
# or misconfigured system store, causing "CERTIFICATE_VERIFY_FAILED:
# unable to get local issuer certificate" on every HTTPS request otherwise.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _answer_signature(text: str) -> str:
    """Cheap normalization for comparing free-text LLM answers to each other:
    pulls out any numbers found (the usual 'final answer' for math
    questions), or falls back to a lowercased/stripped prefix so near-
    identical phrasing still counts as agreement."""
    numbers = re.findall(r"-?\d+\.?\d*", text)
    if numbers:
        return ",".join(numbers[:3])
    return text.strip().lower()[:60]


class _Provider:
    """A single OpenAI-compatible chat-completions endpoint."""

    def __init__(self, name: str, base_url: str, api_key: str, model_name: str):
        self.name = name
        self.base_url = base_url
        self.api_key = (api_key or "").strip()
        self.model_name = model_name
        self.last_error: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def call_raw(self, messages: list, timeout_s: int, tools: Optional[list] = None) -> Optional[dict]:
        """Like call(), but sends arbitrary message history and (optionally)
        tool schemas, and returns the full response message object (which
        may contain tool_calls) instead of just extracted text — needed for
        the agentic tool-calling loop."""
        body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base_url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        if self.name == "openrouter":
            req.add_header("HTTP-Referer", "https://truemath.local")
            req.add_header("X-Title", "TrueMath")

        self.last_error = None
        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=_SSL_CONTEXT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="ignore")[:300]
            logger.warning(f"{self.name} API returned HTTP {e.code}: {body_text}")
            self.last_error = "rate_limited" if e.code == 429 else ("invalid_key" if e.code in (401, 403) else f"http_{e.code}")
        except Exception as e:
            logger.warning(f"{self.name} call_raw failed: {e}")
            self.last_error = "network_error"
        return None

    def call(self, system_prompt: str, user_prompt: str, timeout_s: int) -> Optional[str]:
        payload = json.dumps({
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 800,
        }).encode("utf-8")

        req = urllib.request.Request(self.base_url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        if self.name == "openrouter":
            # Recommended by OpenRouter for request attribution — harmless to include.
            req.add_header("HTTP-Referer", "https://truemath.local")
            req.add_header("X-Title", "TrueMath")

        self.last_error = None
        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=_SSL_CONTEXT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")[:300]
            logger.warning(f"{self.name} API returned HTTP {e.code}: {body}")
            if e.code == 429:
                self.last_error = "rate_limited"
            elif e.code in (401, 403):
                self.last_error = "invalid_key"
            else:
                self.last_error = f"http_{e.code}"
        except Exception as e:
            logger.warning(f"{self.name} call failed: {e}")
            self.last_error = "network_error"
        return None


class CloudLLMBridge:
    """Drop-in replacement for LocalLLMBridge. Tries Groq first, then
    OpenRouter, so a single provider outage doesn't take the whole app down.
    Runs entirely over the network — no local model weights, no local RAM
    spike, no PC hang."""

    def __init__(
        self,
        groq_api_key: str,
        groq_model: str,
        groq_base_url: str,
        openrouter_api_key: str,
        openrouter_model: str,
        openrouter_base_url: str,
        timeout_s: int = 20,
    ):
        self.timeout_s = timeout_s
        self._providers = [
            _Provider("groq", groq_base_url, groq_api_key, groq_model),
            _Provider("openrouter", openrouter_base_url, openrouter_api_key, openrouter_model),
        ]
        configured = [p.name for p in self._providers if p.is_configured]
        if configured:
            logger.info(f"Cloud LLM providers active: {', '.join(configured)}")
        else:
            logger.warning(
                "No cloud LLM API keys configured. Set TRUEMATH_GROQ_API_KEY "
                "and/or TRUEMATH_OPENROUTER_API_KEY in your .env file. "
                "Until then, the built-in fallback generator will be used "
                "and the Q&A box will report that no AI engine is reachable."
            )

    def last_error_message(self) -> str:
        """Builds a specific, accurate explanation of why the last prompt_ai
        call failed — distinguishing 'no key configured' from 'rate limit
        hit' from 'invalid key' from 'network/SSL error', instead of always
        pointing at API key configuration regardless of the real cause."""
        configured = [p for p in self._providers if p.is_configured]
        if not configured:
            return (
                "Koi bhi API key set nahi hai. TRUEMATH_GROQ_API_KEY ya "
                "TRUEMATH_OPENROUTER_API_KEY .env file mein daalein."
            )

        reasons = {p.name: p.last_error for p in configured if p.last_error}
        if not reasons:
            return "Cloud AI se jawab nahi mil saka (wajah spasht nahi) — dobara try karein."

        if all(r == "rate_limited" for r in reasons.values()):
            names = ", ".join(reasons.keys())
            return (
                f"{names} ki free-tier rate limit abhi hit ho gayi hai (thodi der mein reset hogi). "
                "Ye API key ka masla nahi hai — bas thoda intezaar karein, ya doosri provider "
                "(Groq + OpenRouter dono) configure karein taake fallback mil sake."
            )
        if any(r == "invalid_key" for r in reasons.values()):
            bad = [name for name, r in reasons.items() if r == "invalid_key"]
            return f"{', '.join(bad)} ki API key invalid/expired lag rahi hai — .env file mein check karein."
        if all(r == "network_error" for r in reasons.values()):
            return "Internet/network se connect nahi ho saka — connection check karein."

        detail = "; ".join(f"{name}: {reason}" for name, reason in reasons.items())
        return f"Cloud AI se jawab nahi mil saka ({detail})."

    def prompt_with_user_key(
        self, system_prompt: str, math_context: str, user_provider: str, user_api_key: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Uses a CALLER-SUPPLIED API key for a single request, instead of
        the server's own configured Groq/OpenRouter keys. This is the
        mechanism that makes a public, multi-user deployment viable: every
        visitor uses their OWN free-tier quota, so no single shared key
        gets rate-limited by everyone at once. The key is used only for
        this one call and is never persisted anywhere (no database, no
        file, no log) — it lives only in this function call's memory.

        Returns (answer, error_reason) — error_reason is one of
        'rate_limited' / 'invalid_key' / 'network_error' / None (success).
        """
        user_provider = (user_provider or "").strip().lower()
        base_urls = {
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
        }
        default_models = {
            "groq": "openai/gpt-oss-120b",
            "openrouter": "deepseek/deepseek-chat",
        }
        if user_provider not in base_urls:
            return None, "invalid_key"

        temp_provider = _Provider(user_provider, base_urls[user_provider], user_api_key, default_models[user_provider])
        if not temp_provider.is_configured:
            return None, "invalid_key"

        result = temp_provider.call(system_prompt, math_context, self.timeout_s)
        return result, temp_provider.last_error

    def prompt_ai(self, system_prompt: str, math_context: str) -> Optional[str]:
        for provider in self._providers:
            if not provider.is_configured:
                continue
            result = provider.call(system_prompt, math_context, self.timeout_s)
            if result:
                return result
            logger.info(f"'{provider.name}' failed or returned nothing — trying next provider...")
        return None

    def prompt_ai_self_consistent(self, system_prompt: str, math_context: str, n: int = 3):
        """Self-Consistency prompting (Wang et al., 2022, "Self-Consistency
        Improves Chain of Thought Reasoning in Language Models"): runs the
        SAME question through the LLM `n` times independently (in parallel,
        so this doesn't take n times as long), extracts a comparable
        "answer signature" from each response (any numbers found, or a
        normalized text prefix), and majority-votes on it.

        Returns (best_answer_text, agreement_ratio, all_answers). A higher
        agreement_ratio (e.g. 3/3) means the model was consistent across
        independent attempts — a genuine (if imperfect) confidence signal
        used in real LLM research, not a cosmetic label.
        """
        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(self.prompt_ai, system_prompt, math_context) for _ in range(n)]
            answers = [f.result() for f in futures]
        answers = [a for a in answers if a]

        if not answers:
            return None, 0.0, []

        sigs = [_answer_signature(a) for a in answers]
        winning_sig, winning_count = Counter(sigs).most_common(1)[0]
        best_answer = next(a for a, s in zip(answers, sigs) if s == winning_sig)
        agreement = winning_count / len(answers)
        return best_answer, agreement, answers

    def run_agent(self, system_prompt: str, user_message: str, tools: list, execute_tool, max_iterations: int = 5):
        """Runs the standard OpenAI/Groq agentic tool-calling loop for
        compound questions ("factor 360, then find its gcd with 48, then
        the determinant of [[2,1],[1,3]]"):

          1. Send the question + tool schemas to the LLM.
          2. If the LLM requests tool call(s), execute each via `execute_tool`
             (the REAL Python dispatcher — the LLM never does the math
             itself, it only decides which tool to call and with what
             arguments).
          3. Feed the real results back to the LLM.
          4. Repeat until the LLM gives a final text answer (or the
             iteration cap is hit, as a safety valve against loops).

        Returns (final_answer_text, tool_call_log) where tool_call_log is a
        list of {"tool": name, "arguments": ..., "result": ...} — full
        transparency into exactly which real computations backed the
        answer, so nothing is a hidden/unverifiable LLM claim.
        """
        provider = next((p for p in self._providers if p.is_configured), None)
        if provider is None:
            return None, []

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        tool_call_log = []

        for _ in range(max_iterations):
            message = provider.call_raw(messages, self.timeout_s, tools=tools)
            if message is None:
                return None, tool_call_log

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return message.get("content"), tool_call_log

            messages.append(message)
            for call in tool_calls:
                fn_name = call["function"]["name"]
                try:
                    fn_args = json.loads(call["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}
                result = execute_tool(fn_name, fn_args)
                tool_call_log.append({"tool": fn_name, "arguments": fn_args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                })

        # Hit the iteration cap — ask one more time without tools to force a final answer.
        message = provider.call_raw(messages, self.timeout_s, tools=None)
        return (message.get("content") if message else None), tool_call_log
