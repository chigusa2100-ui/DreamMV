"""Project-level integration helpers for DreamMV scene queues."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .queue import QueueManager

class ProjectQueueService:
    """Manage queue metadata; this does not generate images or videos."""
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.output_dir = self.project_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.queue = QueueManager(self.output_dir)

    def create_from_scenes(self, scenes: list[dict[str, Any]], title: str = "DreamMV") -> dict[str, Any]:
        return self.queue.create(scenes, title=title)

    def create_from_plan(self, plan: dict[str, Any], title: str = "DreamMV") -> dict[str, Any]:
        scenes = plan.get("scenes", [])
        if not isinstance(scenes, list):
            raise ValueError("plan['scenes'] must be a list")
        return self.create_from_scenes(scenes, title=title)

    def load(self) -> dict[str, Any]:
        return self.queue.load()

    def progress(self) -> dict[str, int | float]:
        return self.queue.progress()

    def retry_failed(self) -> int:
        """Move every failed scene back to queued and return the number retried."""
        data = self.queue.load()
        retried = 0
        for scene in data.get("scenes", []):
            if scene.get("status") == "failed":
                self.queue.retry(scene["id"])
                retried += 1
        return retried

    # --- used by RenderWorker (Wan rendering) ---
    def recover_running(self) -> int:
        return self.queue.recover_running()

    def set_scene_status(self, scene_id: Any, status: str,
                         error: str | None = None, output: str | None = None) -> None:
        """Move a scene through QueueManager's own state machine."""
        if status == "running":
            self.queue.start(scene_id)
        elif status == "completed":
            self.queue.complete(scene_id, output=output)
        elif status == "failed":
            self.queue.fail(scene_id, error or "unknown error")
        elif status == "queued":
            self.queue.retry(scene_id)  # failed -> queued only
        else:
            raise ValueError(f"unknown status: {status}")
