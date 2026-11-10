# 外出・外泊管理アプリ

精神科病棟の入院患者の外出・外泊を記録し、帰院予定を過ぎたらiPadで知らせるアプリです。

- 使う場所：https://heartcommit-design.github.io/gaishutsu/ を病棟のiPadのホーム画面に追加して使います。
- データ：iPadの中だけに保存します。外部には送りません。
- 今の版：1.9.0
- 作った人：黒田 優

## ファイル
- `index.html` アプリ本体（1ファイル）
- `sw.js` `manifest.webmanifest` `icon-*.png` ホーム画面に追加して使うための部品
- `tests/` 自動テスト（`bash tests/run_tests.sh`）
- `docs/改善メモ.md` 課題と対応の記録
- `CLAUDE.md` 開発の決まりごと

テストや画面写真のデータはすべて架空です。
