# DreamMV

**Generate. Sleep. Wake up to your music video.**

DreamMV is an experimental local desktop application that turns an audio track into a music video. It analyzes the song, plans scenes, generates anime illustrations, adds camera motion, and combines the clips with the original audio.

DreamMV は、音楽からミュージックビデオを生成するためのローカルデスクトップアプリです。曲を解析してシーンを計画し、アニメイラストを生成してカメラ移動を加え、元の音声と組み合わせます。

> **Status / 状態: Experimental / 実験的なリリース**
>
> Processing is designed to run locally. Model downloads require an internet connection. Results and performance depend on your hardware and settings.
>
> 処理はローカル環境で実行する設計です。モデルのダウンロードにはインターネット接続が必要です。生成速度や結果はハードウェアと設定によって変わります。

## Features / 主な機能

- Load audio files: MP3, WAV, FLAC, OGG, and M4A.
- Analyze audio duration.
- Optionally transcribe lyrics with Whisper when available.
- Plan scenes using song length, lyrics, and theme configuration.
- Save project information, job state, and scene queue.
- Track scene progress and retry failed scenes.
- Generate anime illustrations with Animagine XL 4.0.
- Add slow pan/zoom camera motion to scene clips.
- Combine scene clips with the original audio into `output/music_video.mp4`.

日本語:

- MP3、WAV、FLAC、OGG、M4A の読み込み。
- 曲の長さの解析。
- 利用可能な場合の Whisper による歌詞の文字起こし。
- 曲の長さ、歌詞、テーマ設定に基づくシーン計画。
- プロジェクト情報、ジョブ状態、シーンキューの保存。
- シーンの進行状況確認と失敗シーンの再試行。
- Animagine XL 4.0 によるアニメイラスト生成。
- パン・ズームによるカメラ移動の追加。
- シーンクリップと元の音声を結合した MP4 の出力。

## Image generation / 画像生成

DreamMV currently uses **Animagine XL 4.0**, an SDXL-based image-generation model.

- One still illustration is generated for each scene.
- Camera motion is added to create video clips.
- The clips are combined with the original song.
- Characters do not animate like they would in a dedicated text-to-video model.
- Model files require several gigabytes of disk space.
- On GPUs with 8 GB of VRAM, memory-saving options may reduce performance.

DreamMV の現在の画像生成エンジンは **Animagine XL 4.0** です。各シーンに静止画を生成し、カメラ移動を加えて動画クリップを作成します。専用の動画生成モデルのようにキャラクターそのものが連続的に動く方式ではありません。

歌詞は現在、テーマ検出やシーン名の作成に利用されますが、画像プロンプトへの自動挿入には制限があります。

## Requirements / 動作要件

- Windows
- NVIDIA GPU and a compatible driver
- Internet connection for initial setup and model downloads
- Python environment configured by the installer

Windows と NVIDIA GPU、および対応するドライバーが必要です。初回セットアップとモデルのダウンロードにはインターネット接続が必要です。

## Installation / インストール

Run PowerShell from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File installer\install.ps1
```

リポジトリのルートフォルダーで上記のコマンドを実行してください。

To download or switch to the anime model later, if needed:

```powershell
.venv\Scripts\python.exe installer\download_model.py anime
```

## Run / 起動

Use `run.bat`, or run:

```powershell
.venv\Scripts\python.exe DreamMV.py
```

Typical workflow:

1. Open an audio file.
2. Select **Generate** to create the project and scene queue.
3. Use **AnimagineでMV生成** to process the queue.
4. Open `output/music_video.mp4` in the project folder.

基本的な使い方:

1. 音声ファイルを開く。
2. **Generate** でプロジェクトとシーンキューを作成する。
3. **AnimagineでMV生成** でキューを処理する。
4. プロジェクト内の `output/music_video.mp4` を再生する。

**Important / 注意:** Selecting Generate again rebuilds the scene queue and resets its progress. To resume an existing project, reopen it and use the rendering action.

Generate を再度実行するとシーンキューが作り直され、進行状況がリセットされます。既存プロジェクトの続きから生成する場合は、プロジェクトを開き直してレンダリング操作を使用してください。

## Project output / 出力構成

```text
Song.dreammv/
├── song.mp3
├── project.json
├── output/
│   ├── queue.json
│   ├── job.json
│   └── music_video.mp4
└── render/
    ├── clips/
    ├── normalized/
    └── render.log
```

If the application crashes, check `crash.log` in the repository root when available.

アプリがクラッシュした場合は、リポジトリのルートに `crash.log` が作成されていれば確認してください。

## Tests / テスト

Run the test suite from the repository root:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Known limitations / 既知の制限

- Lyrics are not yet automatically inserted into image prompts.
- Plain-text lyrics without timestamps are not distributed precisely across the song.
- Image generation produces still illustrations with camera motion, not full character animation.
- Generation speed and memory use depend on hardware and settings.

- 歌詞はまだ画像プロンプトに自動挿入されません。
- タイムスタンプのない歌詞は曲中に正確に割り当てられません。
- 生成されるのはカメラ移動を加えた静止画ベースの動画であり、キャラクター自体の完全なアニメーションではありません。
- 生成速度とメモリ使用量はハードウェアや設定によって異なります。

## License / ライセンス

DreamMV source code is released under the MIT License. See `LICENSE`.

DreamMV のソースコードは MIT License で公開されています。`LICENSE` を確認してください。

Model weights have separate licenses. Check the applicable model license before redistribution or commercial use.
