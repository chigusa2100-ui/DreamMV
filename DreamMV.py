"""DreamMV desktop application entry point."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
)
from src.dreammv.audio import AudioAnalyzer
from src.dreammv.config import load_config, write_default_config
from src.dreammv.jobs import JobManager
from src.dreammv.planner import StoryPlanner
from src.dreammv.project import ProjectManager
from src.dreammv.project_queue import ProjectQueueService
from src.dreammv.render_worker import AssembleWorker, RenderWorker


# ---- クラッシュ診断: 落ちたときの原因を crash.log に残す ----
import faulthandler
import traceback

_crash_log = open(Path.cwd() / "crash.log", "a", encoding="utf-8")
faulthandler.enable(_crash_log, all_threads=True)  # ネイティブ(C/CUDA)クラッシュのスタックを記録


def _excepthook(exc_type, exc, tb):
    _crash_log.write("".join(traceback.format_exception(exc_type, exc, tb)))
    _crash_log.flush()
    sys.__excepthook__(exc_type, exc, tb)


sys.excepthook = _excepthook


class DreamMV(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DreamMV v1.0.2 - Animagine XL 4.0")
        self.resize(820, 700)
        self.selected_path: str | None = None
        self.project_dir: Path | None = None
        self.project: dict = {}
        self.duration: float | None = None
        self.queue_service: ProjectQueueService | None = None
        self.worker: RenderWorker | None = None

        self.label = QLabel("MP3を選択してください")
        self.button = QPushButton("🎵 MP3を開く")
        self.project_button = QPushButton("📂 プロジェクトを開く")
        self.generate_button = QPushButton("🎬 Generate（設計図の作成）")
        self.generate_button.setEnabled(False)
        self.queue_summary = QLabel("キュー: プロジェクトを開くか、MVの設計図を作成してください")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("シーン進捗: %p%")
        self.refresh_queue_button = QPushButton("🔄 キュー更新")
        self.retry_button = QPushButton("↻ 失敗シーンを再試行")
        self.retry_button.setEnabled(False)
        self.render_button = QPushButton("🎨 AnimagineでMV生成")
        self.render_button.setEnabled(False)
        self.assemble_button = QPushButton("🎞 完了済みシーンから再結合（再生成なし）")
        self.assemble_button.setEnabled(False)
        self.stop_button = QPushButton("■ 中止")
        self.stop_button.setEnabled(False)
        self.render_log = QLabel("")
        self.scene_table = QTableWidget(0, 4)
        self.scene_table.setHorizontalHeaderLabels(["シーンID", "シーン名", "状態", "詳細"])
        self.scene_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.scene_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.scene_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        for widget in (self.label, self.button, self.project_button, self.generate_button,
                       self.queue_summary, self.progress_bar, self.scene_table):
            layout.addWidget(widget)
        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_queue_button)
        buttons.addWidget(self.retry_button)
        layout.addLayout(buttons)
        render_buttons = QHBoxLayout()
        render_buttons.addWidget(self.render_button)
        render_buttons.addWidget(self.assemble_button)
        render_buttons.addWidget(self.stop_button)
        layout.addLayout(render_buttons)
        layout.addWidget(self.render_log)

        self.button.clicked.connect(self.open_file)
        self.project_button.clicked.connect(self.open_project)
        self.generate_button.clicked.connect(self.generate_project)
        self.refresh_queue_button.clicked.connect(self.refresh_queue)
        self.retry_button.clicked.connect(self.retry_failed_scenes)
        self.render_button.clicked.connect(self.start_render)
        self.assemble_button.clicked.connect(self.start_assemble_only)
        self.stop_button.clicked.connect(self.stop_render)

        self.config_path = Path.cwd() / "config.json"
        try:
            write_default_config(self.config_path)
            self.config = load_config(self.config_path)
        except ValueError as exc:
            QMessageBox.warning(self, "設定エラー", str(exc))
            self.config = load_config(None)

    # ------------------------------------------------------------ input
    def open_file(self):
        if self.worker is not None:
            QMessageBox.information(self, "DreamMV", "レンダリング中は変更できません。")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "音声ファイルを選択", "", "Audio (*.mp3 *.wav *.flac *.ogg *.m4a)"
        )
        if not path:
            return
        try:
            info = AudioAnalyzer().analyze(
                path, sample_rate=self.config["audio_sample_rate"],
                mono=self.config["audio_mono"],
            )
        except Exception as exc:
            QMessageBox.critical(self, "音声解析エラー", str(exc))
            return
        self.selected_path = path
        self.project_dir = None
        self.project = {}
        self.queue_service = None
        self.duration = info["duration"]
        minutes, seconds = int(self.duration // 60), int(self.duration % 60)
        self.generate_button.setEnabled(True)
        self.label.setText(
            f"楽曲: {Path(path).stem}\n長さ: {minutes}:{seconds:02d} ({self.duration:.2f} 秒)\n"
            "Generate を押すと、MVの設計図とシーンキューを作成します。"
        )
        self._clear_queue_view()

    def open_project(self):
        if self.worker is not None:
            QMessageBox.information(self, "DreamMV", "レンダリング中は変更できません。")
            return
        project_dir = QFileDialog.getExistingDirectory(self, "DreamMVプロジェクトを選択")
        if not project_dir:
            return
        try:
            result = ProjectManager(StoryPlanner(config_path=self.config_path)).load(project_dir)
            self.project_dir = result["project_dir"]
            self.project = result["project"]
            audio_name = self.project.get("audio", {}).get("filename", "song.mp3")
            audio_path = self.project_dir / audio_name
            self.selected_path = str(audio_path) if audio_path.exists() else None
            self.duration = float(self.project["duration"])
            self.generate_button.setEnabled(False)  # 既存プロジェクトのキューを誤って作り直さない
            self.label.setText(
                "プロジェクト読み込み成功\n"
                f"タイトル: {self.project.get('title', self.project_dir.name)}\n"
                f"長さ: {self.duration:.2f} 秒\n"
                f"シーン数: {self.project.get('scene_count', '-')}\n"
                f"状態: {self.project.get('status', '-')}"
            )
            if self.selected_path is None:
                self.label.setText(self.label.text() + "\n音声ファイルが見つかりません。MP3を選び直してください。")
            self.queue_service = ProjectQueueService(self.project_dir)
            self.refresh_queue()
        except Exception as exc:
            QMessageBox.critical(self, "プロジェクト読み込みエラー", str(exc))

    def generate_project(self):
        if self.worker is not None:
            return
        if not self.selected_path:
            QMessageBox.information(self, "DreamMV", "先に音声ファイルを選択してください。")
            return
        try:
            planner = StoryPlanner(config_path=self.config_path)
            manager = ProjectManager(planner)
            result = manager.create_from_audio(self.selected_path, self.project_dir)
            project_dir, project = result["project_dir"], result["project"]
            jobs = JobManager(project_dir / self.config["output_subdir"])
            jobs.update("running", project["title"], "planning")
            queue_service = ProjectQueueService(project_dir)
            queue_data = queue_service.create_from_plan(project, title=project["title"])
            jobs.update("completed", project["title"], "planning")
            project["status"] = "planned"
            manager.save(project_dir, project)
            self.project_dir, self.project = project_dir, project
            self.duration = float(project["duration"])
            self.selected_path = str(project_dir / project["audio"]["filename"])
            self.queue_service = queue_service
            self.label.setText(
                "MVの設計図を作成しました！\n"
                f"タイトル: {project['title']}\nシーン数: {project['scene_count']}\n"
                f"キュー内シーン数: {len(queue_data.get('scenes', []))}\n保存先: {project_dir}\n\n"
                "「🎨 AnimagineでMV生成」を押すと、シーンごとに動画を生成します。"
            )
            self.refresh_queue()
        except Exception as exc:
            QMessageBox.critical(self, "生成準備エラー", str(exc))
            self.label.setText(f"処理に失敗しました。\n{exc}")

    # ------------------------------------------------------------ queue view
    def _clear_queue_view(self):
        self.queue_summary.setText("キュー: まだ読み込まれていません")
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
                f"シーン総数: {total}   待機: {queued}   実行中: {running}   完了: {completed}   失敗: {failed}"
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
            idle = self.worker is None
            self.retry_button.setEnabled(idle and failed > 0)
            self.render_button.setEnabled(idle and self.selected_path is not None and (queued + running) > 0)
            completed_with_files = any(
                scene.get("status") == "completed"
                and scene.get("output")
                and Path(scene["output"]).exists()
                for scene in scenes
            )
            self.assemble_button.setEnabled(
                idle and self.selected_path is not None and self.project_dir is not None
                and completed_with_files
            )
        except FileNotFoundError:
            self._clear_queue_view()
            self.queue_summary.setText("キューがありません。Generate で設計図を作成してください。")
        except Exception as exc:
            QMessageBox.warning(self, "キュー読み込みエラー", str(exc))

    def retry_failed_scenes(self):
        if self.queue_service is None or self.worker is not None:
            return
        try:
            count = self.queue_service.retry_failed()
            self.refresh_queue()
            QMessageBox.information(
                self, "失敗シーンの再試行",
                f"{count} 件の失敗シーンを待機状態に戻しました。\n"
                "「🎨 AnimagineでMV生成」を押すと、これらを再生成します。",
            )
        except Exception as exc:
            QMessageBox.critical(self, "再試行エラー", str(exc))

    # ------------------------------------------------------------ rendering
    def start_render(self):
        if self.queue_service is None or not self.selected_path or self.project_dir is None:
            return
        if self.worker is not None:
            return
        settings_path = Path.cwd() / "anime_settings.json"
        settings: dict = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text("utf-8-sig"))
            except Exception as exc:
                QMessageBox.warning(self, "設定エラー", f"anime_settings.json を読めません: {exc}")
        # Old settings are read only as a migration fallback for the model cache path.
        if not settings and (Path.cwd() / "wan_settings.json").exists():
            try:
                old_settings = json.loads((Path.cwd() / "wan_settings.json").read_text("utf-8-sig"))
                settings = {"models_dir": old_settings.get("models_dir")}
            except Exception:
                settings = {}
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
        self.render_log.setText("レンダリングを開始しました（初回はモデルの読み込みに時間がかかります）...")
        self.worker.start()

    def start_assemble_only(self):
        """Mux existing completed clips; do not initialize Animagine or regenerate scenes."""
        if self.queue_service is None or not self.selected_path or self.project_dir is None:
            return
        if self.worker is not None:
            return
        answer = QMessageBox.question(
            self, "完成済みシーンから再結合",
            "画像生成は行わず、完了済みのシーンクリップと音声だけを結合します。\\n"
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
        self.render_log.setText("完了済みシーンを再結合しています（画像の再生成はしません）...")
        self.worker.start()

    def stop_render(self):
        if self.worker is not None:
            self.worker.cancel()
            self.stop_button.setEnabled(False)
            self.render_log.setText("中止を受け付けました。実行中のシーンが終わり次第止まります...")

    def _render_done(self, path: str):
        self.render_log.setText(f"完成: {path}")
        QMessageBox.information(self, "完成", f"ミュージックビデオを書き出しました。\n{path}")

    def _render_failed(self, msg: str):
        self.render_log.setText(f"失敗: {msg}")
        QMessageBox.critical(self, "レンダリングエラー", msg)

    def _thread_finished(self):
        self.worker = None
        self.stop_button.setEnabled(False)
        self.refresh_queue()

    def closeEvent(self, event):
        if self.worker is not None:
            QMessageBox.information(
                self, "DreamMV",
                "レンダリング中です。「■ 中止」を押し、停止してから閉じてください。",
            )
            event.ignore()
            return
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DreamMV()
    window.show()
    sys.exit(app.exec())
