"""
In-memory Job Registry and WebSocket Pub/Sub Manager for Asynchronous Simulations.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SimulationJob(BaseModel):
    """Data model representing the state of an asynchronous simulation task."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = Field(default=JobStatus.QUEUED)
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    completed_paths: int = Field(default=0, ge=0)
    total_paths: int = Field(..., gt=0)
    partial_metrics: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class JobManager:
    """Manages life-cycle, status updates, and WebSocket broadcasting for simulation jobs."""

    def __init__(self, job_ttl_seconds: int = 1800) -> None:
        self._jobs: dict[str, SimulationJob] = {}
        self._listeners: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self.job_ttl = job_ttl_seconds

    def create_job(self, total_paths: int) -> SimulationJob:
        """Register a new job in QUEUED status."""
        job = SimulationJob(total_paths=total_paths)
        self._jobs[job.job_id] = job
        self._listeners[job.job_id] = []
        return job

    def get_job(self, job_id: str) -> Optional[SimulationJob]:
        """Retrieve job state by ID."""
        return self._jobs.get(job_id)

    def set_processing(self, job_id: str) -> None:
        """Mark job as PROCESSING."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.PROCESSING
            job.updated_at = time.time()

    async def update_progress(
        self,
        job_id: str,
        completed_paths: int,
        total_paths: int,
        partial_metrics: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update job progress and broadcast PROGRESS event to all active WebSocket listeners."""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = JobStatus.PROCESSING
        job.completed_paths = completed_paths
        job.total_paths = total_paths
        job.progress = round((completed_paths / total_paths) * 100.0, 1)
        job.updated_at = time.time()
        if partial_metrics:
            job.partial_metrics = partial_metrics

        event = {
            "type": "PROGRESS",
            "job_id": job_id,
            "status": job.status.value,
            "percent": job.progress,
            "completed_paths": completed_paths,
            "total_paths": total_paths,
            "partial_metrics": job.partial_metrics,
        }
        await self._broadcast(job_id, event)

    async def set_completed(self, job_id: str, result_data: dict[str, Any]) -> None:
        """Mark job as COMPLETED and broadcast COMPLETE event with payload."""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = JobStatus.COMPLETED
        job.progress = 100.0
        job.completed_paths = job.total_paths
        job.result = result_data
        job.updated_at = time.time()

        event = {
            "type": "COMPLETE",
            "job_id": job_id,
            "status": job.status.value,
            "percent": 100.0,
            "completed_paths": job.total_paths,
            "total_paths": job.total_paths,
            "data": result_data,
        }
        await self._broadcast(job_id, event)

    async def set_failed(self, job_id: str, error_message: str) -> None:
        """Mark job as FAILED and broadcast ERROR event."""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = JobStatus.FAILED
        job.error = error_message
        job.updated_at = time.time()

        event = {
            "type": "ERROR",
            "job_id": job_id,
            "status": job.status.value,
            "error": error_message,
        }
        await self._broadcast(job_id, event)

    def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe a new WebSocket connection to receive events for job_id."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if job_id not in self._listeners:
            self._listeners[job_id] = []
        self._listeners[job_id].append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue when WebSocket disconnects."""
        if job_id in self._listeners and queue in self._listeners[job_id]:
            self._listeners[job_id].remove(queue)
            if not self._listeners[job_id] and job_id not in self._jobs:
                del self._listeners[job_id]

    async def _broadcast(self, job_id: str, event: dict[str, Any]) -> None:
        """Push message to all subscriber queues for job_id."""
        listeners = self._listeners.get(job_id, [])
        for queue in listeners:
            await queue.put(event)


# Global singleton JobManager instance
job_manager = JobManager()
