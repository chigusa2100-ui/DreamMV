"""Download the exact LTX-2.5 model files required by DreamMV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from huggingface_hub import snapshot_download
from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

REPOSITORY = "Lightricks/LTX-2.5"

REQUIRED_FILES = [
    "diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors",
    "text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors",
    "vae/ltx-2.5-video-vae-bf16.safetensors",
    "vae/ltx-2.5-audio-vae-bf16.safetensors",
    "model_patches/ltx-2.5-duration-head-bf16.safetensors",
    "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        default=r"C:\AI\DreamMV-LTX25\models",
    )
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        name for name in REQUIRED_FILES
        if not (model_dir / name).is_file()
    ]

    if not missing:
        print("All required LTX-2.5 model files are already installed.")
        return 0

    print("Repository:", REPOSITORY)
    print("Destination:", model_dir)
    print("Files to download:")
    for name in missing:
        print("  -", name)

    print()
    print("This download is approximately 66 GB.")
    print("Your Hugging Face account must have accepted the model license.")
    print()

    try:
        snapshot_download(
            repo_id=REPOSITORY,
            local_dir=str(model_dir),
            allow_patterns=REQUIRED_FILES,
            token=True,
        )
    except GatedRepoError:
        print(
            "\nAccess denied. Open https://huggingface.co/Lightricks/LTX-2.5 "
            "and accept the model access conditions while signed in.",
            file=sys.stderr,
        )
        print(
            "Then authenticate with: hf auth login",
            file=sys.stderr,
        )
        return 2
    except HfHubHTTPError as exc:
        print(f"\nHugging Face download failed: {exc}", file=sys.stderr)
        print("Check your network connection and Hugging Face access.", file=sys.stderr)
        return 3

    missing_after = [
        name for name in REQUIRED_FILES
        if not (model_dir / name).is_file()
    ]

    if missing_after:
        print("Some required model files are still missing:", file=sys.stderr)
        for name in missing_after:
            print("  -", name, file=sys.stderr)
        return 4

    print("\nAll six LTX-2.5 model files are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
