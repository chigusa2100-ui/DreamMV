
"""Native LTX-2.5 video generation engine.

DreamMV launches the LTX-2.5 native pipeline CLI in its own Python
environment. ComfyUI is not required.
"""
from __future__ import annotations

import math
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path


DEFAULT_LTX_ROOT = Path(r"C:\AI\DreamMV-LTX25\LTX-2")
DEFAULT_MODEL_ROOT = Path(r"C:\AI\DreamMV-LTX25\models")

DEFAULT_WIDTH = 704
DEFAULT_HEIGHT = 384
DEFAULT_FPS = 24

JAPANESE_ANIME_STYLE = (
    "Japanese 2D anime illustration style, "
    "hand-drawn Japanese anime, "
    "refined anime character design, "
    "expressive anime eyes, "
    "delicate clean line art, "
    "detailed cel shading, "
    "high-quality Japanese animation aesthetic"
)


class LTX25Error(RuntimeError):
    """Raised when native LTX-2.5 generation fails."""


class LTX25Engine:
    """Run the native LTX-2.5 distilled pipeline."""

    def __init__(
        self,
        ltx_root: str | Path = DEFAULT_LTX_ROOT,
        model_root: str | Path = DEFAULT_MODEL_ROOT,
        timeout: float = 3600.0,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        fps: int = DEFAULT_FPS,
    ):
        self.ltx_root = Path(ltx_root)
        self.model_root = Path(model_root)

        self.python = self.ltx_root / ".venv" / "Scripts" / "python.exe"

        self.timeout = max(10.0, float(timeout))
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)

        self.transformer_path = (
            self.model_root
            / "diffusion_models"
            / "ltx-2.5-22b-distilled-transformer-bf16.safetensors"
        )
        self.text_encoder_path = (
            self.model_root
            / "text_encoders"
            / "gemma4-12b-with-proj-ltx-2.5-bf16.safetensors"
        )
        self.video_vae_path = (
            self.model_root
            / "vae"
            / "ltx-2.5-video-vae-bf16.safetensors"
        )
        self.audio_vae_path = (
            self.model_root
            / "vae"
            / "ltx-2.5-audio-vae-bf16.safetensors"
        )
        self.duration_head_path = (
            self.model_root
            / "model_patches"
            / "ltx-2.5-duration-head-bf16.safetensors"
        )
        self.spatial_upsampler_path = (
            self.model_root
            / "latent_upscale_models"
            / "ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"
        )

        self._loaded = False
        self._process: subprocess.Popen | None = None
        self._process_lock = threading.Lock()
        self._cancel_event = threading.Event()

    def _required_paths(self) -> list[Path]:
        return [
            self.python,
            self.transformer_path,
            self.text_encoder_path,
            self.video_vae_path,
            self.audio_vae_path,
            self.duration_head_path,
            self.spatial_upsampler_path,
        ]

    def load(self) -> None:
        """Validate the native runtime and model files.

        Model weights are loaded by the LTX CLI process, not by DreamMV.
        """
        missing = [
            path for path in self._required_paths()
            if not path.is_file()
        ]

        if missing:
            details = "\n".join(f"  - {path}" for path in missing)
            raise LTX25Error(
                "LTX-2.5 runtime or model files are missing:\n"
                f"{details}"
            )

        if not self.ltx_root.is_dir():
            raise LTX25Error(
                f"LTX-2.5 directory does not exist: {self.ltx_root}"
            )

        self._cancel_event.clear()
        self._loaded = True

    def unload(self) -> None:
        """Stop an active generation process and release engine state."""
        self.cancel()
        self._loaded = False

    def cancel(self) -> None:
        """Request cancellation of the active CLI process."""
        self._cancel_event.set()

        with self._process_lock:
            process = self._process

        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            except OSError:
                pass

    @staticmethod
    def frame_count(duration: float) -> int:
        """Return a frame count compatible with the LTX temporal stride.

        LTX uses frame counts of 8n+1.
        """
        duration = max(0.1, float(duration))
        required_frames = math.ceil(duration * DEFAULT_FPS)
        return max(9, math.ceil((required_frames - 1) / 8) * 8 + 1)

    @staticmethod
    def build_prompt(prompt: str) -> str:
        """Add the default Japanese anime style without replacing the scene."""
        prompt = str(prompt or "").strip()

        if not prompt:
            raise LTX25Error("The scene prompt is empty.")

        lowered = prompt.lower()

        style_markers = (
            "japanese 2d anime",
            "hand-drawn japanese anime",
            "japanese anime illustration",
        )

        if any(marker in lowered for marker in style_markers):
            return prompt

        return f"{JAPANESE_ANIME_STYLE}. {prompt}"

    def build_command(
        self,
        prompt: str,
        duration: float,
        output_path: str | Path,
        seed: int | None = None,
    ) -> list[str]:
        """Build the native LTX-2.5 CLI command."""
        if not self._loaded:
            self.load()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if seed is None:
            seed = secrets.randbelow(2**31 - 1)

        frames = self.frame_count(duration)

        return [
            str(self.python),
            "-m",
            "ltx_pipelines.distilled",
            "--transformer-path",
            str(self.transformer_path),
            "--text-encoder-path",
            str(self.text_encoder_path),
            "--video-vae-path",
            str(self.video_vae_path),
            "--audio-vae-path",
            str(self.audio_vae_path),
            "--duration-head-path",
            str(self.duration_head_path),
            "--spatial-upsampler-path",
            str(self.spatial_upsampler_path),
            "--prompt",
            self.build_prompt(prompt),
            "--output-path",
            str(output_path.resolve()),
            "--seed",
            str(int(seed)),
            "--offload",
            "disk",
            "--quantization",
            "fp8-cast",
            "--height",
            str(self.height),
            "--width",
            str(self.width),
            "--num-frames",
            str(frames),
            "--frame-rate",
            str(self.fps),
        ]

    def generate(
        self,
        prompt: str,
        duration: float,
        output_path: str | Path,
        seed: int | None = None,
    ) -> Path:
        """Generate one video clip using the native LTX-2.5 CLI."""
        if not self._loaded:
            self.load()

        if self._cancel_event.is_set():
            raise LTX25Error("LTX-2.5 generation was cancelled.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        log_path = output_path.with_suffix(".ltx25.log")
        command = self.build_command(
            prompt=prompt,
            duration=duration,
            output_path=output_path,
            seed=seed,
        )

        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"

        started_at = time.monotonic()

        try:
            with log_path.open("w", encoding="utf-8") as log_file:
                log_file.write("Starting native LTX-2.5 generation.\n")
                log_file.write("Command:\n")
                log_file.write(subprocess.list2cmdline(command) + "\n\n")
                log_file.flush()

                process = subprocess.Popen(
                    command,
                    cwd=str(self.ltx_root),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    env=environment,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0
                    ),
                )

                with self._process_lock:
                    self._process = process

                while process.poll() is None:
                    if self._cancel_event.is_set():
                        self.cancel()
                        raise LTX25Error(
                            "LTX-2.5 generation was cancelled."
                        )

                    if time.monotonic() - started_at > self.timeout:
                        self.cancel()
                        raise LTX25Error(
                            f"LTX-2.5 generation timed out after "
                            f"{self.timeout:.0f} seconds."
                        )

                    time.sleep(0.5)

                return_code = process.returncode

            if return_code != 0:
                try:
                    log_text = log_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                except OSError:
                    log_text = "(Could not read LTX log.)"

                tail = "\n".join(log_text.splitlines()[-60:])

                raise LTX25Error(
                    f"LTX-2.5 CLI failed with exit code "
                    f"{return_code}.\n"
                    f"Log: {log_path}\n\n{tail}"
                )

            if not output_path.is_file():
                raise LTX25Error(
                    "LTX-2.5 finished without creating the output video.\n"
                    f"Expected: {output_path}\n"
                    f"Log: {log_path}"
                )

            if output_path.stat().st_size == 0:
                raise LTX25Error(
                    f"LTX-2.5 created an empty video: {output_path}"
                )

            return output_path

        except LTX25Error:
            raise
        except OSError as exc:
            raise LTX25Error(
                f"Could not start the native LTX-2.5 process: {exc}"
            ) from exc
        finally:
            with self._process_lock:
                self._process = None
