
"""Background worker for narration project creation."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.dreammv.audio import AudioAnalyzer
from src.dreammv.config import load_config
from src.dreammv.narration_service import NarrationProjectService


class NarrationWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        audio_path: str,
        project_dir: str,
        config_path: str,
    ) -> None:
        super().__init__()
        self.audio_path = Path(audio_path)
        self.project_dir = Path(project_dir)
        self.config_path = Path(config_path)

    def run(self) -> None:
        try:
            self.progress.emit("音声の長さを解析しています...")

            config = load_config(self.config_path)
            info = AudioAnalyzer().analyze(
                str(self.audio_path),
                sample_rate=config["audio_sample_rate"],
                mono=config["audio_mono"],
            )
            duration = float(info["duration"])

            self.progress.emit(
                "Whisperを初期化しています。初回は時間がかかる場合があります..."
            )

            # Initialize the model in this worker thread, not in the GUI.
            service = NarrationProjectService()

            self.progress.emit("朗読音声を文字起こししています...")

            result = service.create_project(
                audio_file=self.audio_path,
                project_dir=self.project_dir,
                title=self.audio_path.stem,
                audio_duration=duration,
            )

            self.progress.emit("挿絵設計図を保存しました。")
            self.succeeded.emit(result)

        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
