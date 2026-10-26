"""Whisper transcription support for DreamMV."""

from pathlib import Path

from faster_whisper import WhisperModel


class WhisperEngine:

    def __init__(
        self,
        model_name="small",
    ):

        self.model = WhisperModel(
            model_name,
            device="cpu"
        )

    def transcribe(
        self,
        audio_file,
    ):

        audio_file = Path(
            audio_file
        )

        segments, _ = self.model.transcribe(
            str(audio_file)
        )

        result = []

        for segment in segments:

            result.append(
                {
                    "start": float(
                        segment.start
                    ),

                    "end": float(
                        segment.end
                    ),

                    "text": segment.text.strip(),
                }
            )

        return result
