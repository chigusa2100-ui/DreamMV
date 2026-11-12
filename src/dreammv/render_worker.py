
"""Render worker for Animagine XL 4.0 and native LTX-2.5 video generation."""
from __future__ import annotations

import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .anime_engine import ANIME_CONFIG, AnimeEngine
from .ltx25_engine import LTX25Engine


PROMPT_KEYS = (
    "prompt",
    "visual_prompt",
    "video_prompt",
    "description",
    "title",
    "name",
)

LTX_CONFIG = {
    "width": 704,
    "height": 384,
    "fps": 24,
}


def scene_prompt(scene: dict) -> str:
    for key in PROMPT_KEYS:
        if scene.get(key):
            return str(scene[key])
    return "masterpiece, anime illustration, cinematic music video scene"


def scene_duration(scene: dict) -> float:
    if scene.get("duration"):
        return float(scene["duration"])
    try:
        length = float(scene.get("end", 0)) - float(scene.get("start", 0))
    except (TypeError, ValueError):
        length = 0.0
    return length if length > 0 else 5.0


def _ensure_completed_outputs(scenes: list[dict]) -> None:
    """Refuse to assemble a project when a completed scene clip is missing."""
    missing = []

    for scene in scenes:
        if scene.get("status") != "completed":
            continue

        output = scene.get("output")
        if not output or not Path(output).is_file():
            missing.append(str(scene.get("id", "?")))

    if missing:
        raise RuntimeError(
            "完了扱いですが動画ファイルが見つからないシーンがあります: "
            + ", ".join(missing)
            + "\nレンダリングを再実行するか、完成済みクリップを確認してください。"
        )


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def _write_concat_file(concat_txt: Path, clips: list[Path]) -> None:
    """Write FFmpeg concat entries using relative filenames and real newlines.

    FFmpeg's concat demuxer can misread absolute paths containing Japanese
    characters on Windows. The list lives beside the normalized clips, so use
    only each clip's filename and run FFmpeg with that directory as cwd.
    """
    lines = []
    for clip in clips:
        name = clip.name.replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{name}'")

    concat_txt.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _run_ffmpeg(args: list[str], *, cwd: Path | None = None) -> None:
    """Run FFmpeg and include its stderr in any raised error."""
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode:
        details = (
            result.stderr
            or result.stdout
            or "FFmpeg returned a non-zero exit code."
        ).strip()

        raise RuntimeError(
            f"FFmpeg の処理に失敗しました "
            f"(exit {result.returncode})\n{details[-6000:]}"
        )


def _detect_video_config(video_path: Path) -> dict:
    """Detect the resolution and frame rate of an existing video clip.

    Used by AssembleWorker so that assemble-only works with both
    Animagine and LTX-2.5 projects.
    """
    fallback = {
        "width": int(ANIME_CONFIG["width"]),
        "height": int(ANIME_CONFIG["height"]),
        "fps": int(ANIME_CONFIG["fps"]),
    }

    try:
        result = subprocess.run(
            [_ffmpeg(), "-hide_banner", "-i", str(video_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        info = result.stderr or result.stdout or ""

        resolution_match = re.search(
            r"(?<!\d)(\d{2,5})x(\d{2,5})(?!\d)",
            info,
        )
        fps_match = re.search(
            r"(\d+(?:\.\d+)?)\s*fps",
            info,
        )

        config = dict(fallback)

        if resolution_match:
            config["width"] = int(resolution_match.group(1))
            config["height"] = int(resolution_match.group(2))

        if fps_match:
            config["fps"] = max(1, round(float(fps_match.group(1))))

        return config

    except Exception:
        return fallback


def assemble(
    project_dir: Path,
    scenes: list[dict],
    audio_path: Path,
    out_file: Path,
    video_config: dict | None = None,
) -> Path:
    """Normalize generated clips, concatenate them, and add the original song."""

    # Do not silently omit clips whose queue status says they are completed.
    _ensure_completed_outputs(scenes)

    cfg = video_config or ANIME_CONFIG

    width = int(cfg["width"])
    height = int(cfg["height"])
    fps = int(cfg["fps"])

    ff = _ffmpeg()
    norm_dir = project_dir / "render" / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)

    listing: list[Path] = []

    for index, scene in enumerate(scenes, start=1):
        raw = scene.get("output")

        if not raw or not Path(raw).is_file():
            continue

        dst = norm_dir / f"{scene.get('id', index)}.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)

        _run_ffmpeg([
            ff,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(raw),
            "-t",
            f"{scene_duration(scene):.3f}",
            "-vf",
            f"scale={width}:{height},fps={fps}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-an",
            str(dst),
        ])

        listing.append(dst)

    if not listing:
        raise RuntimeError(
            "結合できる動画クリップがありません。"
            "シーンのレンダリング状態と出力ファイルを確認してください。"
        )

    concat_txt = norm_dir / "concat.txt"
    _write_concat_file(concat_txt, listing)

    out_file.parent.mkdir(parents=True, exist_ok=True)

    _run_ffmpeg([
        ff,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_txt.name,
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(out_file),
    ], cwd=norm_dir)

    return out_file


class RenderWorker(QThread):
    log = Signal(str)
    scene_changed = Signal()
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        queue_service,
        project_dir: Path,
        audio_path: Path,
        preset: str = "animagine",
        models_dir: str | None = None,
    ):
        super().__init__()
        self.queue = queue_service
        self.project_dir = Path(project_dir)
        self.audio_path = Path(audio_path)
        self.preset = preset
        self.models_dir = models_dir

        self._cancel = False
        self._engine = None

    def cancel(self):
        self._cancel = True

        engine = self._engine
        if isinstance(engine, LTX25Engine):
            engine.cancel()

    def _log_exc(self, label: str):
        try:
            log_dir = self.project_dir / "render"
            log_dir.mkdir(parents=True, exist_ok=True)

            with (log_dir / "render.log").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"{label} ---\n"
                    f"{traceback.format_exc()}\n"
                )
        except Exception:
            pass

    def _create_engine(self):
        if self.preset in ("anime", "animagine"):
            return AnimeEngine(
                "animagine",
                models_dir=self.models_dir,
            )

        if self.preset == "ltx25":
            return LTX25Engine()

        raise RuntimeError(
            f"未対応のレンダリングエンジンです: {self.preset}"
        )

    def _load_engine(self, engine):
        if isinstance(engine, LTX25Engine):
            self.log.emit(
                "LTX-2.5 native CLI を初期化しています..."
            )
        else:
            self.log.emit(
                "Animagine XL 4.0 を初期化しています... "
                "初回はモデルの読み込みに時間がかかる場合があります。"
            )

        try:
            engine.load()

        except ModuleNotFoundError as exc:
            raise RuntimeError(
                f"必要なPythonモジュールが見つかりません: {exc.name}\n\n"
                "DreamMV の .venv 環境に必要なパッケージが"
                "インストールされているか確認してください。\n"
                f"現在の Python: {sys.executable}"
            ) from exc

    def _generate_scene(
        self,
        engine,
        scene: dict,
        output_path: Path,
        scene_id,
    ):
        prompt = scene_prompt(scene)
        duration = scene_duration(scene)

        if isinstance(engine, LTX25Engine):
            self.log.emit(
                f"シーン {scene_id}: "
                "LTX-2.5 で動画を生成しています..."
            )

            return engine.generate(
                prompt=prompt,
                duration=duration,
                output_path=output_path,
                seed=scene.get("seed"),
            )

        self.log.emit(
            f"シーン {scene_id}: "
            "Animagine で画像を生成しています..."
        )

        def on_step(step, total, sid=scene_id):
            suffix = (
                " 画像生成が完了しました。"
                if step == total
                else ""
            )

            self.log.emit(
                f"シーン {sid}: "
                f"生成ステップ {step}/{total}{suffix}"
            )

        return engine.generate(
            prompt,
            output_path,
            duration,
            on_step=on_step,
            camera_motion=scene.get("camera_motion"),
        )

    def run(self):
        engine = None

        try:
            engine = self._create_engine()
            self._engine = engine

            self._load_engine(engine)

            self.queue.recover_running()
            data = self.queue.load()
            scenes = data.get("scenes", [])

            for scene in scenes:
                if self._cancel:
                    self.log.emit(
                        "レンダリングがキャンセルされました。"
                        "現在のシーンまでの生成結果を保持します。"
                    )
                    break

                if scene.get("status") not in (None, "queued"):
                    continue

                scene_id = scene.get("id")

                self.queue.set_scene_status(
                    scene_id,
                    "running",
                )
                self.scene_changed.emit()

                out = (
                    self.project_dir
                    / "render"
                    / "clips"
                    / f"{scene_id}.mp4"
                )
                out.parent.mkdir(parents=True, exist_ok=True)

                started = time.time()

                try:
                    self._generate_scene(
                        engine,
                        scene,
                        out,
                        scene_id,
                    )

                    self.queue.set_scene_status(
                        scene_id,
                        "completed",
                        output=str(out),
                    )

                    self.log.emit(
                        f"シーン {scene_id} 完了 "
                        f"({(time.time() - started) / 60:.1f} 分)"
                    )

                except Exception as exc:
                    self._log_exc(f"scene {scene_id}")

                    engine.unload()

                    self.queue.set_scene_status(
                        scene_id,
                        "failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )

                    self.log.emit(
                        f"シーン {scene_id} 失敗: {exc}"
                    )

                self.scene_changed.emit()

            data = self.queue.load()

            completed = [
                scene
                for scene in data.get("scenes", [])
                if scene.get("status") == "completed"
            ]

            if not completed:
                raise RuntimeError(
                    "完了したシーンがありません。"
                    "render.log を確認してください。"
                )

            engine.unload()

            if self.preset == "ltx25":
                video_config = LTX_CONFIG
                self.log.emit(
                    "LTX-2.5 の動画クリップを結合しています..."
                    " (704x384 / 24fps)"
                )
            else:
                video_config = ANIME_CONFIG
                self.log.emit(
                    "Animagine の動画クリップを結合しています..."
                )

            result = assemble(
                self.project_dir,
                data["scenes"],
                self.audio_path,
                self.project_dir / "output" / "music_video.mp4",
                video_config=video_config,
            )

            self.finished_ok.emit(str(result))

        except Exception as exc:
            self._log_exc("worker")
            self.failed.emit(str(exc))

        finally:
            if engine is not None:
                try:
                    engine.unload()
                except Exception:
                    pass

            self._engine = None


class AssembleWorker(QThread):
    """Rebuild the final MP4 from completed scene clips without regeneration."""

    log = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        queue_service,
        project_dir: Path,
        audio_path: Path,
    ):
        super().__init__()
        self.queue = queue_service
        self.project_dir = Path(project_dir)
        self.audio_path = Path(audio_path)

    def run(self):
        try:
            data = self.queue.load()
            scenes = data.get("scenes", [])

            completed = [
                scene
                for scene in scenes
                if scene.get("status") == "completed"
            ]

            if not completed:
                raise RuntimeError(
                    "完了済みのシーンがありません。"
                    "先にシーンのレンダリングを実行してください。"
                )

            # Use the same validation as normal rendering.
            _ensure_completed_outputs(completed)

            first_clip = Path(completed[0]["output"])
            video_config = _detect_video_config(first_clip)

            self.log.emit(
                f"完了済み {len(completed)} シーンを結合しています..."
                f" ({video_config['width']}x{video_config['height']} "
                f"/ {video_config['fps']}fps)"
            )

            result = assemble(
                self.project_dir,
                completed,
                self.audio_path,
                self.project_dir / "output" / "music_video.mp4",
                video_config=video_config,
            )

            self.finished_ok.emit(str(result))

        except Exception as exc:
            try:
                log_dir = self.project_dir / "render"
                log_dir.mkdir(parents=True, exist_ok=True)

                with (log_dir / "render.log").open(
                    "a",
                    encoding="utf-8",
                ) as handle:
                    handle.write(
                        f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} "
                        "assemble-only ---\n"
                        f"{type(exc).__name__}: {exc}\n"
                    )
            except Exception:
                pass

            self.failed.emit(str(exc))
