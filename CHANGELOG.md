# Changelog / 変更履歴

All notable changes to DreamMV are documented in this file.
DreamMV の主な変更履歴を記録しています。

## [1.1.0] - 2026-10-29

### Added / 追加

- Added narration illustration support for creating visual scenes to accompany narrated content.
- 朗読音声に合わせた挿絵を生成する「朗読挿絵」機能に対応。
- Added a dedicated narration workflow for managing narration audio and its associated illustrations.
- 朗読音声と対応する挿絵を管理する、朗読専用のワークフローを追加。
- Added `sd_embed` installation to support long-prompt embedding for Animagine XL 4.0.
- Animagine XL 4.0 の長文プロンプト処理に対応するため、`sd_embed` のインストール処理を追加。
- Added an import verification step to detect missing `sd_embed` dependencies during installation.
- インストール時に `sd_embed` の読み込みを検証し、依存関係の不足を検出できるように改善。

### Fixed / 修正

- Fixed installer shortcuts to launch `DreamMV.py` instead of the missing `main.py`.
- インストーラーが作成するショートカットの起動先を、存在しない `main.py` から `DreamMV.py` に修正。
- Synchronized the project version and installer version to `1.1.0`.
- プロジェクトとインストーラーのバージョン表記を `1.1.0` に統一。

### Notes / 注意事項

- Existing CUDA 12.8 PyTorch installation and Animagine XL 4.0 model setup procedures are retained.
- 既存の CUDA 12.8 対応 PyTorch の導入処理と Animagine XL 4.0 のモデル導入処理は維持。
- Long-prompt generation and narration illustration workflows should be tested in the installed environment before release.
- リリース前に、インストール後の環境で長文プロンプトによる画像生成と朗読挿絵のワークフローを検証する必要があります。

---

## [1.0.2] - 2026-10-29

### Changed / 変更

- Expanded the visual theme library to 70 themes.
- ビジュアルテーマのライブラリを70種類に拡張。
- Improved scene-generation prompts based on theme data.
- テーマデータに基づくシーン生成プロンプトを改善。
- Enhanced theme-specific camera, color palette, and setting variations.
- テーマごとのカメラワーク、カラーパレット、舞台設定のバリエーションを強化。

### Tests / テスト

- The previous release notes reported that all 43 tests passed.
- 以前のリリース記録では、43件のテストがすべて成功したと報告されています。
- The previous release notes reported successful operation in a real video-generation test.
- 以前のリリース記録では、実際の動画生成テストで正常動作を確認したと報告されています。

---

## [1.0.1] - 2026-10-28

### Added / 追加

- Added per-scene emotion detection based on lyric keywords.
- 歌詞のキーワードに基づき、シーンごとの感情を判定する機能を追加。
- Added camera, color palette, and setting variations based on theme settings.
- テーマ設定に基づくカメラワーク、色調、舞台設定のバリエーションを追加。

---

## Earlier Versions / 以前のバージョン

For earlier development history, refer to the project's Git history and release records.
それ以前の開発履歴については、Git のコミット履歴およびリリース記録を参照してください。
