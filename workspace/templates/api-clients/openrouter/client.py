"""
OpenRouter API Client

Unified API for accessing hundreds of AI models through a single endpoint.
https://openrouter.ai/docs
"""

from typing import Any, Iterator
from urllib.parse import urljoin

import httpx

from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    GenerationResponse,
    Message,
    ModelInfo,
    ModelsResponse,
    ResponseMessage,
    Tool,
    Usage,
)


class OpenRouterError(Exception):
    """Base exception for OpenRouter API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: int | None = None,
        response: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response = response


class AuthenticationError(OpenRouterError):
    """Authentication failed (401)."""

    pass


class RateLimitError(OpenRouterError):
    """Rate limit exceeded (429)."""

    pass


class InsufficientCreditsError(OpenRouterError):
    """Insufficient credits (402)."""

    pass


class OpenRouterClient:
    """
    OpenRouter API client.

    Provides access to hundreds of AI models through a unified API.

    Usage:
        client = OpenRouterClient(api_key="sk-or-...")

        # Simple chat completion
        response = client.chat(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(response.choices[0].message.content)

        # With streaming
        for chunk in client.chat_stream(
            model="anthropic/claude-3-opus",
            messages=[{"role": "user", "content": "Tell me a story"}]
        ):
            print(chunk.choices[0].delta.content, end="")
    """

    BASE_URL = "https://openrouter.ai/api/v1/"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        base_url: str | None = None,
        app_name: str | None = None,
        app_url: str | None = None,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: Your OpenRouter API key (from openrouter.ai/keys)
            timeout: Request timeout in seconds (default 60s for LLM calls)
            base_url: Optional custom base URL
            app_name: Optional app name for attribution (X-Title header)
            app_url: Optional app URL for attribution (HTTP-Referer header)
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.app_name = app_name
        self.app_url = app_url
        self._client = httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.app_name:
            headers["X-Title"] = self.app_name
        if self.app_url:
            headers["HTTP-Referer"] = self.app_url
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make authenticated request to OpenRouter API."""
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        try:
            response = self._client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            self._handle_error(e)

    def _handle_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors with specific exception types."""
        status = error.response.status_code
        try:
            data = error.response.json()
            message = data.get("error", {}).get("message", error.response.text)
            code = data.get("error", {}).get("code")
        except Exception:
            message = error.response.text
            code = None

        if status == 401:
            raise AuthenticationError(
                message=message,
                status_code=status,
                error_code=code,
                response=error.response,
            )
        elif status == 402:
            raise InsufficientCreditsError(
                message=message,
                status_code=status,
                error_code=code,
                response=error.response,
            )
        elif status == 429:
            raise RateLimitError(
                message=message,
                status_code=status,
                error_code=code,
                response=error.response,
            )
        else:
            raise OpenRouterError(
                message=f"HTTP {status}: {message}",
                status_code=status,
                error_code=code,
                response=error.response,
            )

    # ========================================================================
    # Chat Completions
    # ========================================================================

    def chat(
        self,
        messages: list[dict[str, Any] | Message],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools: list[dict[str, Any] | Tool] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ChatCompletionResponse:
        """
        Create a chat completion.

        Args:
            messages: List of messages in the conversation
            model: Model ID (e.g., "openai/gpt-4o", "anthropic/claude-3-opus")
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            response_format: Force JSON output with {"type": "json_object"}
            tools: List of tools for function calling
            tool_choice: Control tool selection ("auto", "none", or specific)
            **kwargs: Additional parameters (see API docs)

        Returns:
            ChatCompletionResponse with generated text
        """
        # Convert Message objects to dicts if needed
        msg_list = [
            m.model_dump() if isinstance(m, Message) else m for m in messages
        ]
        tool_list = None
        if tools:
            tool_list = [
                t.model_dump() if isinstance(t, Tool) else t for t in tools
            ]

        payload = {
            "messages": msg_list,
            "stream": False,
        }
        if model:
            payload["model"] = model
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if stop:
            payload["stop"] = stop
        if response_format:
            payload["response_format"] = response_format
        if tool_list:
            payload["tools"] = tool_list
        if tool_choice:
            payload["tool_choice"] = tool_choice
        payload.update(kwargs)

        data = self._request("POST", "chat/completions", json=payload)
        return ChatCompletionResponse.model_validate(data)

    def chat_stream(
        self,
        messages: list[dict[str, Any] | Message],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatCompletionResponse]:
        """
        Create a streaming chat completion.

        Args:
            messages: List of messages in the conversation
            model: Model ID
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Yields:
            ChatCompletionResponse chunks with delta content
        """
        msg_list = [
            m.model_dump() if isinstance(m, Message) else m for m in messages
        ]

        payload = {
            "messages": msg_list,
            "stream": True,
        }
        if model:
            payload["model"] = model
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        payload.update(kwargs)

        url = urljoin(self.base_url, "chat/completions")

        with self._client.stream(
            "POST",
            url,
            headers=self._headers(),
            json=payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    if data_str.strip().startswith(":"):
                        # Comment/keepalive, ignore
                        continue
                    try:
                        import json
                        data = json.loads(data_str)
                        yield ChatCompletionResponse.model_validate(data)
                    except Exception:
                        continue

    # ========================================================================
    # Models
    # ========================================================================

    def list_models(self) -> list[ModelInfo]:
        """
        List available models.

        Returns:
            List of available model information
        """
        data = self._request("GET", "models")
        response = ModelsResponse.model_validate(data)
        return response.data

    def get_model(self, model_id: str) -> ModelInfo | None:
        """
        Get information about a specific model.

        Args:
            model_id: Model ID (e.g., "openai/gpt-4o")

        Returns:
            Model information or None if not found
        """
        models = self.list_models()
        for model in models:
            if model.id == model_id:
                return model
        return None

    # ========================================================================
    # Generation Stats
    # ========================================================================

    def get_generation(self, generation_id: str) -> GenerationResponse:
        """
        Get generation statistics.

        Use the ID from a chat completion response to get detailed
        stats including native token counts and cost.

        Args:
            generation_id: Generation ID from completion response

        Returns:
            Generation statistics including cost and tokens
        """
        data = self._request("GET", "generation", params={"id": generation_id})
        return GenerationResponse.model_validate(data)

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "OpenRouterClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncOpenRouterClient:
    """
    Async OpenRouter API client.

    Usage:
        async with AsyncOpenRouterClient(api_key="sk-or-...") as client:
            response = await client.chat(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": "Hello!"}]
            )
    """

    BASE_URL = "https://openrouter.ai/api/v1/"

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        base_url: str | None = None,
        app_name: str | None = None,
        app_url: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.app_name = app_name
        self.app_url = app_url
        self._client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.app_name:
            headers["X-Title"] = self.app_name
        if self.app_url:
            headers["HTTP-Referer"] = self.app_url
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            self._handle_error(e)

    def _handle_error(self, error: httpx.HTTPStatusError) -> None:
        status = error.response.status_code
        try:
            data = error.response.json()
            message = data.get("error", {}).get("message", error.response.text)
            code = data.get("error", {}).get("code")
        except Exception:
            message = error.response.text
            code = None

        if status == 401:
            raise AuthenticationError(message, status, code, error.response)
        elif status == 402:
            raise InsufficientCreditsError(message, status, code, error.response)
        elif status == 429:
            raise RateLimitError(message, status, code, error.response)
        else:
            raise OpenRouterError(f"HTTP {status}: {message}", status, code, error.response)

    async def chat(
        self,
        messages: list[dict[str, Any] | Message],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools: list[dict[str, Any] | Tool] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ChatCompletionResponse:
        """Create a chat completion."""
        msg_list = [
            m.model_dump() if isinstance(m, Message) else m for m in messages
        ]
        tool_list = None
        if tools:
            tool_list = [
                t.model_dump() if isinstance(t, Tool) else t for t in tools
            ]

        payload = {"messages": msg_list, "stream": False}
        if model:
            payload["model"] = model
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if stop:
            payload["stop"] = stop
        if response_format:
            payload["response_format"] = response_format
        if tool_list:
            payload["tools"] = tool_list
        if tool_choice:
            payload["tool_choice"] = tool_choice
        payload.update(kwargs)

        data = await self._request("POST", "chat/completions", json=payload)
        return ChatCompletionResponse.model_validate(data)

    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        data = await self._request("GET", "models")
        response = ModelsResponse.model_validate(data)
        return response.data

    async def get_generation(self, generation_id: str) -> GenerationResponse:
        """Get generation statistics."""
        data = await self._request("GET", "generation", params={"id": generation_id})
        return GenerationResponse.model_validate(data)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncOpenRouterClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
