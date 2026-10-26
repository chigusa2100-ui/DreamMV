# DreamMV

Generate. Sleep. Wake up to your music video.

DreamMV is an experimental local desktop application that turns an audio track into a music video. It analyzes the song, plans a scene-by-scene storyboard, then renders every scene on your own GPU, one after another, and finally joins the clips with the original audio.

> **Status: experimental.** Everything runs locally; nothing is uploaded. Expect rough edges.

## Features

- Select an audio file (`.mp3 .wav .flac .ogg .m4a`) and read its duration.
- Optional lyric transcription (Whisper). If it is unavailable, DreamMV continues without lyrics.
- Generate a scene plan (scene names, descriptions, prompts) from the song length, lyrics and the themes in `config/themes/`.
- Persistent per-scene queue (`output/queue.json`) with progress, failure details and **retry of failed scenes**.
- Overnight rendering with a choice of engines (see below). A failed scene does not stop the run.
- Clips are normalized to each scene's length, concatenated, and muxed with the song into `output/music_video.mp4`.

## Render engines

Choose one with the installer (or `installer/download_model.py <preset>`). The active preset is stored in `wan_settings.json`.

| Preset | Model | What you get | Rough VRAM* |
|---|---|---|---|
| `light` | Wan2.1 T2V 1.3B | 480p text-to-video clips | 8 GB+ |
| `standard` | Wan2.2 TI2V 5B | 720p / 24 fps text-to-video clips | 16 GB+ |
| `anime` | Animagine XL 4.0 (SDXL) | One anime still per scene with a slow zoom/pan (characters do not move) | 8 GB+ |

\* Rough guidelines, not benchmarked. Disk usage ranges from about 7 GB (`anime`) to tens of GB (`standard`).

Notes:

- Wan produces about 5 seconds per clip. Longer scenes are looped to fill their length.
- The `anime` preset reads prompts as tags (`1girl, night sky, ...`); it works best with tag-style prompts in your theme files, and prompts beyond roughly 77 tokens are truncated.

## Requirements

- Windows with an **NVIDIA GPU** and a recent driver (CUDA build of PyTorch)
- Internet access for the first setup (Python, PyTorch, model weights)
- Python 3.11 is installed automatically into `.venv` by the installer (via [uv](https://github.com/astral-sh/uv))

## Install

From the repository root, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1
```

You will be asked which model to download (1 = light, 2 = standard, 3 = anime). To add or switch a model later:

```powershell
.venv\Scripts\python.exe installer\download_model.py anime
```

The installer does not install a Whisper package. Lyric transcription is optional; see `src/dreammv/whisper_engine.py`.

## Run

```
run.bat
```

or

```powershell
.venv\Scripts\python.exe DreamMV.py
```

Usage: **Open MP3** → **Generate** (creates the `.dreammv` project and the scene queue) → **Render with Wan** (processes the queue) → open `output/music_video.mp4` in the project folder.

> Pressing **Generate** again rebuilds the queue and resets all scene progress. After reopening a project, use the render button to resume instead.

On first launch DreamMV creates `config.json` if it does not exist. Existing settings are not overwritten.

## Project folder

```
Song.dreammv/
├── song.mp3              copy of the audio
├── project.json          metadata, lyrics, scene plan
├── output/
│   ├── queue.json        per-scene state (queued / running / completed / failed)
│   ├── job.json
│   └── music_video.mp4   final video
└── render/
    ├── clips/            one clip per scene (plus .png stills for the anime preset)
    ├── normalized/       length-adjusted clips used for joining
    └── render.log        error details
```

If the app crashes, `crash.log` in the repository root records the cause.

## Test

```
py -m unittest discover -s tests -v
```

## Repository layout

```
DreamMV/
├── DreamMV.py
├── run.bat
├── config.json
├── wan_settings.json          active preset and model folder (machine-specific)
├── config/themes/             story themes (keywords, stages, prompts)
├── installer/
│   ├── install.ps1
│   ├── download_model.py
│   └── DreamMV.iss            Inno Setup script for DreamMV-Setup.exe
├── src/dreammv/
│   ├── audio.py
│   ├── config.py
│   ├── jobs.py
│   ├── planner.py
│   ├── project.py
│   ├── queue.py
│   ├── project_queue.py
│   ├── whisper_engine.py
│   ├── wan_engine.py
│   ├── anime_engine.py
│   └── render_worker.py
└── tests/
```

## Known limitations

- Lyrics are used for scene names and theme detection, not (yet) for image prompts, so scenes in the same story stage share the same prompt.
- Plain-text lyrics without timestamps are not spread across the song.
- Model weights are **not** included in this repository and keep their own licenses (Wan: Apache 2.0, Animagine XL 4.0: CreativeML Open RAIL++-M). Check each license before redistributing weights or using output commercially.

## License

The DreamMV source code is released under the MIT License (see `LICENSE`).
