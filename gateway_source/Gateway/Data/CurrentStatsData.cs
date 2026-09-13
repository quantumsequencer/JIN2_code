// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using Sony.Jin.Shared;

    /// <summary>
    /// 電流測定値の統計情報
    /// </summary>
    internal class CurrentStatsData
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="CurrentStatsData"/> class.
        /// </summary>
        /// <param name="values">電流測定値 Raw データ（符号付き 32 ビット整数・リトルエンディアン）</param>
        /// <param name="min">最小値</param>
        /// <param name="minPosition">最小値の位置（Values.Length により正規化）</param>
        /// <param name="max">最大値</param>
        /// <param name="maxPosition">最大値の位置（Values.Length により正規化）</param>
        /// <param name="median">中央値</param>
        /// <param name="rms">二乗平均平方根</param>
        public CurrentStatsData(ByteSpan values, int min, double minPosition, int max, double maxPosition, double median, double rms)
        {
            this.Values = values;
            this.Min = min;
            this.MinPosition = minPosition;
            this.Max = max;
            this.MaxPosition = maxPosition;
            this.Median = median;
            this.Rms = rms;
        }

        /// <summary>
        /// 電流測定値 Raw データ（符号付き 32 ビット整数・リトルエンディアン）
        /// </summary>
        public ByteSpan Values { get; }

        /// <summary>
        /// 最小値
        /// </summary>
        public int Min { get; }

        /// <summary>
        /// 最小値の位置（Values.Length により正規化）
        /// </summary>
        public double MinPosition { get; }

        /// <summary>
        /// 最大値
        /// </summary>
        public int Max { get; }

        /// <summary>
        /// 最大値の位置（Values.Length により正規化）
        /// </summary>
        public double MaxPosition { get; }

        /// <summary>
        /// 中央値
        /// </summary>
        public double Median { get; }

        /// <summary>
        /// 二乗平均平方根
        /// </summary>
        public double Rms { get; }
    }
}
