# DreamMV Theme Expansion Pack

新規テーマJSON 48 件の追加用パックです。既存ファイルを上書きしないでください。

## 追加手順
1. ZIPを展開する。
2. JSONをDreamMVの `config/themes/` にコピーする。
3. 既存テーマ名との重複がないか確認する。
4. `python -m unittest discover -s tests -v` を実行する。

現在共有されているテーマ構造（name / keywords / stages / emotion_keywords / emotion_styles / camera_styles / color_palette / locations）に合わせています。追加前にファイル名の重複を確認し、実際の歌詞でテーマ判定の偏りや生成品質をテストしてください。
