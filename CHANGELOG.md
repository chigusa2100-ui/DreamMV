# Changelog

All notable changes to DreamMV are documented here.
DreamMV の主な変更履歴を記録しています。

## [1.0.2] - 2026-10-29

### 日本語

- ビジュアルテーマを70種類に拡張。
- テーマに応じたシーン生成プロンプトを改善。
- カメラ、色彩、舞台設定のテーマ別バリエーションを強化。
- テーマ関連のテスト43件すべての成功を確認。
- 実際の動画生成テストで正常動作を確認。

### English

- Expanded the visual theme library to 70 themes.
- Improved scene-generation prompts based on theme data.
- Enhanced theme-specific camera, color palette, and setting variations.
- Verified that all 43 tests passed.
- Confirmed successful operation in a real video-generation test.

## [1.0.1] - 2026-10-28

### 日本語

- 歌詞の感情キーワードに基づくシーン別の感情判定を追加。
- テーマ設定に基づくカメラ、色調、舞台設定のバリエーションを追加。

### English

- Added per-scene emotion detection based on lyric keywords.
- Added camera, color palette, and setting variations based on theme data.

## [1.0.0] - 2026-10-27

### 日本語

- ローカル環境で音楽からミュージックビデオを生成するワークフローを整備。
- 音声ファイルの読み込みと曲の長さの解析に対応。
- 曲の長さ、歌詞、テーマ設定に基づくシーン計画を追加。
- プロジェクト、ジョブ状態、シーンキューの保存に対応。
- 失敗したシーンの再試行と、進行状況の確認を改善。
- Animagine XL 4.0 による静止画生成と、カメラ移動を使った動画クリップ作成に対応。
- シーンのクリップを結合し、元の音声を含む MP4 を出力。
- インストール手順と依存関係を改善。

### English

- Established a local workflow for generating music videos from audio.
- Added audio loading and duration analysis.
- Added scene planning based on song length, lyrics, and theme settings.
- Added persistent project, job-state, and scene-queue data.
- Improved progress tracking and retries for failed scenes.
- Added still-image generation with Animagine XL 4.0 and video clips with camera motion.
- Combined scene clips and the original audio into an MP4 output.
- Improved installation and dependency handling.

## [0.2.3]

- ProtoTypeDone

## [0.1.0] - Initial prototype

- Added the PySide6 desktop GUI.
- Added audio file selection and duration analysis.
- Added basic scene planning and project JSON output.
