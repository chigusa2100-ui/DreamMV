"""Small local job-state helper; the actual image/video engine is not connected yet."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobManager:
    VALID_STATES = {"queued", "running", "completed", "failed"}

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.job_file = self.output_dir / "job.json"

    def update(self, status: str, title: str, job_type: str = "planning", error: str | None = None) -> dict[str, Any]:
        if status not in self.VALID_STATES:
            raise ValueError(f"不明なジョブ状態です: {status}")
        job = {
            "title": title,
            "status": status,
            "type": job_type,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return job
