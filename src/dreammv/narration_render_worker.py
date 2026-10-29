
"""Dedicated Animagine renderer for narration illustration projects."""
from __future__ import annotations

import json
import subprocess
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .anime_engine import ANIME_CONFIG, AnimeEngine
from .project_queue import ProjectQueueService
from .render_worker import _ffmpeg, _run_ffmpeg, _write_concat_file, scene_prompt


class NarrationRenderWorker(QThread):
    """Render 10-second narration scenes without using the music MV queue."""

    log = Signal(str)
    scene_changed = Signal()
    finished_ok = Signal(str)
    failed = Signal(str)

    CLIP_DURATION = 10.0

    def __init__(
        self,
        project_dir: str | Path,
        models_dir: str | None = None,
    ):
        super().__init__()
        self.project_dir = Path(project_dir)
        self.models_dir = models_dir
        # A separate directory prevents collisions with the music MV queue.
        self.queue = ProjectQueueService(
            self.project_dir / "narration_render_state"
        )
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _log_error(self, label: str):
        try:
            log_dir = self.project_dir / "render"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "narration_render.log").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write(
                    f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"{label} ---\n{traceback.format_exc()}\n"
                )
        except Exception:
            pass

    def _load_plan(self) -> tuple[dict, Path]:
        plan_path = self.project_dir / "narration_plan.json"
        if not plan_path.is_file():
            raise FileNotFoundError(
                f"朗読設計図が見つかりません: {plan_path}"
            )

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        scenes = plan.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("朗読設計図にシーンがありません。")

        audio_relative = plan.get("audio_file")
        if not audio_relative:
            raise ValueError("朗読設計図に audio_file がありません。")

        audio_path = (self.project_dir / audio_relative).resolve()
        if not audio_path.is_file():
            raise FileNotFoundError(
                f"朗読音声が見つかりません: {audio_path}"
            )

        return plan, audio_path

    def _prepare_queue(self, plan: dict):
        """Initialize the narration queue only if it does not exist yet."""
        queue_file = self.queue.output_dir / "queue.json"
        if queue_file.is_file():
            data = self.queue.load()
            existing_ids = [
                str(scene.get("id")) for scene in data.get("scenes", [])
            ]
            plan_ids = [
                str(scene.get("id")) for scene in plan["scenes"]
            ]
            if existing_ids != plan_ids:
                raise RuntimeError(
                    "保存済みの朗読キューと設計図のシーンIDが一致しません。"
                    "既存データを自動上書きしませんでした。"
                )
            return

        normalized = []
        for index, original in enumerate(plan["scenes"], start=1):
            scene = dict(original)
            scene_id = scene.get("id")
            if scene_id is None or str(scene_id).strip() == "":
                scene_id = f"narration_scene_{index:04d}"
            scene["id"] = scene_id
            scene["duration"] = self.CLIP_DURATION
            scene.setdefault("name", f"朗読シーン {index:04d}")
            scene.setdefault("prompt", scene.get("visual_prompt", ""))
            normalized.append(scene)

        self.queue.create_from_scenes(
            normalized, title=plan.get("title", self.project_dir.name)
        )

    def _assemble(self, audio_path: Path) -> Path:
        data = self.queue.load()
        scenes = data.get("scenes", [])
        clips = []

        for index, scene in enumerate(scenes, start=1):
            if scene.get("status") != "completed":
                continue
            output = scene.get("output")
            if not output or not Path(output).is_file():
                continue
            clips.append(Path(output).resolve())

        if not clips:
            raise RuntimeError(
                "結合できる完成済みクリップがありません。"
            )

        render_dir = self.project_dir / "render" / "narration"
        render_dir.mkdir(parents=True, exist_ok=True)

        concat_file = render_dir / "concat.txt"
        _write_concat_file(concat_file, clips)

        output_file = (
            self.project_dir / "output" / "narration_video.mp4"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        self.log.emit("朗読クリップを結合し、音声を追加しています...")
        # Deliberately omit -shortest: narration audio must not be cut
        # merely because the video stream is shorter.
        _run_ffmpeg([
            _ffmpeg(), "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file.name,
            "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_file),
        ], cwd=render_dir)

        return output_file

    def run(self):
        engine = None
        try:
            plan, audio_path = self._load_plan()
            self._prepare_queue(plan)

            self.log.emit(
                "Animagine XL 4.0 を読み込んでいます..."
                "（初回は時間がかかる場合があります）"
            )
            engine = AnimeEngine("animagine", models_dir=self.models_dir)
            engine.load()

            self.queue.recover_running()
            data = self.queue.load()

            for scene in data.get("scenes", []):
                if self._cancel:
                    self.log.emit(
                        "中止しました。未処理のシーンは待機状態のままです。"
                    )
                    break

                if scene.get("status") != "queued":
                    continue

                scene_id = scene["id"]
                out = (
                    self.project_dir / "render" / "narration"
                    / "clips" / f"{scene_id}.mp4"
                )
                started = time.time()

                self.queue.set_scene_status(scene_id, "running")
                self.scene_changed.emit()
                self.log.emit(
                    f"シーン {scene_id}: Animagineで画像を生成しています..."
                )

                try:
                    engine.generate(
                        scene_prompt(scene),
                        out,
                        self.CLIP_DURATION,
                        on_step=lambda step, total, sid=scene_id:
                            self.log.emit(
                                f"シーン {sid}: 画像生成 step "
                                f"{step}/{total}"
                            ),
                    )
                    self.queue.set_scene_status(
                        scene_id, "completed", output=str(out.resolve())
                    )
                    self.log.emit(
                        f"シーン {scene_id} 完了 "
                        f"（{(time.time() - started) / 60:.1f} 分）"
                    )
                except Exception as exc:
                    self._log_error(f"scene {scene_id}")
                    self.queue.set_scene_status(
                        scene_id, "failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    self.log.emit(f"シーン {scene_id} 失敗: {exc}")
                finally:
                    self.scene_changed.emit()

            engine.unload()
            engine = None

            data = self.queue.load()
            if any(s.get("status") == "completed" for s in data["scenes"]):
                result = self._assemble(audio_path)
                self.finished_ok.emit(str(result))
            elif self._cancel:
                self.log.emit("生成は中止されました。完成済みクリップは保存されています。")
            else:
                raise RuntimeError(
                    "完成したシーンがありません。ログを確認してください。"
                )

        except Exception as exc:
            self._log_error("worker")
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            if engine is not None:
                engine.unload()
