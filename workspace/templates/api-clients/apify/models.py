"""
Apify API - Pydantic Models

Generated from OpenAPI spec: https://docs.apify.com/api/openapi.json
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# === Enums ===


class ActorRunStatus(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMING_OUT = "TIMING-OUT"
    TIMED_OUT = "TIMED-OUT"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"


class BuildStatus(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class SourceType(str, Enum):
    SOURCE_FILES = "SOURCE_FILES"
    GIT_REPO = "GIT_REPO"
    TARBALL = "TARBALL"
    GITHUB_GIST = "GITHUB_GIST"


class WebhookEventType(str, Enum):
    ACTOR_RUN_CREATED = "ACTOR.RUN.CREATED"
    ACTOR_RUN_SUCCEEDED = "ACTOR.RUN.SUCCEEDED"
    ACTOR_RUN_FAILED = "ACTOR.RUN.FAILED"
    ACTOR_RUN_TIMED_OUT = "ACTOR.RUN.TIMED_OUT"
    ACTOR_RUN_ABORTED = "ACTOR.RUN.ABORTED"
    ACTOR_RUN_RESURRECTED = "ACTOR.RUN.RESURRECTED"
    ACTOR_BUILD_CREATED = "ACTOR.BUILD.CREATED"
    ACTOR_BUILD_SUCCEEDED = "ACTOR.BUILD.SUCCEEDED"
    ACTOR_BUILD_FAILED = "ACTOR.BUILD.FAILED"
    ACTOR_BUILD_ABORTED = "ACTOR.BUILD.ABORTED"


# === Base Models ===


class PaginatedList(BaseModel):
    """Base model for paginated list responses."""

    total: int
    offset: int
    limit: int
    count: int
    desc: bool


# === Actor Models ===


class ActorStats(BaseModel):
    total_builds: int = Field(alias="totalBuilds")
    total_runs: int = Field(alias="totalRuns")
    total_users: int = Field(alias="totalUsers")
    total_users_7_days: int = Field(alias="totalUsers7Days")
    total_users_30_days: int = Field(alias="totalUsers30Days")
    total_users_90_days: int = Field(alias="totalUsers90Days")
    last_run_started_at: Optional[datetime] = Field(None, alias="lastRunStartedAt")

    model_config = {"populate_by_name": True}


class DefaultRunOptions(BaseModel):
    build: Optional[str] = None
    timeout_secs: Optional[int] = Field(None, alias="timeoutSecs")
    memory_mbytes: Optional[int] = Field(None, alias="memoryMbytes")

    model_config = {"populate_by_name": True}


class ActorVersion(BaseModel):
    version_number: str = Field(alias="versionNumber")
    source_type: SourceType = Field(alias="sourceType")
    env_vars: Optional[list[dict[str, Any]]] = Field(None, alias="envVars")
    apply_env_vars_to_build: Optional[bool] = Field(None, alias="applyEnvVarsToBuild")
    build_tag: Optional[str] = Field(None, alias="buildTag")
    source_files: Optional[list[dict[str, Any]]] = Field(None, alias="sourceFiles")
    git_repo_url: Optional[str] = Field(None, alias="gitRepoUrl")
    tarball_url: Optional[str] = Field(None, alias="tarballUrl")

    model_config = {"populate_by_name": True}


class Actor(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    name: str
    username: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None
    is_public: bool = Field(alias="isPublic")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    stats: Optional[ActorStats] = None
    versions: Optional[list[ActorVersion]] = None
    default_run_options: Optional[DefaultRunOptions] = Field(
        None, alias="defaultRunOptions"
    )

    model_config = {"populate_by_name": True}


class ActorListItem(BaseModel):
    id: str
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    name: str
    username: Optional[str] = None
    title: Optional[str] = None
    is_public: bool = Field(alias="isPublic")
    stats: Optional[ActorStats] = None

    model_config = {"populate_by_name": True}


class ActorList(PaginatedList):
    items: list[ActorListItem]


# === Actor Run Models ===


class RunStats(BaseModel):
    input_body_len: Optional[int] = Field(None, alias="inputBodyLen")
    reboot_count: int = Field(0, alias="rebootCount")
    restart_count: int = Field(0, alias="restartCount")
    duration_millis: Optional[int] = Field(None, alias="durationMillis")
    run_time_secs: Optional[float] = Field(None, alias="runTimeSecs")
    metamorph: Optional[int] = None
    compute_units: Optional[float] = Field(None, alias="computeUnits")
    memory_avg_bytes: Optional[int] = Field(None, alias="memoryAvgBytes")
    memory_max_bytes: Optional[int] = Field(None, alias="memoryMaxBytes")
    cpu_avg_usage: Optional[float] = Field(None, alias="cpuAvgUsage")
    cpu_max_usage: Optional[float] = Field(None, alias="cpuMaxUsage")
    cpu_current_usage: Optional[float] = Field(None, alias="cpuCurrentUsage")
    memory_current_bytes: Optional[int] = Field(None, alias="memoryCurrentBytes")

    model_config = {"populate_by_name": True}


class RunOptions(BaseModel):
    build: Optional[str] = None
    timeout_secs: Optional[int] = Field(None, alias="timeoutSecs")
    memory_mbytes: Optional[int] = Field(None, alias="memoryMbytes")
    disk_mbytes: Optional[int] = Field(None, alias="diskMbytes")

    model_config = {"populate_by_name": True}


class Run(BaseModel):
    id: str
    act_id: str = Field(alias="actId")
    user_id: str = Field(alias="userId")
    started_at: datetime = Field(alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")
    status: ActorRunStatus
    status_message: Optional[str] = Field(None, alias="statusMessage")
    is_status_message_terminal: Optional[bool] = Field(
        None, alias="isStatusMessageTerminal"
    )
    meta: Optional[dict[str, Any]] = None
    stats: Optional[RunStats] = None
    options: Optional[RunOptions] = None
    build_id: str = Field(alias="buildId")
    build_number: str = Field(alias="buildNumber")
    exit_code: Optional[int] = Field(None, alias="exitCode")
    default_key_value_store_id: str = Field(alias="defaultKeyValueStoreId")
    default_dataset_id: str = Field(alias="defaultDatasetId")
    default_request_queue_id: str = Field(alias="defaultRequestQueueId")
    container_url: Optional[str] = Field(None, alias="containerUrl")

    model_config = {"populate_by_name": True}


class RunListItem(BaseModel):
    id: str
    act_id: str = Field(alias="actId")
    user_id: str = Field(alias="userId")
    started_at: datetime = Field(alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")
    status: ActorRunStatus
    build_id: str = Field(alias="buildId")
    build_number: str = Field(alias="buildNumber")

    model_config = {"populate_by_name": True}


class RunList(PaginatedList):
    items: list[RunListItem]


# === Build Models ===


class Build(BaseModel):
    id: str
    act_id: str = Field(alias="actId")
    user_id: str = Field(alias="userId")
    started_at: datetime = Field(alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")
    status: BuildStatus
    meta: Optional[dict[str, Any]] = None
    stats: Optional[dict[str, Any]] = None
    options: Optional[dict[str, Any]] = None
    input_schema: Optional[str] = Field(None, alias="inputSchema")
    readme: Optional[str] = None
    build_number: str = Field(alias="buildNumber")

    model_config = {"populate_by_name": True}


class BuildListItem(BaseModel):
    id: str
    act_id: str = Field(alias="actId")
    status: BuildStatus
    started_at: datetime = Field(alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")
    build_number: str = Field(alias="buildNumber")

    model_config = {"populate_by_name": True}


class BuildList(PaginatedList):
    items: list[BuildListItem]


# === Task Models ===


class Task(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    act_id: str = Field(alias="actId")
    name: str
    username: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    options: Optional[RunOptions] = None
    input: Optional[dict[str, Any]] = None
    stats: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class TaskListItem(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    act_id: str = Field(alias="actId")
    name: str
    username: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")

    model_config = {"populate_by_name": True}


class TaskList(PaginatedList):
    items: list[TaskListItem]


# === Dataset Models ===


class Dataset(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    accessed_at: Optional[datetime] = Field(None, alias="accessedAt")
    item_count: int = Field(alias="itemCount")
    clean_item_count: Optional[int] = Field(None, alias="cleanItemCount")
    act_id: Optional[str] = Field(None, alias="actId")
    act_run_id: Optional[str] = Field(None, alias="actRunId")

    model_config = {"populate_by_name": True}


class DatasetListItem(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    item_count: int = Field(alias="itemCount")

    model_config = {"populate_by_name": True}


class DatasetList(PaginatedList):
    items: list[DatasetListItem]


# === Key-Value Store Models ===


class KeyValueStore(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    accessed_at: Optional[datetime] = Field(None, alias="accessedAt")
    act_id: Optional[str] = Field(None, alias="actId")
    act_run_id: Optional[str] = Field(None, alias="actRunId")

    model_config = {"populate_by_name": True}


class KeyValueStoreListItem(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")

    model_config = {"populate_by_name": True}


class KeyValueStoreList(PaginatedList):
    items: list[KeyValueStoreListItem]


class KeyRecord(BaseModel):
    key: str
    size: int


class KeyList(BaseModel):
    items: list[KeyRecord]
    count: int
    limit: int
    exclusive_start_key: Optional[str] = Field(None, alias="exclusiveStartKey")
    is_truncated: bool = Field(alias="isTruncated")
    next_exclusive_start_key: Optional[str] = Field(
        None, alias="nextExclusiveStartKey"
    )

    model_config = {"populate_by_name": True}


# === Request Queue Models ===


class RequestQueue(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    accessed_at: Optional[datetime] = Field(None, alias="accessedAt")
    total_request_count: int = Field(alias="totalRequestCount")
    handled_request_count: int = Field(alias="handledRequestCount")
    pending_request_count: int = Field(alias="pendingRequestCount")

    model_config = {"populate_by_name": True}


class QueueRequest(BaseModel):
    id: str
    url: str
    unique_key: str = Field(alias="uniqueKey")
    method: Optional[str] = None
    retry_count: int = Field(0, alias="retryCount")
    handled_at: Optional[datetime] = Field(None, alias="handledAt")
    user_data: Optional[dict[str, Any]] = Field(None, alias="userData")

    model_config = {"populate_by_name": True}


# === Schedule Models ===


class Schedule(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    name: str
    cron_expression: str = Field(alias="cronExpression")
    timezone: str
    is_enabled: bool = Field(alias="isEnabled")
    is_exclusive: bool = Field(alias="isExclusive")
    description: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    next_run_at: Optional[datetime] = Field(None, alias="nextRunAt")
    last_run_at: Optional[datetime] = Field(None, alias="lastRunAt")
    actions: Optional[list[dict[str, Any]]] = None

    model_config = {"populate_by_name": True}


class ScheduleListItem(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    name: str
    cron_expression: str = Field(alias="cronExpression")
    is_enabled: bool = Field(alias="isEnabled")
    created_at: datetime = Field(alias="createdAt")
    next_run_at: Optional[datetime] = Field(None, alias="nextRunAt")

    model_config = {"populate_by_name": True}


class ScheduleList(PaginatedList):
    items: list[ScheduleListItem]


# === Webhook Models ===


class Webhook(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    is_ad_hoc: bool = Field(alias="isAdHoc")
    event_types: list[WebhookEventType] = Field(alias="eventTypes")
    condition: Optional[dict[str, Any]] = None
    request_url: str = Field(alias="requestUrl")
    payload_template: Optional[str] = Field(None, alias="payloadTemplate")
    headers_template: Optional[str] = Field(None, alias="headersTemplate")
    description: Optional[str] = None
    last_dispatch: Optional[dict[str, Any]] = Field(None, alias="lastDispatch")
    stats: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class WebhookListItem(BaseModel):
    id: str
    created_at: datetime = Field(alias="createdAt")
    modified_at: datetime = Field(alias="modifiedAt")
    is_ad_hoc: bool = Field(alias="isAdHoc")
    event_types: list[WebhookEventType] = Field(alias="eventTypes")
    request_url: str = Field(alias="requestUrl")

    model_config = {"populate_by_name": True}


class WebhookList(PaginatedList):
    items: list[WebhookListItem]


# === User Models ===


class User(BaseModel):
    id: str
    username: str
    profile: Optional[dict[str, Any]] = None


class UserLimits(BaseModel):
    monthly_usage_cycle: dict[str, Any] = Field(alias="monthlyUsageCycle")
    limits: dict[str, Any]
    current: dict[str, Any]

    model_config = {"populate_by_name": True}


class MonthlyUsage(BaseModel):
    usage_cycle: dict[str, Any] = Field(alias="usageCycle")
    daily_service_usages: list[dict[str, Any]] = Field(alias="dailyServiceUsages")
    total_usage_credits_usd: float = Field(alias="totalUsageCreditsUsd")
    total_usage_credits_usd_before_volume_discount: Optional[float] = Field(
        None, alias="totalUsageCreditsUsdBeforeVolumeDiscount"
    )

    model_config = {"populate_by_name": True}


# === Request/Response Wrappers ===


class DataWrapper[T](BaseModel):
    """Generic wrapper for API responses."""

    data: T


class ErrorDetail(BaseModel):
    type: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# === Create/Update Request Models ===


class CreateActorRequest(BaseModel):
    name: str
    description: Optional[str] = None
    title: Optional[str] = None
    is_public: bool = Field(False, alias="isPublic")
    versions: Optional[list[ActorVersion]] = None
    default_run_options: Optional[DefaultRunOptions] = Field(
        None, alias="defaultRunOptions"
    )

    model_config = {"populate_by_name": True}


class UpdateActorRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    title: Optional[str] = None
    is_public: Optional[bool] = Field(None, alias="isPublic")
    default_run_options: Optional[DefaultRunOptions] = Field(
        None, alias="defaultRunOptions"
    )

    model_config = {"populate_by_name": True}


class CreateVersionRequest(BaseModel):
    version_number: str = Field(alias="versionNumber")
    source_type: SourceType = Field(alias="sourceType")
    env_vars: Optional[list[dict[str, Any]]] = Field(None, alias="envVars")
    apply_env_vars_to_build: Optional[bool] = Field(None, alias="applyEnvVarsToBuild")
    build_tag: Optional[str] = Field(None, alias="buildTag")
    source_files: Optional[list[dict[str, Any]]] = Field(None, alias="sourceFiles")
    git_repo_url: Optional[str] = Field(None, alias="gitRepoUrl")
    tarball_url: Optional[str] = Field(None, alias="tarballUrl")

    model_config = {"populate_by_name": True}


class CreateTaskRequest(BaseModel):
    act_id: str = Field(alias="actId")
    name: str
    options: Optional[RunOptions] = None
    input: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class UpdateTaskRequest(BaseModel):
    name: Optional[str] = None
    options: Optional[RunOptions] = None
    input: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class CreateScheduleRequest(BaseModel):
    name: str
    cron_expression: str = Field(alias="cronExpression")
    timezone: str = "UTC"
    is_enabled: bool = Field(True, alias="isEnabled")
    is_exclusive: bool = Field(True, alias="isExclusive")
    description: Optional[str] = None
    actions: list[dict[str, Any]]

    model_config = {"populate_by_name": True}


class CreateWebhookRequest(BaseModel):
    event_types: list[WebhookEventType] = Field(alias="eventTypes")
    request_url: str = Field(alias="requestUrl")
    payload_template: Optional[str] = Field(None, alias="payloadTemplate")
    headers_template: Optional[str] = Field(None, alias="headersTemplate")
    description: Optional[str] = None
    condition: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class CreateEnvVarRequest(BaseModel):
    name: str
    value: str
    is_secret: bool = Field(False, alias="isSecret")

    model_config = {"populate_by_name": True}


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    is_secret: bool = Field(alias="isSecret")

    model_config = {"populate_by_name": True}
