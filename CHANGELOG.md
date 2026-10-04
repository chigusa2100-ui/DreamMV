# Changelog

All notable changes to DreamMV will be recorded here.

[Unreleased] 2026-10-04

Fixed

generate_project() 内の重複したテストファイル作成処理を削除

ジョブ管理開始前に行われていた不要なテストファイル作成を整理

Tested

job.json の最終状態が completed になることを確認

正常終了時に error が null になることを確認

---

[Unreleased] 2026-10-03

Added

job.json の生成ジョブ状態を queued、running、completed へ更新できるようにした

生成ジョブの最終状態をDreamMVの画面に表示できるようにした

ジョブ情報にエラー内容を記録できるようにした

Fixed

テスト処理でエラーが発生した場合、ジョブ状態を failed として保存するようにした

エラー処理後に状態が completed へ上書きされる問題を修正

---

[Unreleased] 2026-10-02

Added

既存の .dreammv プロジェクトを開けるようにした

プロジェクト内の project.json を読み込めるようにした

読み込んだプロジェクト情報をDreamMV内に保持するようにした

既存プロジェクトに対してGenerateを実行できるようにした

Generate時に output/ へテストファイルを生成できるようにした

Generate時に output/job.json へ生成ジョブ情報を保存できるようにした

Fixed

既存プロジェクトでGenerateを実行した際、タイトルが song に変わる問題を修正

タイトルが song になっている場合、プロジェクトフォルダ名から復元できるようにした

---

## [Unreleased] 2026-10-01

### Added
- 既存の `.dreammv` プロジェクトを開けるようにした
- プロジェクト内の `project.json` を読み込めるようにした
- 読み込んだプロジェクト情報をDreamMV内に保持するようにした
- 既存プロジェクトに対してGenerateを実行できるようにした
- Generate時に `output/` へテストファイルを生成できるようにした

---

## [Unreleased] 2026-10-01

### Added
- 既存の `.dreammv` プロジェクトを開けるようにした
- プロジェクト内の `project.json` を読み込めるようにした
- 読み込んだプロジェクト情報をDreamMV内に保持するようにした

---

## [Unreleased] 2026-09-30

### Added
- MP3選択後にGenerateボタンを有効化
- `.dreammv`プロジェクトを自動生成
- プロジェクト内に `project.json` を作成
- 選択したMP3を `song.mp3` としてプロジェクトへ保存
- `scenes/` と `output/` ディレクトリを自動生成

---

## [0.1.2] - 2026-09-29

### Added

- GUI起動
- MP3読み込み
- 曲の長さ表示
- 初めて音楽解析に成功

---

## [0.1.1] - 2026-09-29

### Added

- DreamMV初期GUI
- プロジェクト構成作成