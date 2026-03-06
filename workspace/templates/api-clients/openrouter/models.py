"""
OpenRouter API Pydantic Models

Request and response types for OpenRouter API.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Message Types
# ============================================================================


class TextContent(BaseModel):
    """Text content part."""

    type: Literal["text"] = "text"
    text: str


class ImageUrl(BaseModel):
    """Image URL details."""

    url: str
    detail: str | None = "auto"


class ImageContent(BaseModel):
    """Image content part."""

    type: Literal["image_url"] = "image_url"
    image_url: ImageUrl


class Message(BaseModel):
    """Chat message."""

    role: Literal["user", "assistant", "system", "tool"]
    content: str | list[TextContent | ImageContent]
    name: str | None = None
    tool_call_id: str | None = None


# ============================================================================
# Tool Types
# ============================================================================


class FunctionParameters(BaseModel):
    """Function parameters schema."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class FunctionDescription(BaseModel):
    """Function description for tool calling."""

    name: str
    description: str | None = None
    parameters: FunctionParameters | dict[str, Any] = Field(
        default_factory=FunctionParameters
    )


class Tool(BaseModel):
    """Tool definition."""

    type: Literal["function"] = "function"
    function: FunctionDescription


class ToolChoiceFunction(BaseModel):
    """Specific function choice."""

    name: str


class ToolChoiceObject(BaseModel):
    """Tool choice object."""

    type: Literal["function"] = "function"
    function: ToolChoiceFunction


# ============================================================================
# Request Types
# ============================================================================


class ChatCompletionRequest(BaseModel):
    """Request body for chat completions."""

    model: str | None = None
    messages: list[Message]
    stream: bool = False

    # Generation parameters
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    repetition_penalty: float | None = None
    min_p: float | None = None
    top_a: float | None = None
    seed: int | None = None
    stop: str | list[str] | None = None

    # Response format
    response_format: dict[str, str] | None = None

    # Tool calling
    tools: list[Tool] | None = None
    tool_choice: Literal["none", "auto"] | ToolChoiceObject | None = None

    # OpenRouter-specific
    transforms: list[str] | None = None
    models: list[str] | None = None
    route: Literal["fallback"] | None = None
    provider: dict[str, Any] | None = None
    user: str | None = None


# ============================================================================
# Response Types
# ============================================================================


class FunctionCall(BaseModel):
    """Function call in response."""

    name: str
    arguments: str


class ToolCall(BaseModel):
    """Tool call in response."""

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class ResponseMessage(BaseModel):
    """Message in response."""

    role: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class Choice(BaseModel):
    """Choice in response."""

    index: int = 0
    finish_reason: str | None = None
    native_finish_reason: str | None = None
    message: ResponseMessage | None = None
    delta: ResponseMessage | None = None


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Response from chat completions."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage | None = None
    system_fingerprint: str | None = None


class ErrorResponse(BaseModel):
    """Error response from API."""

    code: int
    message: str
    metadata: dict[str, Any] | None = None


# ============================================================================
# Generation Stats
# ============================================================================


class GenerationStats(BaseModel):
    """Generation statistics from /api/v1/generation endpoint."""

    id: str
    model: str | None = None
    total_cost: float | None = None
    origin: str | None = None
    usage: Usage | None = None
    created_at: str | None = None
    provider_name: str | None = None
    latency: int | None = None
    moderation_latency: int | None = None
    generation_time: int | None = None
    finish_reason: str | None = None
    native_tokens_prompt: int | None = None
    native_tokens_completion: int | None = None
    num_media_prompt: int | None = None
    num_media_completion: int | None = None
    app_id: int | None = None
    streamed: bool | None = None
    cancelled: bool | None = None
    tokens_prompt: int | None = None
    tokens_completion: int | None = None


class GenerationResponse(BaseModel):
    """Response from generation stats endpoint."""

    data: GenerationStats


# ============================================================================
# Models List
# ============================================================================


class ModelPricing(BaseModel):
    """Model pricing information."""

    prompt: str
    completion: str
    image: str | None = None
    request: str | None = None


class ModelInfo(BaseModel):
    """Model information."""

    id: str
    name: str
    created: int | None = None
    description: str | None = None
    context_length: int | None = None
    architecture: dict[str, Any] | None = None
    pricing: ModelPricing | None = None
    top_provider: dict[str, Any] | None = None
    per_request_limits: dict[str, Any] | None = None


class ModelsResponse(BaseModel):
    """Response from models list endpoint."""

    data: list[ModelInfo]
