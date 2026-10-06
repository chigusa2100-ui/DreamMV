from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QVBoxLayout,
)
import sys
from pathlib import Path
import json
import shutil

from src.dreammv.audio import AudioAnalyzer

class DreamMV(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DreamMV v0.1")
        self.resize(500, 250)

        self.label = QLabel("MP3を選択してください")
        self.button = QPushButton("🎵 MP3を開く")
        self.project_button = QPushButton("📂 プロジェクトを開く")
        self.generate_button = QPushButton("🎬 Generate")
        self.generate_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        layout.addWidget(self.project_button)
        layout.addWidget(self.generate_button)

        self.button.clicked.connect(self.open_file)
        self.project_button.clicked.connect(self.open_project)
        self.generate_button.clicked.connect(self.generate_project)

    def open_project(self):
        project_dir = QFileDialog.getExistingDirectory(
            self,
            "DreamMVプロジェクトを開く"
        )

        if not project_dir:
            return

        project_file = Path(project_dir) / "project.json"

        if not project_file.exists():
            self.label.setText(
                "project.json が見つかりません\n\n"
                f"選択された場所：\n{project_dir}"
            )
            return

        try:
            self.project = json.loads(
                project_file.read_text(encoding="utf-8")
            )
            # タイトルが "song" に壊れていたら、フォルダ名から復元する
            if self.project.get("title") == "song":
                self.project["title"] = Path(project_dir).stem
            print("読み込んだプロジェクト情報:", self.project)
            self.selected_path = str(Path(project_dir) / "song.mp3")
            self.project_dir = Path(project_dir)
            self.duration = self.project["duration"]

            self.label.setText(
                "プロジェクト読み込み成功！\n\n"
                f"タイトル：{self.project['title']}\n"
                f"長さ：{self.project['duration']}\n"
                f"状態：{self.project['status']}"
            )

            self.generate_button.setEnabled(True)

        except Exception as e:
            self.label.setText(
                "project.json の読み込みに失敗しました\n\n"
                f"{e}"
            )

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open MP3",
            "",
            "Audio (*.mp3)"
        )

        if path:
            self.selected_path = path
            self.generate_button.setEnabled(True)

            analyzer = AudioAnalyzer()
            result = analyzer.analyze(path)
            self.duration = result["duration"]
            minutes = int(result["duration"] // 60)
            seconds = int(result["duration"] % 60)

            self.label.setText(
                f"{path}\n\n長さ：{minutes}:{seconds:02d}"
            )

    def run_test_generation(self, output_dir):
        test_file = output_dir / "generate_test.txt"
        test_file.write_text(
            "DreamMV Generate Test OK",
            encoding="utf-8"
        )

    def generate_project(self):
        if not self.selected_path:
            return

        source = Path(self.selected_path)

        project_dir = getattr(
            self,
            "project_dir",
            source.parent / f"{source.stem}.dreammv"
        )
        scenes_dir = project_dir / "scenes"
        output_dir = project_dir / "output"

        scenes_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        if source != project_dir / "song.mp3":
            shutil.copy2(source, project_dir / "song.mp3")

        project = {
           "title": getattr(self, "project", {}).get("title", source.stem),
           "duration": self.duration,
           "status": "created"
        }

        (project_dir / "project.json").write_text(
            json.dumps(project, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        job_file = output_dir / "job.json"

        job = {
            "title": project["title"],
            "status": "queued",
            "type": "test",
            "error": None
        }

        try:
            # 生成待ち
            job_file.write_text(
                json.dumps(job, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # テスト処理開始
            job["status"] = "running"
            job_file.write_text(
                json.dumps(job, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # テスト処理（現時点では成功するだけのテスト）
            self.run_test_generation(output_dir)

            # テスト処理完了
            job["status"] = "completed"

        except Exception as e:
            # エラー内容を記録
            job["status"] = "failed"
            job["error"] = str(e)

        finally:
            # 最終状態を保存
            job_file.write_text(
                json.dumps(job, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        status_text = {
            "queued": "生成待ち",
            "running": "テスト処理中",
            "completed": "テスト完了",
            "failed": "生成失敗"
        }

        self.label.setText(
            f"プロジェクト：{project['title']}\n"
            f"状態：{status_text.get(job['status'], job['status'])}\n"
            f"保存先：{project_dir}"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DreamMV()
    window.show()
    app.exec()