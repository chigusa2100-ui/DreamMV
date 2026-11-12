# Changelog

All notable changes to DreamMV are documented here.
DreamMV の主な変更履歴を記録しています。

## [2.0.0] - 2026-11-12

### 日本語 / Japanese

#### 主な変更 / Added

- 次世代動画生成エンジンとしてLTX-2.5を追加。
- Animagine XL 4.0とLTX-2.5を独立した生成エンジンとして利用できる構成に拡張。
- ComfyUIを実行時依存とせず、LTX-2.5のネイティブパイプラインを直接実行するローカル推論方式を追加。
- LTX-2.5専用のPython 3.12実行環境を導入し、DreamMV本体のPython環境から分離。
- LTX-2.5のソースを固定コミットで取得し、Windows向けランタイムパッチを適用するインストール処理を追加。
- LTX-2.5のモデルファイルを必要に応じて導入できるオプションを追加。モデルのダウンロードにはHugging Faceの認証とアクセス許可が必要。
- 日本語2Dアニメ調のスタイルプロンプトをLTX-2.5の標準設定として追加。
- LTX-2.5による動画のみの生成に対応し、DreamMV側で元楽曲と動画を合成するワークフローを追加。
- LTX-2.5の生成処理を独立プロセスとして実行し、ログ記録、キャンセル、タイムアウト処理に対応。

#### 改善 / Improved

- Animagine XL 4.0とLTX-2.5で共通のシーンキューおよび動画結合ワークフローを利用できるよう改善。
- LTX-2.5の動画をFFmpegで正規化・結合し、元楽曲を含むMP4として出力する処理を追加。
- 既存のAnimagine XL 4.0による生成環境を維持しながら、新しい動画生成エンジンを追加できる構成に改善。

#### テスト / Tests

- LTX-2.5エンジン関連テスト：11 passed。
- RenderWorker関連テスト：3 passed。
- 全体テスト：63 passed。
- テーマ関連サブテスト：140 passed。
- 合計203件のテスト項目が成功。

### English

#### Added

- Added LTX-2.5 as the next-generation video generation engine.
- Expanded the engine architecture to support Animagine XL 4.0 and LTX-2.5 as independent generation engines.
- Added native local inference by directly launching the LTX-2.5 pipeline without requiring ComfyUI at runtime.
- Introduced a dedicated Python 3.12 environment for LTX-2.5, isolated from DreamMV's main Python environment.
- Added an installation workflow that checks out a pinned LTX-2.5 source commit and applies Windows runtime patches.
- Added optional installation of LTX-2.5 model files. Model downloads require Hugging Face authentication and access approval.
- Added a Japanese 2D anime-style prompt as the default visual style for LTX-2.5.
- Added video-only generation with LTX-2.5 and a workflow for combining generated video with the original song inside DreamMV.
- Run LTX-2.5 generation as an independent process with logging, cancellation, and timeout handling.

#### Improved

- Improved the shared scene queue and video assembly workflow to support both Animagine XL 4.0 and LTX-2.5.
- Added FFmpeg processing to normalize and combine LTX-2.5 clips and produce MP4 output with the original audio.
- Extended DreamMV with a new video generation engine while preserving the existing Animagine XL 4.0 environment.

#### Tests

- LTX-2.5 engine tests: 11 passed.
- RenderWorker tests: 3 passed.
- Full test suite: 63 passed.
- Theme-related subtests: 140 passed.
- All 203 test cases passed.

---
## [1.2.0] - 2026-11-05

### 日本語 / Japanese

#### 主な変更 / Added

- 歌詞の内容を解析し、シーンの演出を決定するScene Directorを追加。
- 歌詞からアクション、舞台設定、時間帯、照明、構図を自動判定。
- テーマ設定に基づくキャラクターの一貫性を強化。
- 140種類のテーマJSONにDirector設定を追加。
- 感情に応じたカメラ移動のフォールバック処理を追加。

#### 改善 / Improved

- 時刻指定のない歌詞を楽曲の長さに応じて自動配置。
- シーン境界の処理を改善し、歌詞の重複を防止。
- テーマ固有のビジュアル表現をシーン生成プロンプトに反映。

#### テスト / Tests

- pytest：52 passed。
- テーマ関連サブテスト：140 passed。
- 合計192件のテスト項目が成功。

### English

#### Added

- Added a rule-based Scene Director that interprets lyrics and determines scene direction.
- Automatically derives actions, settings, time of day, lighting, and composition from lyrics.
- Improved character consistency using theme-specific character descriptions.
- Added Director configuration to all 140 theme JSON files.
- Added emotion-aware fallback camera movement.

#### Improved

- Automatically distributes untimed lyrics across the full song duration.
- Improved scene-boundary handling to prevent duplicate lyrics.
- Incorporated theme-specific visual language into scene-generation prompts.

#### Tests

- pytest: 52 passed.
- Theme-related subtests: 140 passed.
- All 192 test cases passed.

---

## [1.1.0] - 2026-11-04

### 主な変更

- カメラ演出を画像生成プロンプトから分離。
- シーンごとのカメラスタイルとカメラ移動を独立して管理。
- カメラ移動の設定をレンダリングエンジンへ受け渡す仕組みを追加。
- 旧プロジェクトや既存キューとの互換性を維持。
- カメラ移動設定がない旧テーマでも正常に動作するよう改善。

### テスト

- ユニットテスト45件すべて成功。
- GUIの正常起動を確認。
- Animagine XL 4.0による動画生成を確認。
- カメラ演出が画像生成ではなくレンダリング時に適用されることを確認。

### English

- Separated camera direction metadata from image-generation prompts.
- Added independent per-scene camera style and motion settings.
- Forwarded camera motion settings to the rendering engine.
- Preserved backward compatibility with existing projects and queues.
- Improved compatibility with legacy themes without camera motion settings.

### Tests

- All 45 unit tests passed.
- Confirmed successful GUI startup and video generation.
- Verified camera movement is applied during rendering.

## [1.0.4]

### Fixed / 修正
- Improved handling of long prompts using Compel.
  - Compelを使用し、長いプロンプトの処理を改善。
- Added Compel 2.5.1 to project dependencies and the installer.
  - プロジェクトの依存関係とインストーラーにCompel 2.5.1を追加。

### Tests / テスト
- Verified Compel import successfully.
  - Compelのインポートを確認。
- All 8 related tests passed.
  - 関連テスト8件がすべて成功。

# [v1.0.3]

## 主な変更
- MV生成用テーマを70種類追加
- テーマライブラリを合計140種類に拡充

## テスト
- pytest：43 passed
- テーマ関連サブテスト：140 passed
- テーマJSON：140ファイルを検査し、構文エラー0件

## 今後について
モデルの追加はいったん終了し、既存モデルとテーマライブラリの活用・安定性向上を優先します。

## Key Changes
- Added 70 new themes for music video generation.
- Expanded the theme library to a total of 140 themes.

## Tests
- pytest: 43 passed
- Theme-related subtests: 140 passed
- Theme JSON files: 140 validated, with 0 syntax errors.

## Future Development
Model additions are on hold for now. Development will focus on making better use of existing models and the theme library, while improving overall stability.

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
