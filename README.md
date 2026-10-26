# DreamMV

Generate. Sleep. Wake up to your music video.

DreamMV is an experimental local desktop application that turns an audio track into a music video. It analyzes the song, plans a scene-by-scene storyboard, then uses Animagine XL 4.0 to create one anime illustration per scene, adds slow pan/zoom camera movement, and joins the clips with the original audio.

> **Status: experimental.** Everything runs locally; nothing is uploaded. Expect rough edges.

## Features

- Select an audio file (`.mp3 .wav .flac .ogg .m4a`) and read its duration.
- Optional lyric transcription (Whisper). If it is unavailable, DreamMV continues without lyrics.
- Generate a scene plan (scene names, descriptions, prompts) from the song length, lyrics and the themes in `config/themes/`.
- Persistent per-scene queue (`output/queue.json`) with progress, failure details and **retry of failed scenes**.
- Overnight Animagine XL 4.0 rendering. A failed scene does not stop the run.
- Clips are normalized to each scene's length, concatenated, and muxed with the song into `output/music_video.mp4`.

## Image generation

DreamMV uses **Animagine XL 4.0** (SDXL) as its only active generation engine.

- One anime still image is generated for each scene.
- DreamMV adds slow pan/zoom camera movement and exports each scene as MP4.
- The scene clips are joined and the original song is added.
- The character itself does **not** animate like a text-to-video model.
- The first setup downloads the model files; allow roughly several GB of free disk space.
- With an 8 GB GPU, CPU offload and memory-saving VAE options are enabled. Generation can be slow.

Theme prompts should use descriptive anime illustration tags where possible. Lyrics currently affect theme detection and scene naming, but are not yet automatically inserted into image prompts.

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

Usage: **Open MP3** → **Generate** (creates the `.dreammv` project and the scene queue) → **AnimagineでMV生成** (processes the queue) → open `output/music_video.mp4` in the project folder.

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
    ├── clips/            one clip per scene plus the source .png still
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
├── anime_settings.json         Animagine model cache directory
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
- Model weights are **not** included in this repository and keep their own licenses (Animagine XL 4.0: CreativeML Open RAIL++-M). Check each license before redistributing weights or using output commercially.

## License

The DreamMV source code is released under the MIT License (see `LICENSE`).
