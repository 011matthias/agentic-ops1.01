"""
OpenRouter API Client

Unified API for accessing hundreds of AI models through a single endpoint.

Usage:
    from openrouter import OpenRouterClient

    client = OpenRouterClient(api_key="sk-or-...")

    # Simple chat completion
    response = client.chat(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

    # Async client
    from openrouter import AsyncOpenRouterClient

    async with AsyncOpenRouterClient(api_key="sk-or-...") as client:
        response = await client.chat(
            model="anthropic/claude-3-opus",
            messages=[{"role": "user", "content": "Hello!"}]
        )
"""

from .client import (
    AsyncOpenRouterClient,
    AuthenticationError,
    InsufficientCreditsError,
    OpenRouterClient,
    OpenRouterError,
    RateLimitError,
)
from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    FunctionCall,
    FunctionDescription,
    GenerationResponse,
    GenerationStats,
    Message,
    ModelInfo,
    ModelsResponse,
    ResponseMessage,
    Tool,
    ToolCall,
    Usage,
)

__all__ = [
    # Clients
    "OpenRouterClient",
    "AsyncOpenRouterClient",
    # Errors
    "OpenRouterError",
    "AuthenticationError",
    "RateLimitError",
    "InsufficientCreditsError",
    # Request types
    "ChatCompletionRequest",
    "Message",
    "Tool",
    "FunctionDescription",
    # Response types
    "ChatCompletionResponse",
    "Choice",
    "ResponseMessage",
    "ToolCall",
    "FunctionCall",
    "Usage",
    "GenerationResponse",
    "GenerationStats",
    "ModelInfo",
    "ModelsResponse",
]
