# JIN2_code

装置操作アプリの開発版・展示用ユーザー版と、メーカー配布物をまとめた作業フォルダーです。

## フォルダー案内

| パス | 用途・入口 |
| --- | --- |
| `test2/` | 現在の開発対象。起動・仕様・検証手順は [開発版README](test2/README.md) を参照。 |
| `demo/` | 展示用ユーザー版。起動・表示・検証手順は [展示版README](demo/README.md) を参照。 |
| `SGMO2_original/` | メーカー配布物・原本。両アプリがGatewayを参照するため、名前と配置を維持。 |
| `test2/gateway_source/` | 開発版のGatewayソース。Gateway側を変更する場合の対象。 |
| `StartJIN.bat` / `JINLauncher.ps1` | ユーザー版・開発版を選ぶ起動パネル。 |
| `AGENTS.md` | 開発作業の方針。 |

通常の機能修正は `test2/` で行います。`demo/` は独立したアプリなので、開発版の変更が自動反映されるわけではありません。

## ローカルデータの扱い

- 各アプリの `recipe/`・`setting parameter/` はレシピや装置設定の置き場です。入力ファイルを一括でGit除外しません。
- `recipe/last_used_recipe.json` と `.last_settings_path` は前回の使用状態を保存するローカルファイルとしてGit除外します。ファイル自体は保持します。
- 各アプリの `data/`・`reports/`・`logs/` は生成データの置き場です。既存のGit除外設定を維持し、計測結果は保持します。
- `.uv-cache/`・`.venv/`・`__pycache__/`、メーカーGatewayの実行ログ、起動パネルの `launcher-preview.png` はGit管理対象外です。
- `.backup_before_pull_*/` はローカルの復旧用バックアップとして保持し、Git管理対象外にします。

Git除外設定は未追跡ファイルに適用されます。すでにGit管理されているファイルは引き続き管理されます。

## JIN SAMURAI 起動パネル

**`StartJIN.bat` をダブルクリック**すると、侍の案内付き選択パネルが開きます。

- **ユーザー版**：`demo/main.py` を起動します。
- **開発版**：`test2/main.py` を起動します。

パネルは Windows PowerShell / WPF で動作し、追加ライブラリは不要です。
各アプリの `.venv` を優先します。専用環境がない場合は、ユーザーの標準インストール先と PATH から、必要なライブラリを利用できる Python を探して起動します。利用可能な環境がない場合はセットアップ手順を案内します。

既存コード・起動バッチは変更していません。検出した Python と各フォルダの作業ディレクトリで、通常の接続モードを起動します。起動だけで装置には接続しません。シミュレーションは従来どおり各フォルダの `StartDemo.bat` を使用してください。

起動中は選択ボタンを無効にし、アプリ終了後に再選択できます。パネルを閉じても起動したアプリは終了しません。エラー終了時は一時フォルダの詳細ログの場所を案内します。

画面のみの確認：`powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File .\JINLauncher.ps1 -Preview`（`launcher-preview.png` を生成。アプリ・装置の起動なし）。
