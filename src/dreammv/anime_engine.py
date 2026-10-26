"""Lightweight anime engine: Animagine XL (SDXL) still image + camera-move clip.

WanEngine と同じ generate() インターフェース。1シーン=1枚のアニメ絵を生成し、
ffmpeg でゆっくりズーム/パンさせて mp4 にする（キャラ自体は動かない）。
"""
from __future__ import annotations

import gc
import random
import subprocess
from pathlib import Path
from typing import Callable

from .wan_engine import PRESETS

QUALITY_TAGS = "masterpiece, high score, great score, absurdres"
DEFAULT_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, "
    "fewer digits, cropped, worst quality, low quality, low score, bad score, "
    "average score, signature, watermark, username, blurry"
)
MOTIONS = ("zoom_in", "pan_right", "zoom_out", "pan_left")


def _ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ken_burns(image_path: str | Path, out_path: str | Path, duration: float,
              fps: int = 24, size: tuple[int, int] = (1280, 720),
              motion: str = "zoom_in") -> Path:
    """静止画を、ゆっくりしたカメラワーク付きの mp4 にする（torch不要）。"""
    frames = max(int(round(duration * fps)), fps)
    d = frames
    center_y = "ih/2-(ih/zoom/2)"
    exprs = {
        "zoom_in":   (f"1+0.12*on/{d}", "iw/2-(iw/zoom/2)", center_y),
        "zoom_out":  (f"1.12-0.12*on/{d}", "iw/2-(iw/zoom/2)", center_y),
        "pan_right": ("1.12", f"(iw-iw/zoom)*on/{d}", center_y),
        "pan_left":  ("1.12", f"(iw-iw/zoom)*(1-on/{d})", center_y),
    }
    z, x, y = exprs[motion]
    vf = f"zoompan=z='{z}':x='{x}':y='{y}':d={d}:s={size[0]}x{size[1]}:fps={fps}"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        _ffmpeg(), "-y", "-i", str(image_path), "-vf", vf, "-frames:v", str(frames),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-an", str(out_path),
    ], check=True, capture_output=True)
    return out_path


class AnimeEngine:
    def __init__(self, preset: str = "anime", models_dir: str | Path | None = None,
                 offload: bool = True):
        self.preset_name = preset
        self.cfg = PRESETS[preset]
        self.models_dir = str(models_dir) if models_dir else None
        self.offload = offload
        self.pipe = None

    def load(self) -> None:
        if self.pipe is not None:
            return
        import torch
        from diffusers import StableDiffusionXLPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA対応GPUが見つかりません。NVIDIA GPUとドライバを確認してください。")
        kw = {"cache_dir": self.models_dir} if self.models_dir else {}
        pipe = StableDiffusionXLPipeline.from_pretrained(
            self.cfg["repo"], torch_dtype=torch.float16, use_safetensors=True,
            add_watermarker=False, **kw,
        )
        if self.offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
        self.pipe = pipe

    def unload(self) -> None:
        self.pipe = None
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

    def generate(self, prompt: str, out_path: str | Path, duration: float,
                 seed: int | None = None, negative_prompt: str = DEFAULT_NEGATIVE,
                 on_step: Callable[[int, int], None] | None = None) -> Path:
        import torch
        from PIL import Image

        self.load()
        c = self.cfg
        seed = random.randint(0, 2**31 - 1) if seed is None else seed
        gen = torch.Generator(device="cpu").manual_seed(seed)
        steps = c["steps"]

        def _cb(pipe, i, t, kwargs):
            if on_step:
                on_step(i + 1, steps)
            return kwargs

        image = self.pipe(
            prompt=f"{prompt}, {QUALITY_TAGS}", negative_prompt=negative_prompt,
            width=c["gen_width"], height=c["gen_height"],
            guidance_scale=c["guidance"], num_inference_steps=steps,
            generator=gen, callback_on_step_end=_cb,
        ).images[0]

        # 16:9 に中央クロップ → 大きめに拡大（zoompan のカクつき対策）
        w, h = image.size
        crop_h = int(w * 9 / 16)
        top = max((h - crop_h) // 2, 0)
        image = image.crop((0, top, w, top + min(crop_h, h))).resize((2560, 1440), Image.LANCZOS)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        still = out_path.with_suffix(".png")  # 静止画も残す（後で画像→動画に使える）
        image.save(still)
        return ken_burns(still, out_path, duration, fps=c["fps"],
                         size=(c["width"], c["height"]), motion=MOTIONS[seed % len(MOTIONS)])
