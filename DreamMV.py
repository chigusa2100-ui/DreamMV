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

            self.label.setText(
                "プロジェクト読み込み成功！\n\n"
                f"タイトル：{self.project['title']}\n"
                f"長さ：{self.project['duration']}\n"
                f"状態：{self.project['status']}"
            )

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

    def generate_project(self):
        if not self.selected_path:
            return

        source = Path(self.selected_path)

        project_dir = source.parent / f"{source.stem}.dreammv"
        scenes_dir = project_dir / "scenes"
        output_dir = project_dir / "output"

        scenes_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source, project_dir / "song.mp3")

        project = {
            "title": source.stem,
            "duration": self.duration,
            "status": "created"
        }

        (project_dir / "project.json").write_text(
            json.dumps(project, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        self.label.setText(
            f"プロジェクト作成完了！\n\n{project_dir}"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DreamMV()
    window.show()
    app.exec()