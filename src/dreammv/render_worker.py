"""一晩レンダリング用ワーカー: キューのシーンを順に Wan で生成 → ffmpeg で結合 → 音声を合成。"""
from __future__ import annotations

import subprocess
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .wan_engine import PRESETS, WanEngine

PROMPT_KEYS = ("prompt", "visual_prompt", "video_prompt", "description", "title", "name")


def scene_prompt(scene: dict) -> str:
    for k in PROMPT_KEYS:
        if scene.get(k):
            return str(scene[k])
    return "cinematic music video scene"


def scene_duration(scene: dict) -> float:
    if scene.get("duration"):
        return float(scene["duration"])
    try:
        length = float(scene.get("end", 0)) - float(scene.get("start", 0))
    except (TypeError, ValueError):
        length = 0.0
    return length if length > 0 else 5.0  # start/end が未設定(0)のときは5秒


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def assemble(project_dir: Path, scenes: list[dict], audio_path: Path,
             preset: str, out_file: Path) -> Path:
    """各クリップをシーン長に正規化（足りなければループ、長ければトリム）して結合し音声を載せる。"""
    cfg = PRESETS[preset]
    ff = _ffmpeg()
    norm_dir = project_dir / "render" / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    listing = []
    for s in scenes:
        raw = s.get("output")
        if not raw or not Path(raw).exists():
            continue
        dst = norm_dir / f"{s.get('id')}.mp4"
        subprocess.run([
            ff, "-y", "-stream_loop", "-1", "-i", raw, "-t", f"{scene_duration(s):.3f}",
            "-vf", f"scale={cfg['width']}:{cfg['height']},fps=24",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-an", str(dst),
        ], check=True, capture_output=True)
        listing.append(dst)
    if not listing:
        raise RuntimeError("結合できるクリップがありません。")
    concat_txt = norm_dir / "concat.txt"
    concat_txt.write_text("".join(f"file '{p.as_posix()}'\n" for p in listing), encoding="utf-8")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        ff, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-i", str(audio_path),
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(out_file),
    ], check=True, capture_output=True)
    return out_file


class RenderWorker(QThread):
    log = Signal(str)
    scene_changed = Signal()          # キュー表示の更新用
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, queue_service, project_dir: Path, audio_path: Path,
                 preset: str = "light", models_dir: str | None = None):
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
            d = self.project_dir / "render"
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "render.log", "a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} {label} ---\n{traceback.format_exc()}\n")
        except Exception:
            pass

    def run(self):
        engine = WanEngine(self.preset, models_dir=self.models_dir)
        try:
            # 先にモデルを読み込む。環境の問題（torch未導入など）はここで止め、シーンは失敗扱いにしない
            self.log.emit("モデルを読み込み中...（初回は数分かかります）")
            try:
                engine.load()
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    f"必要なライブラリが見つかりません: {exc.name}\n\n"
                    "このアプリを .venv の Python で起動していますか？ run.bat から起動してください。\n"
                    f"現在の Python: {sys.executable}"
                ) from exc
            self.queue.recover_running()  # 前回クラッシュ等で running のまま残ったものを戻す
            data = self.queue.load()
            scenes = data.get("scenes", [])
            for s in scenes:
                if self._cancel:
                    self.log.emit("キャンセルされました。")
                    break
                if s.get("status") not in (None, "queued"):
                    continue
                sid = s.get("id")
                self.queue.set_scene_status(sid, "running")
                self.scene_changed.emit()
                out = self.project_dir / "render" / "clips" / f"{sid}.mp4"
                t0 = time.time()
                self.log.emit(f"シーン {sid}: 準備中（テキスト解析・モデル転送）...")

                def on_step(i, n, sid=sid):
                    msg = f"シーン {sid}: step {i}/{n}"
                    if i == n:
                        msg += " → 映像にデコード・書き出し中（数分かかることがあります）..."
                    self.log.emit(msg)

                try:
                    engine.generate(scene_prompt(s), out, scene_duration(s), on_step=on_step)
                    self.queue.set_scene_status(sid, "completed", output=str(out))
                    self.log.emit(f"シーン {sid} 完了（{(time.time() - t0) / 60:.1f} 分）")
                except Exception as exc:  # OOM等でも次のシーンへ進む（一晩放置用）
                    self._log_exc(f"scene {sid}")
                    engine.unload()
                    self.queue.set_scene_status(sid, "failed", error=f"{type(exc).__name__}: {exc}")
                self.scene_changed.emit()

            data = self.queue.load()
            done = [s for s in data.get("scenes", []) if s.get("status") == "completed"]
            if not done:
                raise RuntimeError("完了したシーンがありません。")
            engine.unload()
            self.log.emit("動画を結合中...")
            result = assemble(self.project_dir, data["scenes"], self.audio_path,
                              self.preset, self.project_dir / "output" / "music_video.mp4")
            self.finished_ok.emit(str(result))
        except Exception as exc:
            self._log_exc("worker")
            self.failed.emit(str(exc))
        finally:
            engine.unload()
