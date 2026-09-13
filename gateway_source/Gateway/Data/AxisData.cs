// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using System;
    using System.Collections.ObjectModel;

    /// <summary>
    /// 描画グラフの軸情報
    /// </summary>
    /// <typeparam name="T">値の型</typeparam>
    internal class AxisData<T>
        where T : struct, IConvertible
    {
        private static readonly ReadOnlyCollection<AxisData<T>> EmptyCollection = new ReadOnlyCollection<AxisData<T>>(Array.Empty<AxisData<T>>());
        private readonly Func<ReadOnlyCollection<AxisData<T>>> getAutoTargets = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="AxisData{T}"/> class.
        /// </summary>
        /// <param name="min">始点</param>
        /// <param name="max">終点</param>
        /// <param name="minLabel">始点ラベルテキスト</param>
        /// <param name="midLabel">中点ラベルテキスト</param>
        /// <param name="maxLabel">終点ラベルテキスト</param>
        /// <param name="displayName">表示名</param>
        /// <remarks>通常用</remarks>
        public AxisData(T min, T max, string minLabel, string midLabel, string maxLabel, string displayName)
        {
            this.Auto = false;
            this.Min = min;
            this.Max = max;
            this.NormalizationFactor = 1.0 / (max.ToDouble(null) - min.ToDouble(null));
            this.MinLabel = minLabel;
            this.MidLabel = midLabel;
            this.MaxLabel = maxLabel;
            this.DisplayName = displayName;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="AxisData{T}"/> class.
        /// </summary>
        /// <param name="getAutoTargets">選択可能な軸情報の一覧を取得する delegate</param>
        /// <remarks>自動計算指定用</remarks>
        public AxisData(Func<ReadOnlyCollection<AxisData<T>>> getAutoTargets)
        {
            this.getAutoTargets = getAutoTargets;
            this.Auto = true;
            this.Min = default;
            this.Max = default;
            this.NormalizationFactor = default;
            this.MinLabel = string.Empty;
            this.MidLabel = string.Empty;
            this.MaxLabel = string.Empty;
            this.DisplayName = "Auto";
        }

        /// <summary>
        /// 自動計算指定用か否かを取得する。
        /// </summary>
        public bool Auto { get; }

        /// <summary>
        /// 始点
        /// </summary>
        public T Min { get; }

        /// <summary>
        /// 終点
        /// </summary>
        public T Max { get; }

        /// <summary>
        /// 正規化係数
        /// </summary>
        public double NormalizationFactor { get; }

        /// <summary>
        /// 始点ラベルテキスト
        /// </summary>
        public string MinLabel { get; }

        /// <summary>
        /// 中点ラベルテキスト
        /// </summary>
        public string MidLabel { get; }

        /// <summary>
        /// 終点ラベルテキスト
        /// </summary>
        public string MaxLabel { get; }

        /// <summary>
        /// 表示名
        /// </summary>
        public string DisplayName { get; }

        /// <summary>
        /// 自動計算時に選択可能な軸情報の一覧
        /// </summary>
        public ReadOnlyCollection<AxisData<T>> AutoTargets => this.getAutoTargets?.Invoke() ?? EmptyCollection;
    }
}
