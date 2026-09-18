// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using System;
    using System.Collections.Generic;
    using System.Text.Json;
    using System.Text.Json.Serialization;

    /// <summary>
    /// 設定（更新可能）
    /// </summary>
    internal class AppSettings
    {
        // JSON にはこの Dictionary の中身だけを出力する。

        /// <summary>
        /// 値を保持するディクショナリを取得する。
        /// </summary>
        [JsonInclude]
        [JsonPropertyName("Values")]
        public Dictionary<string, JsonElement> Raw { get; private set; } = new Dictionary<string, JsonElement>();

        /// <summary>
        /// 値を取得する。
        /// </summary>
        /// <typeparam name="T">値の型</typeparam>
        /// <param name="key">キー名</param>
        /// <param name="value">値</param>
        /// <returns>成功時 true、エラー時 false</returns>
        public bool GetValue<T>(string key, out T value)
        {
            value = default;

            if (!this.Raw.TryGetValue(key, out var element))
            {
                return false;
            }

            try
            {
                value = element.Deserialize<T>();
                return value != null || !typeof(T).IsValueType;
            }
            catch (Exception e) when (e is JsonException || e is NotSupportedException)
            {
                return false;
            }
        }

        /// <summary>
        /// 値を設定する。
        /// </summary>
        /// <typeparam name="T">値の型</typeparam>
        /// <param name="key">キー名</param>
        /// <param name="value">値</param>
        public void SetValue<T>(string key, T value)
        {
            // オブジェクトから JsonElement へ変換して格納する。
            var element = JsonSerializer.SerializeToElement(value);

            if (this.Raw.TryGetValue(key, out var old) && old.GetRawText() == element.GetRawText())
            {
                return; // 変更なし
            }

            this.Raw[key] = element;
        }
    }
}
