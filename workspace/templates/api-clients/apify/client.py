"""
Apify API Client

A typed Python client for the Apify API v2.
Uses httpx for HTTP requests and Pydantic for data validation.

Usage:
    from client import ApifyClient

    client = ApifyClient(token="your_api_token")

    # Run an actor
    run = client.run_actor("apify/web-scraper", input={"startUrls": [{"url": "https://example.com"}]})

    # Get dataset items
    items = client.get_dataset_items(run.default_dataset_id)
"""

from typing import Any, Literal, Optional, TypeVar

import httpx

from .models import (
    Actor,
    ActorList,
    ActorListItem,
    ActorVersion,
    Build,
    BuildList,
    CreateActorRequest,
    CreateEnvVarRequest,
    CreateScheduleRequest,
    CreateTaskRequest,
    CreateVersionRequest,
    CreateWebhookRequest,
    Dataset,
    DatasetList,
    EnvVar,
    KeyList,
    KeyValueStore,
    KeyValueStoreList,
    MonthlyUsage,
    QueueRequest,
    RequestQueue,
    Run,
    RunList,
    Schedule,
    ScheduleList,
    Task,
    TaskList,
    UpdateActorRequest,
    UpdateTaskRequest,
    User,
    UserLimits,
    Webhook,
    WebhookList,
)

T = TypeVar("T")


class ApifyError(Exception):
    """Base exception for Apify API errors."""

    def __init__(self, message: str, status_code: int, error_type: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(f"[{status_code}] {error_type}: {message}" if error_type else f"[{status_code}] {message}")


class ApifyClient:
    """
    Apify API v2 Client.

    Provides typed methods for interacting with the Apify platform.
    """

    BASE_URL = "https://api.apify.com"

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the Apify client.

        Args:
            token: Your Apify API token from https://console.apify.com/account#/integrations
            base_url: Override the base URL (default: https://api.apify.com)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.token = token
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> httpx.Response:
        """Make an HTTP request and handle errors."""
        # Filter None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = self._client.request(
            method,
            path,
            params=params,
            json=json_data,
            content=data,
            headers=headers,
        )

        if response.status_code >= 400:
            try:
                error_data = response.json()
                error = error_data.get("error", {})
                raise ApifyError(
                    message=error.get("message", response.text),
                    status_code=response.status_code,
                    error_type=error.get("type"),
                )
            except (ValueError, KeyError):
                raise ApifyError(
                    message=response.text,
                    status_code=response.status_code,
                )

        return response

    # === Actors ===

    def list_actors(
        self,
        *,
        my: Optional[bool] = None,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
    ) -> ActorList:
        """
        Get list of Actors.

        Args:
            my: If True, only return Actors owned by the user
            offset: Pagination offset
            limit: Maximum number of items to return (max 1000)
            desc: Sort in descending order
        """
        response = self._request(
            "GET",
            "/v2/acts",
            params={"my": my, "offset": offset, "limit": limit, "desc": desc},
        )
        return ActorList(**response.json()["data"])

    def get_actor(self, actor_id: str) -> Actor:
        """
        Get Actor details.

        Args:
            actor_id: Actor ID or username~actorname
        """
        response = self._request("GET", f"/v2/acts/{actor_id}")
        return Actor(**response.json()["data"])

    def create_actor(self, request: CreateActorRequest) -> Actor:
        """Create a new Actor."""
        response = self._request(
            "POST",
            "/v2/acts",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Actor(**response.json()["data"])

    def update_actor(self, actor_id: str, request: UpdateActorRequest) -> Actor:
        """Update an existing Actor."""
        response = self._request(
            "PUT",
            f"/v2/acts/{actor_id}",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Actor(**response.json()["data"])

    def delete_actor(self, actor_id: str) -> None:
        """Delete an Actor."""
        self._request("DELETE", f"/v2/acts/{actor_id}")

    # === Actor Versions ===

    def list_actor_versions(self, actor_id: str) -> list[ActorVersion]:
        """Get list of Actor versions."""
        response = self._request("GET", f"/v2/acts/{actor_id}/versions")
        return [ActorVersion(**v) for v in response.json()["data"]["items"]]

    def get_actor_version(self, actor_id: str, version_number: str) -> ActorVersion:
        """Get a specific Actor version."""
        response = self._request("GET", f"/v2/acts/{actor_id}/versions/{version_number}")
        return ActorVersion(**response.json()["data"])

    def create_actor_version(
        self, actor_id: str, request: CreateVersionRequest
    ) -> ActorVersion:
        """Create a new Actor version."""
        response = self._request(
            "POST",
            f"/v2/acts/{actor_id}/versions",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return ActorVersion(**response.json()["data"])

    def delete_actor_version(self, actor_id: str, version_number: str) -> None:
        """Delete an Actor version."""
        self._request("DELETE", f"/v2/acts/{actor_id}/versions/{version_number}")

    # === Environment Variables ===

    def list_env_vars(self, actor_id: str, version_number: str) -> list[EnvVar]:
        """Get list of environment variables for an Actor version."""
        response = self._request(
            "GET", f"/v2/acts/{actor_id}/versions/{version_number}/env-vars"
        )
        return [EnvVar(**v) for v in response.json()["data"]["items"]]

    def create_env_var(
        self, actor_id: str, version_number: str, request: CreateEnvVarRequest
    ) -> EnvVar:
        """Create an environment variable."""
        response = self._request(
            "POST",
            f"/v2/acts/{actor_id}/versions/{version_number}/env-vars",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return EnvVar(**response.json()["data"])

    def delete_env_var(
        self, actor_id: str, version_number: str, env_var_name: str
    ) -> None:
        """Delete an environment variable."""
        self._request(
            "DELETE",
            f"/v2/acts/{actor_id}/versions/{version_number}/env-vars/{env_var_name}",
        )

    # === Actor Runs ===

    def run_actor(
        self,
        actor_id: str,
        *,
        input: Optional[dict[str, Any]] = None,
        build: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        wait_for_finish: Optional[int] = None,
        webhooks: Optional[list[dict[str, Any]]] = None,
    ) -> Run:
        """
        Run an Actor.

        Args:
            actor_id: Actor ID or username~actorname
            input: Input data for the Actor
            build: Build tag or number to run
            timeout_secs: Timeout in seconds
            memory_mbytes: Memory limit in MB (128-32768)
            wait_for_finish: Wait for run to finish (max 60 seconds)
            webhooks: List of webhooks to trigger
        """
        response = self._request(
            "POST",
            f"/v2/acts/{actor_id}/runs",
            params={
                "build": build,
                "timeout": timeout_secs,
                "memory": memory_mbytes,
                "waitForFinish": wait_for_finish,
                "webhooks": webhooks,
            },
            json_data=input,
        )
        return Run(**response.json()["data"])

    def run_actor_sync(
        self,
        actor_id: str,
        *,
        input: Optional[dict[str, Any]] = None,
        build: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
    ) -> Any:
        """
        Run an Actor synchronously and return output.

        The run must complete within 300 seconds or it will timeout.
        """
        response = self._request(
            "POST",
            f"/v2/acts/{actor_id}/run-sync",
            params={
                "build": build,
                "timeout": timeout_secs,
                "memory": memory_mbytes,
            },
            json_data=input,
        )
        return response.json()

    def run_actor_sync_get_dataset_items(
        self,
        actor_id: str,
        *,
        input: Optional[dict[str, Any]] = None,
        build: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        format: Literal["json", "csv", "xlsx", "xml", "rss"] = "json",
    ) -> Any:
        """
        Run an Actor synchronously and return dataset items directly.
        """
        response = self._request(
            "POST",
            f"/v2/acts/{actor_id}/run-sync-get-dataset-items",
            params={
                "build": build,
                "timeout": timeout_secs,
                "memory": memory_mbytes,
                "format": format,
            },
            json_data=input,
        )
        if format == "json":
            return response.json()
        return response.content

    def get_run(self, run_id: str) -> Run:
        """Get run details."""
        response = self._request("GET", f"/v2/actor-runs/{run_id}")
        return Run(**response.json()["data"])

    def list_runs(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = True,
        status: Optional[str] = None,
    ) -> RunList:
        """Get list of runs for the user."""
        response = self._request(
            "GET",
            "/v2/actor-runs",
            params={"offset": offset, "limit": limit, "desc": desc, "status": status},
        )
        return RunList(**response.json()["data"])

    def list_actor_runs(
        self,
        actor_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = True,
    ) -> RunList:
        """Get list of runs for a specific Actor."""
        response = self._request(
            "GET",
            f"/v2/acts/{actor_id}/runs",
            params={"offset": offset, "limit": limit, "desc": desc},
        )
        return RunList(**response.json()["data"])

    def get_last_run(self, actor_id: str) -> Optional[Run]:
        """Get the last run for an Actor."""
        response = self._request("GET", f"/v2/acts/{actor_id}/runs/last")
        data = response.json().get("data")
        return Run(**data) if data else None

    def abort_run(self, run_id: str, *, gracefully: bool = False) -> Run:
        """
        Abort a running Actor run.

        Args:
            run_id: Run ID
            gracefully: If True, the run will receive abort signal and can clean up
        """
        response = self._request(
            "POST",
            f"/v2/actor-runs/{run_id}/abort",
            params={"gracefully": gracefully},
        )
        return Run(**response.json()["data"])

    def resurrect_run(self, run_id: str) -> Run:
        """Resurrect a finished run (restart with same storage)."""
        response = self._request("POST", f"/v2/actor-runs/{run_id}/resurrect")
        return Run(**response.json()["data"])

    def get_run_log(self, run_id: str) -> str:
        """Get the log for a run."""
        response = self._request("GET", f"/v2/logs/{run_id}")
        return response.text

    # === Builds ===

    def list_builds(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = True,
    ) -> BuildList:
        """Get list of builds for the user."""
        response = self._request(
            "GET",
            "/v2/actor-builds",
            params={"offset": offset, "limit": limit, "desc": desc},
        )
        return BuildList(**response.json()["data"])

    def list_actor_builds(
        self,
        actor_id: str,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = True,
    ) -> BuildList:
        """Get list of builds for a specific Actor."""
        response = self._request(
            "GET",
            f"/v2/acts/{actor_id}/builds",
            params={"offset": offset, "limit": limit, "desc": desc},
        )
        return BuildList(**response.json()["data"])

    def get_build(self, build_id: str) -> Build:
        """Get build details."""
        response = self._request("GET", f"/v2/actor-builds/{build_id}")
        return Build(**response.json()["data"])

    def build_actor(
        self,
        actor_id: str,
        *,
        version: Optional[str] = None,
        use_cache: bool = True,
        beta_packages: bool = False,
        tag: Optional[str] = None,
        wait_for_finish: Optional[int] = None,
    ) -> Build:
        """
        Build an Actor.

        Args:
            actor_id: Actor ID or username~actorname
            version: Version to build (default: latest)
            use_cache: Use Docker layer cache
            beta_packages: Use beta versions of Apify packages
            tag: Tag the build with a custom tag
            wait_for_finish: Wait for build to finish (seconds)
        """
        response = self._request(
            "POST",
            f"/v2/acts/{actor_id}/builds",
            params={
                "version": version,
                "useCache": use_cache,
                "betaPackages": beta_packages,
                "tag": tag,
                "waitForFinish": wait_for_finish,
            },
        )
        return Build(**response.json()["data"])

    def abort_build(self, build_id: str) -> Build:
        """Abort a running build."""
        response = self._request("POST", f"/v2/actor-builds/{build_id}/abort")
        return Build(**response.json()["data"])

    def get_build_log(self, build_id: str) -> str:
        """Get the log for a build."""
        response = self._request("GET", f"/v2/actor-builds/{build_id}/log")
        return response.text

    # === Tasks ===

    def list_tasks(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
    ) -> TaskList:
        """Get list of tasks."""
        response = self._request(
            "GET",
            "/v2/actor-tasks",
            params={"offset": offset, "limit": limit, "desc": desc},
        )
        return TaskList(**response.json()["data"])

    def get_task(self, task_id: str) -> Task:
        """Get task details."""
        response = self._request("GET", f"/v2/actor-tasks/{task_id}")
        return Task(**response.json()["data"])

    def create_task(self, request: CreateTaskRequest) -> Task:
        """Create a new task."""
        response = self._request(
            "POST",
            "/v2/actor-tasks",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Task(**response.json()["data"])

    def update_task(self, task_id: str, request: UpdateTaskRequest) -> Task:
        """Update an existing task."""
        response = self._request(
            "PUT",
            f"/v2/actor-tasks/{task_id}",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Task(**response.json()["data"])

    def delete_task(self, task_id: str) -> None:
        """Delete a task."""
        self._request("DELETE", f"/v2/actor-tasks/{task_id}")

    def run_task(
        self,
        task_id: str,
        *,
        input: Optional[dict[str, Any]] = None,
        build: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        wait_for_finish: Optional[int] = None,
    ) -> Run:
        """Run a task."""
        response = self._request(
            "POST",
            f"/v2/actor-tasks/{task_id}/runs",
            params={
                "build": build,
                "timeout": timeout_secs,
                "memory": memory_mbytes,
                "waitForFinish": wait_for_finish,
            },
            json_data=input,
        )
        return Run(**response.json()["data"])

    def run_task_sync(
        self,
        task_id: str,
        *,
        input: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Run a task synchronously and return output."""
        response = self._request(
            "POST",
            f"/v2/actor-tasks/{task_id}/run-sync",
            json_data=input,
        )
        return response.json()

    # === Datasets ===

    def list_datasets(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
        unnamed: bool = False,
    ) -> DatasetList:
        """Get list of datasets."""
        response = self._request(
            "GET",
            "/v2/datasets",
            params={"offset": offset, "limit": limit, "desc": desc, "unnamed": unnamed},
        )
        return DatasetList(**response.json()["data"])

    def get_dataset(self, dataset_id: str) -> Dataset:
        """Get dataset details."""
        response = self._request("GET", f"/v2/datasets/{dataset_id}")
        return Dataset(**response.json()["data"])

    def create_dataset(self, name: Optional[str] = None) -> Dataset:
        """Create a new dataset."""
        response = self._request(
            "POST",
            "/v2/datasets",
            params={"name": name} if name else None,
        )
        return Dataset(**response.json()["data"])

    def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset."""
        self._request("DELETE", f"/v2/datasets/{dataset_id}")

    def get_dataset_items(
        self,
        dataset_id: str,
        *,
        offset: int = 0,
        limit: int = 100000,
        clean: bool = False,
        fields: Optional[list[str]] = None,
        omit: Optional[list[str]] = None,
        unwind: Optional[str] = None,
        flatten: Optional[list[str]] = None,
        format: Literal["json", "csv", "xlsx", "xml", "rss"] = "json",
    ) -> Any:
        """
        Get items from a dataset.

        Args:
            dataset_id: Dataset ID
            offset: Pagination offset
            limit: Maximum items to return (max 250000)
            clean: Remove empty items and hidden fields
            fields: Only return these fields
            omit: Omit these fields
            unwind: Unwind an array field into separate items
            flatten: Flatten nested objects
            format: Output format
        """
        response = self._request(
            "GET",
            f"/v2/datasets/{dataset_id}/items",
            params={
                "offset": offset,
                "limit": limit,
                "clean": clean,
                "fields": ",".join(fields) if fields else None,
                "omit": ",".join(omit) if omit else None,
                "unwind": unwind,
                "flatten": ",".join(flatten) if flatten else None,
                "format": format,
            },
        )
        if format == "json":
            return response.json()
        return response.content

    def push_dataset_items(
        self,
        dataset_id: str,
        items: list[dict[str, Any]],
    ) -> None:
        """Push items to a dataset."""
        self._request(
            "POST",
            f"/v2/datasets/{dataset_id}/items",
            json_data=items,
        )

    # === Key-Value Stores ===

    def list_key_value_stores(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
        unnamed: bool = False,
    ) -> KeyValueStoreList:
        """Get list of key-value stores."""
        response = self._request(
            "GET",
            "/v2/key-value-stores",
            params={"offset": offset, "limit": limit, "desc": desc, "unnamed": unnamed},
        )
        return KeyValueStoreList(**response.json()["data"])

    def get_key_value_store(self, store_id: str) -> KeyValueStore:
        """Get key-value store details."""
        response = self._request("GET", f"/v2/key-value-stores/{store_id}")
        return KeyValueStore(**response.json()["data"])

    def create_key_value_store(self, name: Optional[str] = None) -> KeyValueStore:
        """Create a new key-value store."""
        response = self._request(
            "POST",
            "/v2/key-value-stores",
            params={"name": name} if name else None,
        )
        return KeyValueStore(**response.json()["data"])

    def delete_key_value_store(self, store_id: str) -> None:
        """Delete a key-value store."""
        self._request("DELETE", f"/v2/key-value-stores/{store_id}")

    def list_keys(
        self,
        store_id: str,
        *,
        limit: int = 1000,
        exclusive_start_key: Optional[str] = None,
    ) -> KeyList:
        """Get list of keys in a store."""
        response = self._request(
            "GET",
            f"/v2/key-value-stores/{store_id}/keys",
            params={"limit": limit, "exclusiveStartKey": exclusive_start_key},
        )
        return KeyList(**response.json()["data"])

    def get_record(
        self,
        store_id: str,
        record_key: str,
    ) -> tuple[bytes, str]:
        """
        Get a record from a key-value store.

        Returns:
            Tuple of (content bytes, content type)
        """
        response = self._request("GET", f"/v2/key-value-stores/{store_id}/records/{record_key}")
        return response.content, response.headers.get("content-type", "application/octet-stream")

    def set_record(
        self,
        store_id: str,
        record_key: str,
        value: bytes,
        content_type: str = "application/json",
    ) -> None:
        """Set a record in a key-value store."""
        self._request(
            "PUT",
            f"/v2/key-value-stores/{store_id}/records/{record_key}",
            data=value,
            headers={"Content-Type": content_type},
        )

    def delete_record(self, store_id: str, record_key: str) -> None:
        """Delete a record from a key-value store."""
        self._request("DELETE", f"/v2/key-value-stores/{store_id}/records/{record_key}")

    # === Request Queues ===

    def list_request_queues(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
        unnamed: bool = False,
    ) -> list[RequestQueue]:
        """Get list of request queues."""
        response = self._request(
            "GET",
            "/v2/request-queues",
            params={"offset": offset, "limit": limit, "desc": desc, "unnamed": unnamed},
        )
        return [RequestQueue(**q) for q in response.json()["data"]["items"]]

    def get_request_queue(self, queue_id: str) -> RequestQueue:
        """Get request queue details."""
        response = self._request("GET", f"/v2/request-queues/{queue_id}")
        return RequestQueue(**response.json()["data"])

    def create_request_queue(self, name: Optional[str] = None) -> RequestQueue:
        """Create a new request queue."""
        response = self._request(
            "POST",
            "/v2/request-queues",
            params={"name": name} if name else None,
        )
        return RequestQueue(**response.json()["data"])

    def delete_request_queue(self, queue_id: str) -> None:
        """Delete a request queue."""
        self._request("DELETE", f"/v2/request-queues/{queue_id}")

    def add_request(
        self,
        queue_id: str,
        url: str,
        *,
        unique_key: Optional[str] = None,
        method: str = "GET",
        user_data: Optional[dict[str, Any]] = None,
        force_front: bool = False,
    ) -> QueueRequest:
        """Add a request to a queue."""
        response = self._request(
            "POST",
            f"/v2/request-queues/{queue_id}/requests",
            params={"forefront": force_front},
            json_data={
                "url": url,
                "uniqueKey": unique_key or url,
                "method": method,
                "userData": user_data or {},
            },
        )
        return QueueRequest(**response.json()["data"])

    def get_request(self, queue_id: str, request_id: str) -> QueueRequest:
        """Get a request from a queue."""
        response = self._request("GET", f"/v2/request-queues/{queue_id}/requests/{request_id}")
        return QueueRequest(**response.json()["data"])

    def delete_request(self, queue_id: str, request_id: str) -> None:
        """Delete a request from a queue."""
        self._request("DELETE", f"/v2/request-queues/{queue_id}/requests/{request_id}")

    # === Schedules ===

    def list_schedules(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
    ) -> ScheduleList:
        """Get list of schedules."""
        response = self._request(
            "GET",
            "/v2/schedules",
            params={"offset": offset, "limit": limit, "desc": desc},
        )
        return ScheduleList(**response.json()["data"])

    def get_schedule(self, schedule_id: str) -> Schedule:
        """Get schedule details."""
        response = self._request("GET", f"/v2/schedules/{schedule_id}")
        return Schedule(**response.json()["data"])

    def create_schedule(self, request: CreateScheduleRequest) -> Schedule:
        """Create a new schedule."""
        response = self._request(
            "POST",
            "/v2/schedules",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Schedule(**response.json()["data"])

    def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule."""
        self._request("DELETE", f"/v2/schedules/{schedule_id}")

    # === Webhooks ===

    def list_webhooks(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        desc: bool = False,
    ) -> WebhookList:
        """Get list of webhooks."""
        response = self._request(
            "GET",
            "/v2/webhooks",
            params={"offset": offset, "limit": limit, "desc": desc},
        )
        return WebhookList(**response.json()["data"])

    def get_webhook(self, webhook_id: str) -> Webhook:
        """Get webhook details."""
        response = self._request("GET", f"/v2/webhooks/{webhook_id}")
        return Webhook(**response.json()["data"])

    def create_webhook(self, request: CreateWebhookRequest) -> Webhook:
        """Create a new webhook."""
        response = self._request(
            "POST",
            "/v2/webhooks",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return Webhook(**response.json()["data"])

    def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook."""
        self._request("DELETE", f"/v2/webhooks/{webhook_id}")

    def test_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Test a webhook by sending a test dispatch."""
        response = self._request("POST", f"/v2/webhooks/{webhook_id}/test")
        return response.json()["data"]

    # === Users ===

    def get_me(self) -> User:
        """Get current user data."""
        response = self._request("GET", "/v2/users/me")
        return User(**response.json()["data"])

    def get_limits(self) -> UserLimits:
        """Get account limits and current usage."""
        response = self._request("GET", "/v2/users/me/limits")
        return UserLimits(**response.json()["data"])

    def get_monthly_usage(self) -> MonthlyUsage:
        """Get monthly usage details."""
        response = self._request("GET", "/v2/users/me/usage/monthly")
        return MonthlyUsage(**response.json()["data"])

    def get_user(self, user_id: str) -> User:
        """Get public user data."""
        response = self._request("GET", f"/v2/users/{user_id}")
        return User(**response.json()["data"])

    # === Store ===

    def list_store_actors(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        category: Optional[str] = None,
        username: Optional[str] = None,
        pricing_model: Optional[str] = None,
    ) -> ActorList:
        """
        Get list of Actors in the Apify Store.

        Args:
            offset: Pagination offset
            limit: Maximum items to return
            search: Search term
            sort_by: Sort field (e.g., "relevance", "popularity", "newest")
            category: Filter by category
            username: Filter by username
            pricing_model: Filter by pricing model
        """
        response = self._request(
            "GET",
            "/v2/store",
            params={
                "offset": offset,
                "limit": limit,
                "search": search,
                "sortBy": sort_by,
                "category": category,
                "username": username,
                "pricingModel": pricing_model,
            },
        )
        return ActorList(**response.json()["data"])


# === Async Client ===


class AsyncApifyClient:
    """
    Async Apify API v2 Client.

    Same functionality as ApifyClient but uses httpx.AsyncClient.
    """

    BASE_URL = "https://api.apify.com"

    def __init__(
        self,
        token: str,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.token = token
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> httpx.Response:
        """Make an HTTP request and handle errors."""
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = await self._client.request(
            method,
            path,
            params=params,
            json=json_data,
            content=data,
            headers=headers,
        )

        if response.status_code >= 400:
            try:
                error_data = response.json()
                error = error_data.get("error", {})
                raise ApifyError(
                    message=error.get("message", response.text),
                    status_code=response.status_code,
                    error_type=error.get("type"),
                )
            except (ValueError, KeyError):
                raise ApifyError(
                    message=response.text,
                    status_code=response.status_code,
                )

        return response

    # Note: All methods from ApifyClient can be made async by:
    # 1. Adding 'async' before 'def'
    # 2. Adding 'await' before self._request calls
    # For brevity, only a few key methods are shown here.

    async def run_actor(
        self,
        actor_id: str,
        *,
        input: Optional[dict[str, Any]] = None,
        build: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        memory_mbytes: Optional[int] = None,
        wait_for_finish: Optional[int] = None,
    ) -> Run:
        """Run an Actor asynchronously."""
        response = await self._request(
            "POST",
            f"/v2/acts/{actor_id}/runs",
            params={
                "build": build,
                "timeout": timeout_secs,
                "memory": memory_mbytes,
                "waitForFinish": wait_for_finish,
            },
            json_data=input,
        )
        return Run(**response.json()["data"])

    async def get_run(self, run_id: str) -> Run:
        """Get run details."""
        response = await self._request("GET", f"/v2/actor-runs/{run_id}")
        return Run(**response.json()["data"])

    async def get_dataset_items(
        self,
        dataset_id: str,
        *,
        offset: int = 0,
        limit: int = 100000,
        clean: bool = False,
        format: Literal["json", "csv", "xlsx", "xml", "rss"] = "json",
    ) -> Any:
        """Get items from a dataset."""
        response = await self._request(
            "GET",
            f"/v2/datasets/{dataset_id}/items",
            params={
                "offset": offset,
                "limit": limit,
                "clean": clean,
                "format": format,
            },
        )
        if format == "json":
            return response.json()
        return response.content
