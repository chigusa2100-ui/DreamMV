
"""Lightweight anime engine: Animagine XL (SDXL) still image + camera-move clip.

WanEngine と同じ generate() インターフェース。
長文プロンプトは sd_embed で埋め込みに変換し、FFmpeg でカメラワーク付き
MP4 にする（キャラクター自体を動画生成するエンジンではない）。
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
    """静止画を、ゆっくりしたカメラワーク付きの MP4 にする。"""
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
        raise ValueError(f"Unknown camera motion: {motion}")

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

    def load(self) -> None:
        if self.pipe is not None:
            return

        import torch
        from diffusers import StableDiffusionXLPipeline

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA対応GPUが見つかりません。NVIDIA GPUとドライバを確認してください。"
            )

        kw = {"cache_dir": self.models_dir} if self.models_dir else {}

        pipe = StableDiffusionXLPipeline.from_pretrained(
            str(self.cfg["repo"]),
            torch_dtype=torch.float16,
            use_safetensors=True,
            add_watermarker=False,
            **kw,
        )

        # 8 GB VRAM 環境向けのメモリ対策
        if hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()

        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()

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
        from sd_embed.embedding_funcs import get_weighted_text_embeddings_sdxl

        self.load()
        c = self.cfg

        seed = random.randint(0, 2**31 - 1) if seed is None else seed
        generator = torch.Generator(device="cpu").manual_seed(seed)
        steps = int(c["steps"])

        def _cb(pipe, i, t, kwargs):
            if on_step:
                on_step(i + 1, steps)
            return kwargs

        # 品質タグも含めた完全なプロンプトを長文埋め込みに変換する。
        full_prompt = f"{prompt}, {QUALITY_TAGS}"

        (
            prompt_embeds,
            negative_prompt_embeds,
            pooled_prompt_embeds,
            negative_pooled_prompt_embeds,
        ) = get_weighted_text_embeddings_sdxl(
            pipe=self.pipe,
            prompt=full_prompt,
            neg_prompt=negative_prompt,
        )

        try:
            image = self.pipe(
                prompt_embeds=prompt_embeds,
                negative_prompt_embeds=negative_prompt_embeds,
                pooled_prompt_embeds=pooled_prompt_embeds,
                negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
                width=int(c["gen_width"]),
                height=int(c["gen_height"]),
                guidance_scale=float(c["guidance"]),
                num_inference_steps=steps,
                generator=generator,
                callback_on_step_end=_cb,
            ).images[0]
        finally:
            # 長文の埋め込みテンソルを保持し続けないようにする。
            del (
                prompt_embeds,
                negative_prompt_embeds,
                pooled_prompt_embeds,
                negative_pooled_prompt_embeds,
            )
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # 16:9 に中央クロップし、ズーム時の画質低下を抑える。
        w, h = image.size
        crop_h = int(w * 9 / 16)
        top = max((h - crop_h) // 2, 0)
        image = image.crop((0, top, w, top + min(crop_h, h)))
        image = image.resize((2560, 1440), Image.LANCZOS)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # 元の静止画も保存する。
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
