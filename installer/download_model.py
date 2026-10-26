"""Download model weights for a DreamMV preset and record it in wan_settings.json.

Usage:  .venv/Scripts/python.exe installer/download_model.py [light|standard|anime]
"""
import json
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS = APP_DIR / "wan_settings.json"

REPOS = {
    "light": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
    "standard": "Wan-AI/Wan2.2-TI2V-5B-Diffusers",
    "anime": "cagliostrolab/animagine-xl-4.0",
}
# Animagine のリポジトリには単一ファイル版(約7GB x2)も入っているので、diffusers用のフォルダだけ取る
ANIME_PATTERNS = [
    "model_index.json", "scheduler/*", "text_encoder/*", "text_encoder_2/*",
    "tokenizer/*", "tokenizer_2/*", "unet/*", "vae/*",
]


def main() -> None:
    preset = sys.argv[1] if len(sys.argv) > 1 else "light"
    if preset not in REPOS:
        sys.exit(f"unknown preset: {preset} (choose from {', '.join(REPOS)})")

    settings = {}
    if SETTINGS.exists():
        try:
            settings = json.loads(SETTINGS.read_text("utf-8-sig"))
        except Exception:
            settings = {}
    models_dir = settings.get("models_dir") or str(APP_DIR / "models")

    from huggingface_hub import snapshot_download

    kw = {"allow_patterns": ANIME_PATTERNS} if preset == "anime" else {}
    print(f"Downloading {REPOS[preset]} ... this takes a while")
    snapshot_download(REPOS[preset], cache_dir=models_dir, **kw)

    settings.update(preset=preset, models_dir=models_dir)
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done. wan_settings.json now uses preset '{preset}'.")


if __name__ == "__main__":
    main()