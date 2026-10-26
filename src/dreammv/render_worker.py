"""Animagine-only renderer: generate one anime still per scene, animate it, then mux audio."""
from __future__ import annotations

import subprocess
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .anime_engine import ANIME_CONFIG, AnimeEngine

PROMPT_KEYS = ("prompt", "visual_prompt", "video_prompt", "description", "title", "name")


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
    concat_txt.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _run_ffmpeg(args: list[str], *, cwd: Path | None = None) -> None:
    """Run FFmpeg and include its stderr in any raised error."""
    result = subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        details = (result.stderr or result.stdout or "FFmpeg returned a non-zero exit code.").strip()
        raise RuntimeError(f"FFmpeg の処理に失敗しました (exit {result.returncode})\n{details[-6000:]}")


def assemble(project_dir: Path, scenes: list[dict], audio_path: Path, out_file: Path) -> Path:
    """Normalize generated clips to scene lengths, concatenate them, and add the song."""
    cfg = ANIME_CONFIG
    ff = _ffmpeg()
    norm_dir = project_dir / "render" / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    listing: list[Path] = []
    for index, scene in enumerate(scenes, start=1):
        raw = scene.get("output")
        if not raw or not Path(raw).exists():
            continue
        dst = norm_dir / f"{scene.get('id', index)}.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        _run_ffmpeg([
            ff, "-y", "-stream_loop", "-1", "-i", str(raw),
            "-t", f"{scene_duration(scene):.3f}",
            "-vf", f"scale={cfg['width']}:{cfg['height']},fps={cfg['fps']}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-an", str(dst),
        ])
        listing.append(dst)
    if not listing:
        raise RuntimeError("結合できるクリップがありません。")
    concat_txt = norm_dir / "concat.txt"
    _write_concat_file(concat_txt, listing)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg([
        ff, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt.name, "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "192k", "-shortest", str(out_file),
    ], cwd=norm_dir)
    return out_file


class RenderWorker(QThread):
    log = Signal(str)
    scene_changed = Signal()
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, queue_service, project_dir: Path, audio_path: Path,
                 preset: str = "animagine", models_dir: str | None = None):
        super().__init__()
        self.queue = queue_service
        self.project_dir = Path(project_dir)
        self.audio_path = Path(audio_path)
        self.preset = preset
        self.models_dir = models_dir
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _log_exc(self, label: str):
        try:
            log_dir = self.project_dir / "render"
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "render.log").open("a", encoding="utf-8") as handle:
                handle.write(
                    f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} {label} ---\n"
                    f"{traceback.format_exc()}\n"
                )
        except Exception:
            pass

    def run(self):
        if self.preset not in ("anime", "animagine"):
            self.failed.emit(f"未対応の生成方式です: {self.preset}。Animagine XL 4.0 を使用してください。")
            return
        engine = AnimeEngine("animagine", models_dir=self.models_dir)
        try:
            self.log.emit("Animagine XL 4.0 を読み込み中...（初回は数分かかります）")
            try:
                engine.load()
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    f"必要なライブラリが見つかりません: {exc.name}\n\n"
                    "DreamMV の .venv で起動しているか確認してください。run.bat から起動できます。\n"
                    f"現在の Python: {sys.executable}"
                ) from exc
            self.queue.recover_running()
            data = self.queue.load()
            scenes = data.get("scenes", [])
            for scene in scenes:
                if self._cancel:
                    self.log.emit("キャンセルされました。実行中のシーンが終わり次第停止します。")
                    break
                if scene.get("status") not in (None, "queued"):
                    continue
                scene_id = scene.get("id")
                self.queue.set_scene_status(scene_id, "running")
                self.scene_changed.emit()
                out = self.project_dir / "render" / "clips" / f"{scene_id}.mp4"
                started = time.time()
                self.log.emit(f"シーン {scene_id}: Animagine で画像を生成中...")

                def on_step(step, total, sid=scene_id):
                    suffix = " → カメラワーク動画を書き出し中..." if step == total else ""
                    self.log.emit(f"シーン {sid}: 画像生成 step {step}/{total}{suffix}")

                try:
                    engine.generate(scene_prompt(scene), out, scene_duration(scene), on_step=on_step)
                    self.queue.set_scene_status(scene_id, "completed", output=str(out))
                    self.log.emit(f"シーン {scene_id} 完了（{(time.time() - started) / 60:.1f} 分）")
                except Exception as exc:
                    self._log_exc(f"scene {scene_id}")
                    engine.unload()
                    self.queue.set_scene_status(scene_id, "failed", error=f"{type(exc).__name__}: {exc}")
                    self.log.emit(f"シーン {scene_id} 失敗: {exc}")
                self.scene_changed.emit()

            data = self.queue.load()
            completed = [scene for scene in data.get("scenes", []) if scene.get("status") == "completed"]
            if not completed:
                raise RuntimeError("完了したシーンがありません。キューと render.log を確認してください。")
            engine.unload()
            self.log.emit("生成したシーンを結合し、音声を追加中...")
            result = assemble(
                self.project_dir, data["scenes"], self.audio_path,
                self.project_dir / "output" / "music_video.mp4",
            )
            self.finished_ok.emit(str(result))
        except Exception as exc:
            self._log_exc("worker")
            self.failed.emit(str(exc))
        finally:
            engine.unload()


class AssembleWorker(QThread):
    """Rebuild the final MP4 from already completed scene clips without regenerating images."""
    log = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, queue_service, project_dir: Path, audio_path: Path):
        super().__init__()
        self.queue = queue_service
        self.project_dir = Path(project_dir)
        self.audio_path = Path(audio_path)

    def run(self):
        try:
            data = self.queue.load()
            scenes = data.get("scenes", [])
            completed = [scene for scene in scenes if scene.get("status") == "completed"]
            if not completed:
                raise RuntimeError("完了済みシーンがありません。画像生成を行わずに結合できるクリップがありません。")
            missing = [
                str(scene.get("id", "?")) for scene in completed
                if not scene.get("output") or not Path(scene["output"]).exists()
            ]
            if missing:
                raise RuntimeError(
                    "完了扱いですが動画ファイルが見つからないシーンがあります: "
                    + ", ".join(missing)
                    + "\\n生成済みファイルを削除せず、キューと render/clips を確認してください。"
                )
            self.log.emit(f"Animagineは起動せず、完了済み {len(completed)} シーンを結合しています...")
            result = assemble(
                self.project_dir, completed, self.audio_path,
                self.project_dir / "output" / "music_video.mp4",
            )
            self.finished_ok.emit(str(result))
        except Exception as exc:
            try:
                log_dir = self.project_dir / "render"
                log_dir.mkdir(parents=True, exist_ok=True)
                with (log_dir / "render.log").open("a", encoding="utf-8") as handle:
                    handle.write(
                        f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} assemble-only ---\\n"
                        f"{type(exc).__name__}: {exc}\\n"
                    )
            except Exception:
                pass
            self.failed.emit(str(exc))
