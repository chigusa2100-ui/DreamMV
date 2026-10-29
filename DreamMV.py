"""DreamMV desktop application entry point."""
from __future__ import annotations

import faulthandler
import json
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from src.dreammv.audio import AudioAnalyzer
from src.dreammv.config import load_config, write_default_config
from src.dreammv.jobs import JobManager
from src.dreammv.planner import StoryPlanner
from src.dreammv.project import ProjectManager
from src.dreammv.project_queue import ProjectQueueService
from src.dreammv.render_worker import AssembleWorker, RenderWorker
from src.dreammv.narration_service import NarrationProjectService
from src.dreammv.narration_render_worker import NarrationRenderWorker


# ---- クラッシュ診断 ----
_crash_log = open(Path.cwd() / "crash.log", "a", encoding="utf-8")
faulthandler.enable(_crash_log, all_threads=True)


def _excepthook(exc_type, exc, tb):
    _crash_log.write("".join(traceback.format_exception(exc_type, exc, tb)))
    _crash_log.flush()
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _excepthook

AUDIO_FILE_FILTER = "Audio (*.mp3 *.wav *.flac *.ogg *.m4a *.aac)"


class NarrationWorker(QThread):
    """朗読の文字起こしと挿絵設計図の作成をバックグラウンドで実行する。"""

    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, audio_path: str, project_dir: str, config_path: str):
        super().__init__()
        self.audio_path = Path(audio_path)
        self.project_dir = Path(project_dir)
        self.config_path = Path(config_path)

    def run(self):
        try:
            self.progress.emit("朗読音声の長さを解析しています...")
            config = load_config(self.config_path)
            info = AudioAnalyzer().analyze(
                str(self.audio_path),
                sample_rate=config["audio_sample_rate"],
                mono=config["audio_mono"],
            )
            duration = float(info["duration"])

            self.progress.emit(
                "Whisperを読み込んでいます。初回は時間がかかる場合があります..."
            )
            service = NarrationProjectService()
            self.progress.emit("朗読を文字起こししています...")

            result = service.create_project(
                audio_file=self.audio_path,
                project_dir=self.project_dir,
                title=self.audio_path.stem,
                audio_duration=duration,
            )
            self.progress.emit("挿絵設計図の保存が完了しました。")
            self.succeeded.emit(result)

        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class DreamMV(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DreamMV v1.1.0 - Animagine XL 4.0")
        self.resize(1000, 900)

        # ---- 音楽MV用状態 ----
        self.selected_path: str | None = None
        self.project_dir: Path | None = None
        self.project: dict = {}
        self.duration: float | None = None
        self.queue_service: ProjectQueueService | None = None
        self.worker: RenderWorker | None = None

        # ---- 朗読用状態 ----
        self.narration_path: str | None = None
        self.narration_duration: float | None = None
        self.narration_worker: NarrationWorker | None = None
        self.narration_render_worker: NarrationRenderWorker | None = None
        self.narration_project_dir: Path | None = None

        # ---- 音楽MV UI ----
        self.label = QLabel("音楽MV：音楽ファイルを選択してください")
        self.button = QPushButton("🎵 音楽ファイルを開く")
        self.project_button = QPushButton("📂 音楽MVプロジェクトを開く")
        self.generate_button = QPushButton("🎬 Generate（音楽MVの設計図を作成）")
        self.generate_button.setEnabled(False)

        # ---- 朗読 UI ----
        self.narration_file_button = QPushButton("📖 朗読ファイルを開く")
        self.narration_label = QLabel("朗読ファイル：未選択")

        self.narration_button = QPushButton("📝 朗読から挿絵設計図を作成")
        self.narration_button.setEnabled(False)

        self.narration_render_button = QPushButton("🎨 Animagineで朗読挿絵を生成")
        self.narration_render_button.setEnabled(False)

        self.narration_log = QLabel(
            "朗読ファイルを選択してから、設計図を作成してください。"
        )
        self.narration_log.setWordWrap(True)

        # ---- 音楽MVキュー UI ----
        self.queue_summary = QLabel(
            "音楽MVキュー：プロジェクトを開くか、設計図を作成してください"
        )
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("シーン進捗：%p%")

        self.refresh_queue_button = QPushButton("🔄 キュー更新")
        self.retry_button = QPushButton("↻ 失敗シーンを再試行")
        self.retry_button.setEnabled(False)

        self.render_button = QPushButton("🎨 AnimagineでMV生成")
        self.render_button.setEnabled(False)

        self.assemble_button = QPushButton(
            "🎞 完了済みシーンから再結合（再生成なし）"
        )
        self.assemble_button.setEnabled(False)

        self.stop_button = QPushButton("■ 中止")
        self.stop_button.setEnabled(False)

        self.render_log = QLabel("")
        self.render_log.setWordWrap(True)

        self.scene_table = QTableWidget(0, 4)
        self.scene_table.setHorizontalHeaderLabels(
            ["シーンID", "シーン名", "状態", "詳細"]
        )
        self.scene_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.scene_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        header = self.scene_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # ---- レイアウト ----
        layout = QVBoxLayout(self)

        layout.addWidget(self.label)
        layout.addWidget(self.button)
        layout.addWidget(self.narration_file_button)
        layout.addWidget(self.narration_label)
        layout.addWidget(self.project_button)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.render_button)
        layout.addWidget(self.narration_button)
        layout.addWidget(self.narration_render_button)
        layout.addWidget(self.narration_log)

        layout.addWidget(self.queue_summary)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.scene_table)

        queue_buttons = QHBoxLayout()
        queue_buttons.addWidget(self.refresh_queue_button)
        queue_buttons.addWidget(self.retry_button)
        layout.addLayout(queue_buttons)

        render_buttons = QHBoxLayout()
        render_buttons.addWidget(self.assemble_button)
        render_buttons.addWidget(self.stop_button)
        layout.addLayout(render_buttons)
        layout.addWidget(self.render_log)

        # ---- ボタン接続 ----
        self.button.clicked.connect(self.open_file)
        self.narration_file_button.clicked.connect(self.open_narration_file)
        self.project_button.clicked.connect(self.open_project)
        self.generate_button.clicked.connect(self.generate_project)
        self.narration_button.clicked.connect(self.start_narration_project)
        self.narration_render_button.clicked.connect(self.start_narration_render)

        self.refresh_queue_button.clicked.connect(self.refresh_queue)
        self.retry_button.clicked.connect(self.retry_failed_scenes)
        self.render_button.clicked.connect(self.start_render)
        self.assemble_button.clicked.connect(self.start_assemble_only)
        self.stop_button.clicked.connect(self.stop_render)

        # ---- 設定 ----
        self.config_path = Path.cwd() / "config.json"
        try:
            write_default_config(self.config_path)
            self.config = load_config(self.config_path)
        except ValueError as exc:
            QMessageBox.warning(self, "設定エラー", str(exc))
            self.config = load_config(None)

    # ------------------------------------------------------------
    # 共通状態
    # ------------------------------------------------------------
    def _busy(self) -> bool:
        return any(
            worker is not None
            for worker in (
                self.worker,
                self.narration_worker,
                self.narration_render_worker,
            )
        )

    # ------------------------------------------------------------
    # 音楽MV：音声読み込み
    # ------------------------------------------------------------
    def open_file(self):
        if self._busy():
            QMessageBox.information(self, "DreamMV", "処理中は変更できません。")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "音楽MV用の音楽ファイルを選択", "", AUDIO_FILE_FILTER
        )
        if not path:
            return

        try:
            info = AudioAnalyzer().analyze(
                path,
                sample_rate=self.config["audio_sample_rate"],
                mono=self.config["audio_mono"],
            )
        except Exception as exc:
            QMessageBox.critical(self, "音楽ファイル解析エラー", str(exc))
            return

        self.selected_path = path
        self.project_dir = None
        self.project = {}
        self.queue_service = None
        self.duration = float(info["duration"])
        self.generate_button.setEnabled(True)

        minutes, seconds = int(self.duration // 60), int(self.duration % 60)
        self.label.setText(
            f"音楽MV：{Path(path).stem}\n"
            f"長さ：{minutes}:{seconds:02d}（{self.duration:.2f} 秒）\n"
            "Generate を押すと、MVの設計図とシーンキューを作成します。"
        )
        self._clear_queue_view()

    # ------------------------------------------------------------
    # 朗読：ファイル選択
    # ------------------------------------------------------------
    def open_narration_file(self):
        if self._busy():
            QMessageBox.information(self, "DreamMV", "処理中はファイルを変更できません。")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "朗読ファイルを選択", "", AUDIO_FILE_FILTER
        )
        if not path:
            return

        try:
            info = AudioAnalyzer().analyze(
                path,
                sample_rate=self.config["audio_sample_rate"],
                mono=self.config["audio_mono"],
            )
            duration = float(info["duration"])
        except Exception as exc:
            QMessageBox.critical(self, "朗読音声解析エラー", str(exc))
            return

        self.narration_path = path
        self.narration_duration = duration
        self.narration_project_dir = None
        self.narration_render_button.setEnabled(False)

        minutes, seconds = int(duration // 60), int(duration % 60)
        self.narration_label.setText(
            f"朗読ファイル：{Path(path).name}\n"
            f"長さ：{minutes}:{seconds:02d}（{duration:.1f} 秒）"
        )
        self.narration_log.setText(
            "朗読ファイルを読み込みました。「朗読から挿絵設計図を作成」を押してください。"
        )
        self.narration_button.setEnabled(True)

    # ------------------------------------------------------------
    # 音楽MV：プロジェクト読み込み
    # ------------------------------------------------------------
    def open_project(self):
        if self._busy():
            QMessageBox.information(self, "DreamMV", "処理中は変更できません。")
            return

        project_dir = QFileDialog.getExistingDirectory(self, "音楽MVプロジェクトを選択")
        if not project_dir:
            return

        try:
            result = ProjectManager(
                StoryPlanner(config_path=self.config_path)
            ).load(project_dir)

            self.project_dir = result["project_dir"]
            self.project = result["project"]
            audio_name = self.project.get("audio", {}).get("filename", "song.mp3")
            audio_path = self.project_dir / audio_name
            self.selected_path = str(audio_path) if audio_path.exists() else None
            self.duration = float(self.project["duration"])
            self.generate_button.setEnabled(False)

            self.label.setText(
                "音楽MVプロジェクト読み込み成功\n"
                f"タイトル：{self.project.get('title', self.project_dir.name)}\n"
                f"長さ：{self.duration:.2f} 秒\n"
                f"シーン数：{self.project.get('scene_count', '-')}\n"
                f"状態：{self.project.get('status', '-')}"
            )
            if self.selected_path is None:
                self.label.setText(
                    self.label.text()
                    + "\n音楽ファイルが見つかりません。音楽ファイルを選び直してください。"
                )

            self.queue_service = ProjectQueueService(self.project_dir)
            self.refresh_queue()

        except Exception as exc:
            QMessageBox.critical(self, "プロジェクト読み込みエラー", str(exc))

    # ------------------------------------------------------------
    # 音楽MV：設計図作成
    # ------------------------------------------------------------
    def generate_project(self):
        if self._busy():
            return
        if not self.selected_path:
            QMessageBox.information(self, "DreamMV", "先に音楽ファイルを選択してください。")
            return

        try:
            manager = ProjectManager(StoryPlanner(config_path=self.config_path))
            result = manager.create_from_audio(self.selected_path, self.project_dir)
            project_dir = result["project_dir"]
            project = result["project"]

            jobs = JobManager(project_dir / self.config["output_subdir"])
            jobs.update("running", project["title"], "planning")

            queue_service = ProjectQueueService(project_dir)
            queue_data = queue_service.create_from_plan(project, title=project["title"])
            jobs.update("completed", project["title"], "planning")

            project["status"] = "planned"
            manager.save(project_dir, project)

            self.project_dir = project_dir
            self.project = project
            self.duration = float(project["duration"])
            self.selected_path = str(project_dir / project["audio"]["filename"])
            self.queue_service = queue_service

            self.label.setText(
                "音楽MVの設計図を作成しました！\n"
                f"タイトル：{project['title']}\n"
                f"シーン数：{project['scene_count']}\n"
                f"キュー内シーン数：{len(queue_data.get('scenes', []))}\n"
                f"保存先：{project_dir}\n\n"
                "「🎨 AnimagineでMV生成」を押すと、シーンごとに動画を生成します。"
            )
            self.refresh_queue()

        except Exception as exc:
            QMessageBox.critical(self, "生成準備エラー", str(exc))
            self.label.setText(f"処理に失敗しました。\n{exc}")

    # ------------------------------------------------------------
    # 音楽MV：キュー表示
    # ------------------------------------------------------------
    def _clear_queue_view(self):
        self.queue_summary.setText("音楽MVキュー：まだ読み込まれていません")
        self.progress_bar.setValue(0)
        self.scene_table.setRowCount(0)
        self.retry_button.setEnabled(False)
        self.render_button.setEnabled(False)
        self.assemble_button.setEnabled(False)

    def refresh_queue(self):
        if self.queue_service is None:
            self._clear_queue_view()
            return

        try:
            data = self.queue_service.load()
            progress = self.queue_service.progress()
            scenes = data.get("scenes", [])
            total = int(progress.get("total", len(scenes)))
            queued = int(progress.get("queued", 0))
            running = int(progress.get("running", 0))
            completed = int(progress.get("completed", 0))
            failed = int(progress.get("failed", 0))
            default_percent = completed / total * 100 if total else 0
            percent = float(progress.get("progress_percent", default_percent))

            self.queue_summary.setText(
                f"音楽MV：総数 {total} / 待機 {queued} / 実行中 {running} / "
                f"完了 {completed} / 失敗 {failed}"
            )
            self.progress_bar.setValue(max(0, min(100, round(percent))))
            self.scene_table.setRowCount(len(scenes))

            for row, scene in enumerate(scenes):
                values = [
                    str(scene.get("id", "-")),
                    str(scene.get("title", scene.get("name", scene.get("description", "シーン")))),
                    str(scene.get("status", "queued")),
                    str(scene.get("error") or scene.get("detail") or ""),
                ]
                for col, value in enumerate(values):
                    self.scene_table.setItem(row, col, QTableWidgetItem(value))

            idle = not self._busy()
            self.retry_button.setEnabled(idle and failed > 0)
            self.render_button.setEnabled(
                idle and self.selected_path is not None and (queued + running) > 0
            )

            completed_with_files = any(
                scene.get("status") == "completed"
                and scene.get("output")
                and Path(scene["output"]).exists()
                for scene in scenes
            )
            self.assemble_button.setEnabled(
                idle
                and self.selected_path is not None
                and self.project_dir is not None
                and completed_with_files
            )

        except FileNotFoundError:
            self._clear_queue_view()
            self.queue_summary.setText(
                "音楽MVキューがありません。Generate で設計図を作成してください。"
            )
        except Exception as exc:
            QMessageBox.warning(self, "キュー読み込みエラー", str(exc))

    def retry_failed_scenes(self):
        if self.queue_service is None or self._busy():
            return
        try:
            count = self.queue_service.retry_failed()
            self.refresh_queue()
            QMessageBox.information(
                self, "失敗シーンの再試行",
                f"{count} 件の失敗シーンを待機状態に戻しました。\n"
                "「🎨 AnimagineでMV生成」を押すと再生成します。",
            )
        except Exception as exc:
            QMessageBox.critical(self, "再試行エラー", str(exc))

    # ------------------------------------------------------------
    # 音楽MV：レンダリング
    # ------------------------------------------------------------
    def _load_model_settings(self) -> dict:
        settings_path = Path.cwd() / "anime_settings.json"
        if settings_path.exists():
            try:
                return json.loads(settings_path.read_text("utf-8-sig"))
            except Exception as exc:
                QMessageBox.warning(self, "設定エラー", f"anime_settings.json を読めません：{exc}")

        old_path = Path.cwd() / "wan_settings.json"
        if old_path.exists():
            try:
                old_settings = json.loads(old_path.read_text("utf-8-sig"))
                return {"models_dir": old_settings.get("models_dir")}
            except Exception:
                pass
        return {}

    def start_render(self):
        if (
            self.queue_service is None or not self.selected_path
            or self.project_dir is None or self._busy()
        ):
            return

        settings = self._load_model_settings()
        self.worker = RenderWorker(
            self.queue_service, self.project_dir, Path(self.selected_path),
            preset="animagine", models_dir=settings.get("models_dir"),
        )
        self.worker.log.connect(self.render_log.setText)
        self.worker.scene_changed.connect(self.refresh_queue)
        self.worker.finished_ok.connect(self._render_done)
        self.worker.failed.connect(self._render_failed)
        self.worker.finished.connect(self._thread_finished)

        self.render_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.render_log.setText("音楽MVのレンダリングを開始しました...")
        self.worker.start()

    def start_assemble_only(self):
        if (
            self.queue_service is None or not self.selected_path
            or self.project_dir is None or self._busy()
        ):
            return

        answer = QMessageBox.question(
            self, "完成済みシーンから再結合",
            "画像生成は行わず、完成済みのシーンクリップと音声だけを結合します。\n"
            "既存の完成動画 music_video.mp4 は上書きされます。続けますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.worker = AssembleWorker(
            self.queue_service, self.project_dir, Path(self.selected_path)
        )
        self.worker.log.connect(self.render_log.setText)
        self.worker.finished_ok.connect(self._render_done)
        self.worker.failed.connect(self._render_failed)
        self.worker.finished.connect(self._thread_finished)

        self.render_button.setEnabled(False)
        self.assemble_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.render_log.setText("完了済みシーンを再結合しています...")
        self.worker.start()

    def stop_render(self):
        if self.worker is not None:
            self.worker.cancel()
            self.stop_button.setEnabled(False)
            self.render_log.setText("中止を受け付けました。実行中のシーンが終わり次第停止します...")
        elif self.narration_render_worker is not None:
            self.narration_render_worker.cancel()
            self.stop_button.setEnabled(False)
            self.narration_log.setText(
                "朗読生成の中止を受け付けました。実行中のシーンが終わり次第停止します..."
            )

    def _render_done(self, path: str):
        self.render_log.setText(f"完成：{path}")
        QMessageBox.information(self, "完成", f"ミュージックビデオを書き出しました。\n{path}")

    def _render_failed(self, msg: str):
        self.render_log.setText(f"失敗：{msg}")
        QMessageBox.critical(self, "レンダリングエラー", msg)

    def _thread_finished(self):
        self.worker = None
        self.stop_button.setEnabled(False)
        self.refresh_queue()

    # ------------------------------------------------------------
    # 朗読：設計図作成
    # ------------------------------------------------------------
    def start_narration_project(self):
        if self._busy():
            QMessageBox.information(self, "DreamMV", "別の処理が実行中です。完了してから試してください。")
            return
        if not self.narration_path:
            QMessageBox.information(self, "DreamMV", "先に朗読ファイルを選択してください。")
            return

        source = Path(self.narration_path)
        parent_dir = QFileDialog.getExistingDirectory(
            self, "朗読プロジェクトの保存先（親フォルダ）を選択"
        )
        if not parent_dir:
            return

        project_dir = Path(parent_dir) / f"{source.stem}_朗読プロジェクト"
        if project_dir.exists() and any(project_dir.iterdir()):
            QMessageBox.warning(
                self, "保存先を確認",
                "同名の朗読プロジェクトが既に存在し、空ではありません。\n別の保存先を選んでください。",
            )
            return

        self.narration_button.setEnabled(False)
        self.narration_file_button.setEnabled(False)
        self.narration_log.setText("朗読プロジェクトを準備しています...")

        self.narration_worker = NarrationWorker(
            audio_path=str(source),
            project_dir=str(project_dir),
            config_path=str(self.config_path),
        )
        self.narration_worker.progress.connect(self.narration_log.setText)
        self.narration_worker.succeeded.connect(self._narration_done)
        self.narration_worker.failed.connect(self._narration_failed)
        self.narration_worker.finished.connect(self._narration_thread_finished)
        self.narration_worker.start()

    def _narration_done(self, result):
        plan = result["plan"]
        self.narration_project_dir = Path(result["project_dir"])

        self.narration_log.setText(
            f"朗読設計図の作成が完了しました：{self.narration_project_dir}"
        )
        scenes = plan.get("scenes", [])
        self.queue_summary.setText(
            f"朗読設計図：シーン総数 {len(scenes)} / 状態：設計完了"
        )
        self.progress_bar.setValue(0)
        self.scene_table.setRowCount(len(scenes))

        for row, scene in enumerate(scenes):
            values = [
                str(scene.get("id", "-")),
                str(scene.get("name", scene.get("title", f"朗読シーン {row + 1:04d}"))),
                str(scene.get("status", "queued")),
                str(scene.get("description", scene.get("text", ""))),
            ]
            for col, value in enumerate(values):
                self.scene_table.setItem(row, col, QTableWidgetItem(value))

        self.narration_render_button.setEnabled(bool(scenes))
        QMessageBox.information(
            self, "朗読の設計図を作成しました",
            f"タイトル：{plan.get('title', self.narration_project_dir.name)}\n"
            f"音声の長さ：{float(plan.get('audio_duration', 0)):.1f} 秒\n"
            f"シーン数：{len(scenes)}\n"
            f"挿絵クリップの基準：{float(plan.get('render_clip_duration', 10)):.0f} 秒\n\n"
            f"保存先：\n{self.narration_project_dir}\n\n"
            "次に「🎨 Animagineで朗読挿絵を生成」を押すと、挿絵動画の生成を開始します。",
        )

    def _narration_failed(self, message):
        self.narration_log.setText(f"朗読プロジェクトの作成に失敗しました：{message}")
        QMessageBox.critical(self, "朗読処理エラー", message)

    def _narration_thread_finished(self):
        self.narration_worker = None
        self.narration_button.setEnabled(self.narration_path is not None)
        self.narration_file_button.setEnabled(True)

    # ------------------------------------------------------------
    # 朗読：挿絵生成
    # ------------------------------------------------------------
    def start_narration_render(self):
        if self._busy():
            QMessageBox.information(self, "DreamMV", "別の処理が実行中です。完了してから試してください。")
            return
        if self.narration_project_dir is None:
            QMessageBox.information(self, "DreamMV", "先に朗読の設計図を作成してください。")
            return

        settings = self._load_model_settings()
        self.narration_render_worker = NarrationRenderWorker(
            project_dir=self.narration_project_dir,
            models_dir=settings.get("models_dir"),
        )
        self.narration_render_worker.log.connect(self.narration_log.setText)
        self.narration_render_worker.scene_changed.connect(self.refresh_narration_queue)
        self.narration_render_worker.finished_ok.connect(self._narration_render_done)
        self.narration_render_worker.failed.connect(self._narration_render_failed)
        self.narration_render_worker.finished.connect(self._narration_render_thread_finished)

        self.narration_render_button.setEnabled(False)
        self.narration_button.setEnabled(False)
        self.narration_file_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.narration_log.setText("朗読挿絵の生成を開始しました...")
        self.narration_render_worker.start()

    def refresh_narration_queue(self):
        if self.narration_project_dir is None:
            return

        queue_file = (
            self.narration_project_dir
            / "narration_render_state"
            / "output"
            / "queue.json"
        )
        if not queue_file.is_file():
            return

        try:
            data = json.loads(queue_file.read_text(encoding="utf-8"))
            scenes = data.get("scenes", [])
            total = len(scenes)
            counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
            for scene in scenes:
                status = scene.get("status", "queued")
                counts[status] = counts.get(status, 0) + 1

            completed = counts["completed"]
            self.queue_summary.setText(
                f"朗読挿絵：総数 {total} / 待機 {counts['queued']} / "
                f"実行中 {counts['running']} / 完了 {completed} / 失敗 {counts['failed']}"
            )
            self.progress_bar.setValue(round(completed / total * 100) if total else 0)
            self.scene_table.setRowCount(len(scenes))

            for row, scene in enumerate(scenes):
                values = [
                    str(scene.get("id", "-")),
                    str(scene.get("name", scene.get("title", "朗読シーン"))),
                    str(scene.get("status", "queued")),
                    str(scene.get("error") or scene.get("description") or ""),
                ]
                for col, value in enumerate(values):
                    self.scene_table.setItem(row, col, QTableWidgetItem(value))

        except Exception as exc:
            self.narration_log.setText(f"朗読キューの更新に失敗しました：{exc}")

    def _narration_render_done(self, path: str):
        self.narration_log.setText(f"朗読動画の生成が完了しました：{path}")
        QMessageBox.information(self, "朗読動画の完成", f"完成した朗読動画を保存しました。\n{path}")

    def _narration_render_failed(self, message: str):
        self.narration_log.setText(f"朗読挿絵の生成に失敗しました：{message}")
        QMessageBox.critical(self, "朗読レンダリングエラー", message)

    def _narration_render_thread_finished(self):
        self.narration_render_worker = None
        self.stop_button.setEnabled(False)
        self.narration_file_button.setEnabled(True)
        self.narration_button.setEnabled(self.narration_path is not None)
        self.refresh_narration_queue()
        self.narration_render_button.setEnabled(self.narration_project_dir is not None)

    # ------------------------------------------------------------
    # 終了時の安全対策
    # ------------------------------------------------------------
    def closeEvent(self, event):
        if self.worker is not None or self.narration_render_worker is not None:
            QMessageBox.information(
                self, "DreamMV",
                "レンダリング中です。「■ 中止」を押し、停止してから閉じてください。",
            )
            event.ignore()
            return

        if self.narration_worker is not None:
            QMessageBox.information(
                self, "DreamMV",
                "朗読の文字起こし処理中です。完了してから閉じてください。",
            )
            event.ignore()
            return

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DreamMV()
    window.show()
    sys.exit(app.exec())
