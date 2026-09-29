from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QFileDialog,
    QVBoxLayout,
)
import sys


class DreamMV(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DreamMV v0.1")
        self.resize(500, 250)

        self.label = QLabel("MP3を選択してください")
        self.button = QPushButton("🎵 MP3を開く")

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.open_file)

    def from src.dreammv.audio import AudioAnalyzer

# ...

def open_file(self):
    path, _ = QFileDialog.getOpenFileName(
        self,
        "Open MP3",
        "",
        "Audio (*.mp3)"
    )

    if path:
        analyzer = AudioAnalyzer()

        result = analyzer.analyze(path)

        minutes = int(result["duration"] // 60)
        seconds = int(result["duration"] % 60)

        self.label.setText(
            f"{path}\n\n長さ：{minutes}:{seconds:02d}"
        ):
        path, _ = QFileDialog.getOpenFileName(
             self,
            "Open MP3",
            "",
            "Audio (*.mp3)"
        )

        if path:
            self.label.setText(path)


app = QApplication(sys.argv)
window = DreamMV()
window.show()
app.exec()
