"""Lightweight anime engine: Animagine XL (SDXL) still image + camera-move clip.

Generate one anime still image per scene, then create a slow camera-move
MP4 with ffmpeg. CompelForSDXL handles prompt conditioning for SDXL.
"""

from __future__ import annotations

import gc
import random
import subprocess
from pathlib import Path
from typing import Callable


QUALITY_TAGS = "masterpiece, high score, great score, absurdres"

DEFAULT_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, "
    "fewer digits, cropped, worst quality, low quality, low score, bad score, "
    "average score, signature, watermark, username, blurry"
)

MOTIONS = ("zoom_in", "pan_right", "zoom_out", "pan_left")

# Animagine XL 4.0 is an SDXL still-image model.
# Keep the active engine independent of WanEngine.
ANIME_CONFIG: dict[str, object] = {
    "repo": "cagliostrolab/animagine-xl-4.0",
    "width": 1280,
    "height": 720,
    "fps": 24,
    "gen_width": 1024,
    "gen_height": 1024,
    "steps": 28,
    "guidance": 5.0,
}


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def ken_burns(
    image_path: str | Path,
    out_path: str | Path,
    duration: float,
    fps: int = 24,
    size: tuple[int, int] = (1280, 720),
    motion: str = "zoom_in",
) -> Path:
    """Turn a still image into an MP4 with a slow camera move."""
    frames = max(int(round(duration * fps)), fps)
    d = frames
    center_y = "ih/2-(ih/zoom/2)"

    exprs = {
        "zoom_in": (f"1+0.12*on/{d}", "iw/2-(iw/zoom/2)", center_y),
        "zoom_out": (f"1.12-0.12*on/{d}", "iw/2-(iw/zoom/2)", center_y),
        "pan_right": ("1.12", f"(iw-iw/zoom)*on/{d}", center_y),
        "pan_left": ("1.12", f"(iw-iw/zoom)*(1-on/{d})", center_y),
    }

    if motion not in exprs:
        raise ValueError(f"unknown camera motion: {motion}")

    z, x, y = exprs[motion]
    vf = (
        f"zoompan=z='{z}':x='{x}':y='{y}':"
        f"d={d}:s={size[0]}x{size[1]}:fps={fps}"
    )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            _ffmpeg(),
            "-y",
            "-i",
            str(image_path),
            "-vf",
            vf,
            "-frames:v",
            str(frames),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-an",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )

    return out_path


class AnimeEngine:
    def __init__(
        self,
        preset: str = "anime",
        models_dir: str | Path | None = None,
        offload: bool = True,
    ):
        if preset not in ("anime", "animagine"):
            raise ValueError(f"unknown image-generation preset: {preset}")

        self.preset_name = "animagine"
        self.cfg = ANIME_CONFIG
        self.models_dir = str(models_dir) if models_dir else None
        self.offload = offload

        self.pipe = None
        self.compel = None

    def load(self) -> None:
        if self.pipe is not None:
            return

        import torch
        from compel import CompelForSDXL
        from diffusers import StableDiffusionXLPipeline

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA対応GPUが見つかりません。"
                "NVIDIA GPUとドライバーを確認してください。"
            )

        kw = {"cache_dir": self.models_dir} if self.models_dir else {}

        pipe = StableDiffusionXLPipeline.from_pretrained(
            str(self.cfg["repo"]),
            torch_dtype=torch.float16,
            use_safetensors=True,
            add_watermarker=False,
            **kw,
        )

        # Reduce SDXL memory usage for GPUs with 8 GB VRAM.
        if hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()

        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()

        if self.offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")

        # Build SDXL prompt conditioning with Compel.
        # Keep the same pipeline and its existing memory configuration.
        try:
            compel = CompelForSDXL(pipe, device="cuda")
        except Exception:
            del pipe
            gc.collect()
            torch.cuda.empty_cache()
            raise

        self.pipe = pipe
        self.compel = compel

    def unload(self) -> None:
        self.compel = None
        self.pipe = None

        gc.collect()

        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass

    def generate(
        self,
        prompt: str,
        out_path: str | Path,
        duration: float,
        seed: int | None = None,
        negative_prompt: str = DEFAULT_NEGATIVE,
        on_step: Callable[[int, int], None] | None = None,
    ) -> Path:
        import torch
        from PIL import Image

        self.load()

        if self.pipe is None or self.compel is None:
            raise RuntimeError("Animagine pipeline or Compel is not initialized.")

        c = self.cfg
        seed = random.randint(0, 2**31 - 1) if seed is None else seed
        gen = torch.Generator(device="cpu").manual_seed(seed)
        steps = int(c["steps"])

        def _cb(pipe, i, t, kwargs):
            if on_step:
                on_step(i + 1, steps)
            return kwargs

        full_prompt = f"{prompt}, {QUALITY_TAGS}"

        # CompelForSDXL returns positive and negative SDXL conditioning.
        # Pass embeddings instead of raw strings to avoid the ordinary
        # tokenizer truncation path for long prompts.
        with torch.no_grad():
            conditioning = self.compel(
                main_prompt=full_prompt,
                negative_prompt=negative_prompt,
            )

            image = self.pipe(
                prompt_embeds=conditioning.embeds,
                pooled_prompt_embeds=conditioning.pooled_embeds,
                negative_prompt_embeds=conditioning.negative_embeds,
                negative_pooled_prompt_embeds=conditioning.negative_pooled_embeds,
                width=int(c["gen_width"]),
                height=int(c["gen_height"]),
                guidance_scale=float(c["guidance"]),
                num_inference_steps=steps,
                generator=gen,
                callback_on_step_end=_cb,
            ).images[0]

            del conditioning

        # Crop the square image to 16:9, then upscale for the video output.
        w, h = image.size
        crop_h = int(w * 9 / 16)
        top = max((h - crop_h) // 2, 0)

        image = image.crop(
            (0, top, w, top + min(crop_h, h))
        ).resize((2560, 1440), Image.LANCZOS)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Keep the still image as well as the MP4.
        still = out_path.with_suffix(".png")
        image.save(still)

        return ken_burns(
            still,
            out_path,
            duration,
            fps=int(c["fps"]),
            size=(int(c["width"]), int(c["height"])),
            motion=MOTIONS[seed % len(MOTIONS)],
        )