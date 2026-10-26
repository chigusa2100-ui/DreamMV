"""Wan 2.x video engine (diffusers). Lazy-loaded; one clip per scene."""
from __future__ import annotations

import gc
import random
from pathlib import Path
from typing import Callable

PRESETS: dict[str, dict] = {
    # VRAM 8〜12GB 目安。480p。
    "light": {
        "repo": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        "width": 832, "height": 480, "fps": 16, "max_frames": 81,
        "steps": 30, "guidance": 5.0,
    },
    # VRAM 16〜24GB 目安（CPU offload 前提）。720p / 24fps。
    "standard": {
        "repo": "Wan-AI/Wan2.2-TI2V-5B-Diffusers",
        "width": 1280, "height": 704, "fps": 24, "max_frames": 121,
        "steps": 40, "guidance": 5.0,
    },
}

DEFAULT_NEGATIVE = (
    "bright tones, overexposed, static, blurred details, worst quality, low quality, "
    "jpeg artifacts, ugly, deformed, extra fingers, poorly drawn hands, messy background, "
    "subtitles, watermark, text"
)


def frames_for(duration: float, fps: int, max_frames: int) -> int:
    """Wan は 4k+1 フレームが必要。シーン長に合わせつつ上限で丸める。"""
    n = max(int(round(duration * fps)), 17)
    n = ((n - 1) // 4) * 4 + 1
    return min(n, max_frames)


class WanEngine:
    def __init__(self, preset: str = "light", models_dir: str | Path | None = None,
                 offload: bool = True):
        if preset not in PRESETS:
            raise ValueError(f"unknown preset: {preset}")
        self.preset_name = preset
        self.cfg = PRESETS[preset]
        self.models_dir = str(models_dir) if models_dir else None
        self.offload = offload
        self.pipe = None

    # ---- lifecycle -------------------------------------------------
    def load(self) -> None:
        if self.pipe is not None:
            return
        import torch
        from diffusers import AutoencoderKLWan, WanPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA対応GPUが見つかりません。NVIDIA GPUとドライバを確認してください。")
        repo = self.cfg["repo"]
        kw = {"cache_dir": self.models_dir} if self.models_dir else {}
        vae = AutoencoderKLWan.from_pretrained(repo, subfolder="vae", torch_dtype=torch.float32, **kw)
        pipe = WanPipeline.from_pretrained(repo, vae=vae, torch_dtype=torch.bfloat16, **kw)
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

    # ---- generation ------------------------------------------------
    def generate(self, prompt: str, out_path: str | Path, duration: float,
                 seed: int | None = None, negative_prompt: str = DEFAULT_NEGATIVE,
                 on_step: Callable[[int, int], None] | None = None) -> Path:
        import torch
        from diffusers.utils import export_to_video

        self.load()
        c = self.cfg
        seed = random.randint(0, 2**31 - 1) if seed is None else seed
        gen = torch.Generator(device="cpu").manual_seed(seed)
        steps = c["steps"]

        def _cb(pipe, i, t, kwargs):
            if on_step:
                on_step(i + 1, steps)
            return kwargs

        frames = self.pipe(
            prompt=prompt, negative_prompt=negative_prompt,
            height=c["height"], width=c["width"],
            num_frames=frames_for(duration, c["fps"], c["max_frames"]),
            guidance_scale=c["guidance"], num_inference_steps=steps,
            generator=gen, callback_on_step_end=_cb,
        ).frames[0]
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        export_to_video(frames, str(out_path), fps=c["fps"])
        return out_path
