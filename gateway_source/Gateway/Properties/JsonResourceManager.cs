// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Properties
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel;
    using System.IO;
    using System.Reflection;
    using System.Text.Json;

    // 補足事項
    //   1) 動作イメージ
    //        - 実行時: resources.json の値を表示
    //        - デザイン時（読み込み成功）: 実際の文字列がデザイナに表示
    //        - デザイン時（キー未定義／ファイル未発見）: #Key名 のように表示されレイアウト確認可能
    //        - 例外発生時: レイアウトが壊れず、識別可能な文字列を返す
    //   2) resource.json のプロパティについて
    //        - ビルドアクション: None（またはコンテンツ）
    //        - 出力ディレクトリにコピー: 「新しい場合はコピーする」
    //      とする。これにより出力ディレクトリにコピーされ、実行時もデザイン時（アセンブリ位置探索）も検出可能となる。但し、
    //        - 探索階層数（6階層）は必要に応じて調整
    //        - ソリューション構成によっては、resources.json をプロジェクトルートに置きつつ「出力にコピー」しておくのが最もトラブルが少ない構成
    //      に留意する。

    /// <summary>
    /// *.json 形式ファイルから起動時に読み込んだ文字列を利用可能とするリソースマネージャ（デザイナ対応）を提供する。
    /// デザイン時は EXE ディレクトリが取得できないことや resources.json が存在しないケースが多いため、複数の場所を探索する仕組みを導入する。
    /// </summary>
    internal class JsonResourceManager : INotifyPropertyChanged
    {
        private const string FileName = "resources.json";
        private const int MaxDirectoryDepth = 6;
        private static readonly Lazy<JsonResourceManager> LazyInstance = new Lazy<JsonResourceManager>(() => new JsonResourceManager());
        private Dictionary<string, string> resources = new Dictionary<string, string>(StringComparer.Ordinal);

        private JsonResourceManager()
        {
            this.Load();
        }

        /// <inheritdoc/>
        public event PropertyChangedEventHandler PropertyChanged = null;

        /// <summary>
        /// Singleton インスタンスを取得する。
        /// </summary>
        public static JsonResourceManager Instance => LazyInstance.Value;

        /// <summary>
        /// リソースを取得する。
        /// </summary>
        /// <param name="key">リソースキー</param>
        /// <returns>リソース値</returns>
        public string this[string key] => this.resources.TryGetValue(key, out var v) ? v : $"[{key}]";

        /// <summary>
        /// リソースを取得する。
        /// </summary>
        /// <param name="key">リソースキー</param>
        /// <returns>リソース値</returns>
        public string Get(string key) => this[key];

        /// <summary>
        /// *.json ファイルを読み込む。
        /// </summary>
        public void Load()
        {
            try
            {
                var filePath = FindResourceFile();
                if (filePath == null || !File.Exists(filePath))
                {
                    return;
                }

                var json = File.ReadAllText(filePath);
                var options = new JsonSerializerOptions
                {
                    ReadCommentHandling = JsonCommentHandling.Skip,
                    AllowTrailingCommas = true,
                };
                this.resources = JsonSerializer.Deserialize<Dictionary<string, string>>(json, options) ?? new Dictionary<string, string>(StringComparer.Ordinal);
            }
            catch
            {
                // 必要に応じてログ
            }

            this.PropertyChanged?.Invoke(this, new PropertyChangedEventArgs("Item[]"));
        }

        /// <summary>
        /// resources.json を複数箇所から探索。
        /// 実行時: EXE と同じディレクトリ
        /// デザイン時: アセンブリ位置から上位ディレクトリを遡ってプロジェクト直下を探索
        /// </summary>
        private static string FindResourceFile()
        {
            // (1) 実行時: EXE と同じディレクトリ
            //     補足: デザイナのプロセス（XDesProc.exe 等）は EXE と別プロセスのため GetEntryAssembly() が null になることがある。
            try
            {
                var entry = Assembly.GetEntryAssembly();
                if (entry != null)
                {
                    var dirPath = Path.GetDirectoryName(entry.Location);
                    var filePath = Path.Combine(dirPath, FileName);
                    if (File.Exists(filePath))
                    {
                        return filePath;
                    }
                }
            }
            catch
            {
            }

            // (2) 現在のアセンブリの場所（デザイナ時は Visual Studio 配下になる場合あり）
            try
            {
                var assembly = Assembly.GetExecutingAssembly();
                var dirPath = Path.GetDirectoryName(assembly.Location);
                var filePath = Path.Combine(dirPath, FileName);
                if (File.Exists(filePath))
                {
                    return filePath;
                }

                // (3) 上位ディレクトリを最大 6 階層まで遡る（bin\Debug 等からプロジェクトルートへ）。
                var current = new DirectoryInfo(dirPath);
                for (var depth = 0; depth < MaxDirectoryDepth && current != null; depth++)
                {
                    var candidate = Path.Combine(current.FullName, FileName);
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }

                    current = current.Parent;
                }
            }
            catch
            {
            }

            // (4) AppDomain のベースディレクトリ
            try
            {
                var filePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, FileName);
                if (File.Exists(filePath))
                {
                    return filePath;
                }
            }
            catch
            {
            }

            return null;
        }
    }
}
