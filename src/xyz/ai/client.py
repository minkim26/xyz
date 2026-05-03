"""Gemini API client wrapper for XYZ.

Provides a single shared client instance that all AI functions use.
Handles key loading, error handling, and graceful fallback when no
API key is configured.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from google import genai
from google.genai import types
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash-lite"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 8192


class GeminiClient:
    """Async wrapper around the Google GenAI SDK.

    Usage::

        client = GeminiClient()          # reads GEMINI_API_KEY from env
        if client.is_available:
            text = await client.generate("Explain numpy")
    """

    _instance: Optional["GeminiClient"] = None

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client: genai.Client | None = None

        if self._api_key:
            try:
                self._client = genai.Client(api_key=self._api_key)
                logger.info("Gemini client initialised (model=%s)", MODEL)
            except Exception:
                logger.exception("Failed to initialise Gemini client")
                self._client = None
        else:
            logger.info(
                "No GEMINI_API_KEY found -- AI features disabled. "
                "Set the GEMINI_API_KEY environment variable to enable."
            )

        # Track timestamps of requests for local rate limiting
        self._request_timestamps: list[float] = []

    def _check_rate_limit(self) -> bool:
        """Enforce a strict 14 requests per minute limit locally.
        
        This prevents burning quota on failed API calls when we know 
        we'll get a 429 anyway.
        """
        now = time.time()
        # Keep only timestamps from the last 60 seconds
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]
        
        # Limit to 14 requests per rolling 60s window
        if len(self._request_timestamps) >= 14:
            return False
            
        self._request_timestamps.append(now)
        return True

    # -- Singleton accessor --------------------------------------------------

    @classmethod
    def get_instance(cls, api_key: str | None = None) -> "GeminiClient":
        """Return the shared client instance, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls(api_key=api_key)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton -- mainly useful for testing."""
        cls._instance = None

    # -- Public API ----------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when a valid API key was provided and the client is ready."""
        return self._client is not None

    async def stream_generate(
        self,
        prompt: str,
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """Stream a prompt to Gemini, yielding text chunks as they arrive.

        Yields a single error string (never raises) so callers can always
        display something in the detail pane.
        """
        if not self.is_available:
            yield (
                "AI features are offline.\n"
                "Set the GEMINI_API_KEY environment variable to enable "
                "package explanations."
            )
            return

        if not self._check_rate_limit():
            logger.warning("Local rate limit hit (preventing API call)")
            yield "Rate limit reached — please wait a moment before asking AI."
            return

        try:
            async for chunk in await self._client.aio.models.generate_content_stream(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            error_str = str(exc).lower()
            if "rate limit" in error_str or "quota exceeded" in error_str or "429" in error_str:
                logger.warning("Gemini rate limit hit: %s", exc)
                yield "Rate limit reached — please wait a moment and try again."
            elif "api key" in error_str or "401" in error_str or "403" in error_str:
                logger.error("Gemini auth error: %s", exc)
                yield "Invalid API key. Check your GEMINI_API_KEY environment variable."
            else:
                logger.exception("Gemini streaming error")
                yield f"AI request failed: {exc}"

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str:
        """Send a prompt to Gemini and return the response text.

        Returns a user-friendly error string (never raises) so the TUI
        can always display *something* in the detail pane.
        """
        if not self.is_available:
            return (
                "AI features are offline.\n"
                "Set the GEMINI_API_KEY environment variable to enable "
                "package explanations."
            )

        if not self._check_rate_limit():
            logger.warning("Local rate limit hit (preventing API call)")
            return "Rate limit reached — please wait a moment before asking AI."

        try:
            response = await self._client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            text = response.text
            if not text:
                return "Gemini returned an empty response. Try again."
            return text.strip()
        except Exception as exc:
            error_str = str(exc).lower()
            if "rate limit" in error_str or "quota exceeded" in error_str or "429" in error_str:
                logger.warning("Gemini rate limit hit: %s", exc)
                return "Rate limit reached — please wait a moment and try again."
            if "api key" in error_str or "401" in error_str or "403" in error_str:
                logger.error("Gemini auth error: %s", exc)
                return "Invalid API key. Check your GEMINI_API_KEY environment variable."
            logger.exception("Gemini API error")
            return f"AI request failed: {exc}"
