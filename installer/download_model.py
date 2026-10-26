"""Download Animagine XL 4.0 weights for DreamMV.

Usage: .venv/Scripts/python.exe installer/download_model.py
"""
import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
SETTINGS = APP_DIR / "anime_settings.json"
REPO_ID = "cagliostrolab/animagine-xl-4.0"


def main() -> None:
    settings = {}
    if SETTINGS.exists():
        try:
            settings = json.loads(SETTINGS.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            settings = {}
    # Backward compatibility: preserve the existing model cache directory.
    if not settings.get("models_dir"):
        old_settings = APP_DIR / "wan_settings.json"
        if old_settings.exists():
            try:
                settings["models_dir"] = json.loads(old_settings.read_text(encoding="utf-8-sig")).get("models_dir")
            except (OSError, json.JSONDecodeError):
                pass
    models_dir = Path(settings.get("models_dir") or APP_DIR / "models")
    models_dir.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import snapshot_download

    print(f"Downloading {REPO_ID} ... this may take a while")
    snapshot_download(
        REPO_ID,
        cache_dir=str(models_dir),
        allow_patterns=[
            "model_index.json", "scheduler/*", "text_encoder/*", "text_encoder_2/*",
            "tokenizer/*", "tokenizer_2/*", "unet/*", "vae/*",
        ],
    )
    settings.update(engine="animagine-xl-4.0", models_dir=str(models_dir))
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Done. anime_settings.json saved. Model cache: {models_dir}")


if __name__ == "__main__":
    main()
