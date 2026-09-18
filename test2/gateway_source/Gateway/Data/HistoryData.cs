// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using System;

    /// <summary>
    /// 記録データ（1件分）
    /// </summary>
    /// <typeparam name="T">メタデータの型</typeparam>
    [System.Diagnostics.CodeAnalysis.SuppressMessage("StyleCop.CSharp.MaintainabilityRules", "SA1402:File may only contain a single type", Justification = "<保留中>")]
    internal class HistoryData<T> : HistoryData
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="HistoryData{T}"/> class.
        /// </summary>
        /// <param name="meta">メタデータ</param>
        /// <param name="message">メッセージ</param>
        public HistoryData(T meta, string message)
            : base(message)
        {
            this.Meta = meta;
        }

        /// <summary>
        /// メタデータ
        /// </summary>
        public T Meta { get; }
    }

    /// <summary>
    /// 記録データ（1件分）
    /// </summary>
    internal class HistoryData
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="HistoryData"/> class.
        /// </summary>
        /// <param name="message">メッセージ</param>
        public HistoryData(string message)
        {
            this.Time = DateTimeOffset.Now;
            this.Message = message;
        }

        /// <summary>
        /// 記録日時
        /// </summary>
        public DateTimeOffset Time { get; }

        /// <summary>
        /// メッセージ
        /// </summary>
        public string Message { get; }
    }
}
