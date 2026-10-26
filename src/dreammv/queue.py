"""Persistent per-scene queue management for DreamMV.

This module only tracks scene job state in output/queue.json.
It does not generate images or videos itself.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# create() が管理するキー。プランナーが同名キーを渡しても、これらは上書きされる。
_CORE_KEYS = {
    "id", "name", "start", "end", "prompt",
    "status", "attempts", "error", "created_at", "updated_at",
}


class QueueManager:
    """Persist and manage scene jobs in output/queue.json."""

    VALID_STATES = {"queued", "running", "completed", "failed"}

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.output_dir / "queue.json"
        # GUIスレッドとレンダリングスレッドが同じインスタンスを共有する前提。
        self._lock = threading.RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read(self) -> dict[str, Any]:
        with self._lock:
            if not self.queue_file.exists():
                return {
                    "version": 1,
                    "created_at": self._now(),
                    "updated_at": self._now(),
                    "scenes": [],
                }
            try:
                data = json.loads(self.queue_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"Could not read queue file: {exc}") from exc
            if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
                raise ValueError("Invalid queue file: expected an object with a scenes list")
            return data

    def _write(self, data: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data["updated_at"] = self._now()
            temp_file = self.queue_file.with_suffix(".json.tmp")
            temp_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            # Windowsでは、他のプロセス(ウイルス対策・同期ソフト等)が一瞬ファイルを
            # 開いているだけで replace が PermissionError になることがあるのでリトライする。
            for attempt in range(10):
                try:
                    temp_file.replace(self.queue_file)
                    break
                except PermissionError:
                    if attempt == 9:
                        raise
                    time.sleep(0.05)
            return data

    def create(self, scenes: Iterable[dict[str, Any]], title: str = "DreamMV") -> dict[str, Any]:
        """Create a fresh queue from scene-plan dictionaries.

        Extra keys in each scene (e.g. title, description, mood) are preserved.
        """
        normalized = []
        seen_ids = set()
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise ValueError(f"Scene {index} must be an object")
            scene_id = scene.get("id", index)
            if isinstance(scene_id, bool) or not isinstance(scene_id, (str, int)):
                raise ValueError(f"Scene {index} has an invalid id")
            scene_key = str(scene_id)
            if not scene_key:
                raise ValueError(f"Scene {index} has an empty id")
            if scene_key in seen_ids:
                raise ValueError(f"Duplicate scene id: {scene_key}")
            seen_ids.add(scene_key)
            extras = {k: v for k, v in scene.items() if k not in _CORE_KEYS}
            normalized.append({
                **extras,
                "id": scene_id,
                "name": str(scene.get("name", scene.get("title", f"Scene {scene_id}"))),
                "start": scene.get("start", 0),
                "end": scene.get("end", 0),
                "prompt": str(scene.get("prompt", "")),
                "status": "queued",
                "attempts": 0,
                "error": None,
                "created_at": self._now(),
                "updated_at": self._now(),
            })
        data = {
            "version": 1,
            "title": str(title),
            "created_at": self._now(),
            "updated_at": self._now(),
            "scenes": normalized,
        }
        with self._lock:
            self._write(data)
        return data

    def load(self) -> dict[str, Any]:
        """Load persisted queue data."""
        return self._read()

    def _update_scene(self, scene_id: str | int, updater) -> dict[str, Any]:
        with self._lock:  # 読み→更新→書きを1つの操作として保護する
            data = self._read()
            scene = next((item for item in data["scenes"] if str(item.get("id")) == str(scene_id)), None)
            if scene is None:
                raise KeyError(f"Scene not found: {scene_id}")
            updater(scene)
            scene["updated_at"] = self._now()
            self._write(data)
            return scene

    def start(self, scene_id: str | int) -> dict[str, Any]:
        def update(scene):
            if scene["status"] != "queued":
                raise ValueError(f"Cannot start scene in state: {scene['status']}")
            scene["status"] = "running"
            scene["attempts"] = int(scene.get("attempts", 0)) + 1
            scene["error"] = None
        return self._update_scene(scene_id, update)

    def complete(self, scene_id: str | int, output: str | None = None) -> dict[str, Any]:
        """Mark a running scene completed. `output` is the generated clip path, if any."""
        def update(scene):
            if scene["status"] != "running":
                raise ValueError(f"Cannot complete scene in state: {scene['status']}")
            scene["status"] = "completed"
            scene["error"] = None
            if output:
                scene["output"] = str(output)
        return self._update_scene(scene_id, update)

    def fail(self, scene_id: str | int, error: str) -> dict[str, Any]:
        def update(scene):
            if scene["status"] != "running":
                raise ValueError(f"Cannot fail scene in state: {scene['status']}")
            scene["status"] = "failed"
            scene["error"] = str(error)
        return self._update_scene(scene_id, update)

    def retry(self, scene_id: str | int) -> dict[str, Any]:
        def update(scene):
            if scene["status"] != "failed":
                raise ValueError(f"Only failed scenes can be retried; current state: {scene['status']}")
            scene["status"] = "queued"
            scene["error"] = None
        return self._update_scene(scene_id, update)

    def next_queued(self) -> dict[str, Any] | None:
        data = self._read()
        return next((scene for scene in data["scenes"] if scene.get("status") == "queued"), None)

    def recover_running(self) -> int:
        """Requeue scenes left running after an interrupted session.

        Call this only when the previous queue worker is known to have stopped.
        Returns the number of recovered scenes.
        """
        with self._lock:
            data = self._read()
            recovered = 0
            for scene in data["scenes"]:
                if scene.get("status") == "running":
                    scene["status"] = "queued"
                    scene["error"] = "Recovered after interrupted session"
                    scene["updated_at"] = self._now()
                    recovered += 1
            if recovered:
                self._write(data)
            return recovered

    def progress(self) -> dict[str, Any]:
        scenes = self._read()["scenes"]
        total = len(scenes)
        counts = {state: sum(1 for scene in scenes if scene.get("status") == state) for state in self.VALID_STATES}
        completed = counts["completed"]
        return {
            "total": total,
            "queued": counts["queued"],
            "running": counts["running"],
            "completed": completed,
            "failed": counts["failed"],
            "progress_percent": round(completed * 100 / total, 1) if total else 0.0,
        }
