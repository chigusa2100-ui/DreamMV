# DreamMV

Generate. Sleep. Wake up to your music video.

DreamMV is an experimental local desktop application for planning a music video from an audio track.

## Current milestone

- Select an audio file and read its duration.
- Create a `.dreammv` project folder.
- Generate a scene-by-scene MV plan with scene names, descriptions, and image prompts.
- Store project metadata in `project.json` and local job status in `output/job.json`.
- Configure scene duration and audio analysis settings in `config.json`.

**Important:** the current version creates the MV plan only. It does not yet generate images or video. The image/video generation engine will be integrated in a later milestone.

## Requirements

- Python 3.10+ (use the Python version already set up for your environment)
- PySide6
- librosa
- soundfile

Install dependencies using the Python launcher:

```powershell
py -m pip install PySide6 librosa soundfile
```

## Run

From the repository root:

```powershell
py DreamMV.py
```

On first launch, DreamMV creates `config.json` if it does not exist. Existing settings are not overwritten.

## Test

```powershell
py -m unittest discover -s tests -v
```

## Project layout

```text
DreamMV/
├── DreamMV.py
├── config.json
├── src/
│   └── dreammv/
│       ├── audio.py
│       ├── config.py
│       ├── jobs.py
│       ├── planner.py
│       └── project.py
└── tests/
```
