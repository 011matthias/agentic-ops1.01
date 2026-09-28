"""Gemini as the receipt reader (backlog item 239, owner decision 2026-09-28).

Dirk asked for Google's Gemini to read receipts instead of OpenAI, supplying a
key on a billed project. Only the READING changes: the prompt, the
untrusted-data fences, the response schema, the extraction cache and the
parser stay the ones `OpenAIClient.extract_receipt` already uses, and every
other model call (categories, FX and ambiguity judgments) stays on OpenAI.
This module is the one network call; `OpenAIClient` decides when to use it.

The switch is OFF unless configured, so a deploy changes nothing:

* config: ``cfg["llm"]["receipt_reader"] = {"provider": "gemini",
  "model": "gemini-3.8-flash", "reads": "images" | "all",
  "api_key_env": "GEMINI_API_KEY", "thinking_level": "low"}`` (all but
  ``reads`` optional);
* or the environment, for the hosted app: ``EXPENSE_RECON_GEMINI_READS``
  (``images`` = photos, scanned PDFs and rendered mail bodies; ``all`` = also
  PDFs that carry a text layer; anything else = off), with
  ``EXPENSE_RECON_GEMINI_MODEL`` and ``EXPENSE_RECON_GEMINI_THINKING``.

A config block wins over the environment. The key is read from
``GEMINI_API_KEY`` (or the block's ``api_key_env``) and travels in the
``x-goog-api-key`` header, never in the URL: Google's error pages echo the
request address, and one such page was found holding the key on 2026-09-27.

Fail-open by design: a reading Gemini cannot give (rate limit or outage after
the retries, a refused or truncated answer, JSON the parser rejects) raises
`ReaderUnavailable`, and the caller reads that document with OpenAI instead.
A receipt is never lost or stalled because the second provider had a bad
minute; the log says which provider answered.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_KEY_ENV = "GEMINI_API_KEY"

# What the switch can name, and what each covers. "image" = every read that
# sends pictures (photos, scanned PDFs, the tool's own rendered mail bodies);
# "text" = PDFs with a text layer, which are read as their extracted text.
READS: dict[str, tuple[str, ...]] = {
    "images": ("image",),
    "all": ("image", "text"),
}

# Transient answers worth a retry; anything else is final for this document.
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class ReaderUnavailable(RuntimeError):
    """Gemini gave no usable reading for this document; read it with OpenAI."""


@dataclass(frozen=True)
class ReaderResult:
    """One reading: the raw JSON the model returned, plus billable tokens."""

    payload: str
    input_tokens: int
    output_tokens: int  # includes the model's thinking tokens (billed as output)
    cached_tokens: int = 0


# (url, headers, body, timeout) -> (HTTP status, decoded JSON body)
Post = Callable[[str, dict, dict, float], tuple[int, dict]]


def _urllib_post(url: str, headers: dict, body: dict, timeout: float) -> tuple[int, dict]:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https host
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read() or b"{}"
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"error": {"message": raw[:200].decode("utf-8", "replace")}}


class GeminiReader:
    """Reads one receipt with Gemini through the generateContent REST call."""

    provider = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        reads: str = "images",
        thinking_level: str | None = None,
        attempts: int = 3,
        backoff_s: tuple[float, ...] = (2.0, 6.0),
        timeout_s: float = 120.0,
        post: Post | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not api_key:
            raise ValueError("GeminiReader needs an API key")
        if reads not in READS:
            raise ValueError(f"reads must be one of {sorted(READS)}, got {reads!r}")
        self._api_key = api_key
        self.model = model
        self.reads = reads
        self.paths = READS[reads]
        self.thinking_level = thinking_level or None
        self.attempts = max(1, attempts)
        self.backoff_s = backoff_s
        self.timeout_s = timeout_s
        self._post = post or _urllib_post
        self._sleep = sleep

    def takes(self, *, is_text: bool) -> bool:
        """Whether this reader covers a text-layer read (True) or a picture read."""
        return ("text" if is_text else "image") in self.paths

    def describe(self) -> dict:
        """What the reader is, for logs and /healthz. Never includes the key."""
        out = {"provider": self.provider, "model": self.model, "reads": self.reads}
        if self.thinking_level:
            out["thinking_level"] = self.thinking_level
        return out

    def request_body(
        self,
        *,
        system: str,
        prompt_text: str,
        images: list[tuple[bytes, str]] | None,
        schema: dict,
    ) -> dict:
        """The exact JSON sent. Public so a test can assert what reaches Gemini."""
        parts: list[dict] = [{"text": prompt_text}]
        for raw, mime in images or []:
            parts.append({"inlineData": {
                "mimeType": mime,
                "data": base64.b64encode(raw).decode("ascii"),
            }})
        generation: dict = {
            # `responseFormat` is the current structured-output field;
            # `responseSchema` / `responseJsonSchema` are deprecated. The enum
            # spelling is required: "application/json" is refused with a 400
            # (probed 2026-09-28 on 3.8 Flash and 3.1 Pro).
            "responseFormat": {"text": {"mimeType": "APPLICATION_JSON", "schema": schema}},
        }
        # Temperature is left at Google's default: its guidance for Gemini 3 is
        # 1.0, and lower values are documented to loop or degrade.
        if self.thinking_level:
            generation["thinkingConfig"] = {"thinkingLevel": self.thinking_level}
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation,
        }

    def read(
        self,
        *,
        system: str,
        prompt_text: str,
        images: list[tuple[bytes, str]] | None,
        schema: dict,
    ) -> ReaderResult:
        body = self.request_body(
            system=system, prompt_text=prompt_text, images=images, schema=schema
        )
        url = GEMINI_ENDPOINT.format(model=self.model)
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._api_key}
        last = "no attempt made"
        for attempt in range(1, self.attempts + 1):
            try:
                status, data = self._post(url, headers, body, self.timeout_s)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                status, data = 0, {"error": {"message": f"{type(exc).__name__}: {exc}"}}
            if status == 200:
                return self._result(data)
            message = ((data or {}).get("error") or {}).get("message") or ""
            last = f"HTTP {status}: {message[:160]}"
            if (status in _RETRY_STATUS or status == 0) and attempt < self.attempts:
                self._sleep(self.backoff_s[min(attempt - 1, len(self.backoff_s) - 1)])
                continue
            break
        raise ReaderUnavailable(last)

    def _result(self, data: dict) -> ReaderResult:
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise ReaderUnavailable(f"prompt blocked: {block}")
        candidates = data.get("candidates") or []
        if not candidates:
            raise ReaderUnavailable("no candidate returned")
        first = candidates[0]
        finish = first.get("finishReason")
        if finish not in (None, "STOP"):
            # MAX_TOKENS, SAFETY, RECITATION, ...: the JSON is cut or absent.
            raise ReaderUnavailable(f"finishReason {finish}")
        parts = (first.get("content") or {}).get("parts") or []
        payload = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not payload.strip():
            raise ReaderUnavailable("empty answer")
        usage = data.get("usageMetadata") or {}
        return ReaderResult(
            payload=payload,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0)
            + int(usage.get("thoughtsTokenCount") or 0),
            cached_tokens=int(usage.get("cachedContentTokenCount") or 0),
        )


def _reader_block_from_env(environ: Mapping[str, str]) -> dict | None:
    reads = (environ.get("EXPENSE_RECON_GEMINI_READS") or "").strip().lower()
    if not reads or reads in ("0", "off", "none", "no", "false"):
        return None
    if reads not in READS:
        logger.warning(
            "EXPENSE_RECON_GEMINI_READS=%r is not one of %s; receipts stay on OpenAI",
            reads, sorted(READS),
        )
        return None
    block = {"provider": "gemini", "reads": reads}
    model = (environ.get("EXPENSE_RECON_GEMINI_MODEL") or "").strip()
    if model:
        block["model"] = model
    thinking = (environ.get("EXPENSE_RECON_GEMINI_THINKING") or "").strip().lower()
    if thinking:
        block["thinking_level"] = thinking
    return block


def reader_block(llm_cfg: Mapping | None, environ: Mapping[str, str] | None = None) -> dict | None:
    """The configured reader block: the config's own, else the environment's."""
    environ = os.environ if environ is None else environ
    block = llm_cfg.get("receipt_reader") if isinstance(llm_cfg, Mapping) else None
    if isinstance(block, Mapping):
        return dict(block)
    return _reader_block_from_env(environ)


def receipt_reader_from_config(
    llm_cfg: Mapping | None,
    environ: Mapping[str, str] | None = None,
    **reader_kwargs,
) -> GeminiReader | None:
    """Build the Gemini reader the config or environment asks for, or None.

    A block naming another provider or an unknown ``reads`` value raises
    ValueError (a config mistake should be loud). A missing key only warns
    and returns None: receipts keep being read, by OpenAI.
    """
    environ = os.environ if environ is None else environ
    block = reader_block(llm_cfg, environ)
    if not block:
        return None
    provider = block.get("provider", "gemini")
    if provider != "gemini":
        raise ValueError(f"receipt_reader provider {provider!r} not supported (only 'gemini')")
    reads = str(block.get("reads", "images")).strip().lower()
    if reads not in READS:
        raise ValueError(f"receipt_reader reads must be one of {sorted(READS)}, got {reads!r}")
    key_env = block.get("api_key_env") or DEFAULT_KEY_ENV
    key = (environ.get(key_env) or "").strip()
    if not key:
        logger.warning(
            "Gemini receipt reader is switched on (%s) but %s is not set; "
            "receipts stay on OpenAI", reads, key_env,
        )
        return None
    return GeminiReader(
        api_key=key,
        model=block.get("model") or DEFAULT_GEMINI_MODEL,
        reads=reads,
        thinking_level=block.get("thinking_level"),
        **reader_kwargs,
    )


def receipt_reader_status(environ: Mapping[str, str] | None = None) -> dict:
    """What the hosted app's environment switches on, for /healthz.

    ``{"reads": "off"}`` when off; otherwise the provider, model, what it
    reads, and whether its key is present. Never the key itself.
    """
    environ = os.environ if environ is None else environ
    block = _reader_block_from_env(environ)
    if not block:
        return {"reads": "off"}
    key_env = DEFAULT_KEY_ENV
    status = {
        "provider": "gemini",
        "model": block.get("model") or DEFAULT_GEMINI_MODEL,
        "reads": block["reads"],
        "key_set": bool((environ.get(key_env) or "").strip()),
    }
    if block.get("thinking_level"):
        status["thinking_level"] = block["thinking_level"]
    return status
