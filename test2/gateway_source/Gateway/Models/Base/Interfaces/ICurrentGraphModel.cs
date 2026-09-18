// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using Reactive.Bindings;
    using Sony.Jin.Gateway.Data;

    /// <summary>
    /// CurrentGraphModel
    /// </summary>
    internal interface ICurrentGraphModel : IGraphModel<CurrentGraphSource>
    {
        /// <summary>
        /// 測定値の描画色を取得する。
        /// </summary>
        System.Drawing.Color ValueColor { get; }

        /// <summary>
        /// 中央値の描画色を取得する。
        /// </summary>
        System.Drawing.Color MedianColor { get; }

        /// <summary>
        /// 二乗平均平方根の描画色を取得する。
        /// </summary>
        System.Drawing.Color RmsColor { get; }

        /// <summary>
        /// グラフのデータ種別テキストを取得する。
        /// </summary>
        IReadOnlyReactiveProperty<string> DataTypeText { get; }
    }
}
