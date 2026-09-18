// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.Drawing;
    using System.Linq;
    using Sony.Jin.Shared;

    /// <summary>
    /// 電流値グラフ表示用情報
    /// </summary>
    internal class CurrentGraphSource : GraphSource
    {
        private readonly CurrentStatsCalculator statsCalculator = null;
        private readonly RingBuffer<CurrentStatsData> ringBuffer = null;
        private readonly Color valueColor = default;
        private readonly Color medianColor = default;
        private readonly Color rmsColor = default;

        /// <summary>
        /// Initializes a new instance of the <see cref="CurrentGraphSource"/> class.
        /// </summary>
        /// <param name="dataType">Host Port Frame のデータ種別</param>
        /// <param name="serialNumber">Serial Number</param>
        /// <param name="values">電流測定値 Raw データ（符号付き 32 ビット整数・リトルエンディアン）</param>
        /// <param name="valueColor">測定値描画色</param>
        /// <param name="medianColor">中央値描画色</param>
        /// <param name="rmsColor">二乗平均平方根描画色</param>
        /// <param name="ringBufferCapacity">リングバッファの最大要素数</param>
        public CurrentGraphSource(HostPortDataType dataType, uint serialNumber, ByteSpan values, Color valueColor, Color medianColor, Color rmsColor, int ringBufferCapacity)
            : this(new CurrentStatsCalculator(), new RingBuffer<CurrentStatsData>(ringBufferCapacity), dataType, valueColor, medianColor, rmsColor, serialNumber, values)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="CurrentGraphSource"/> class.
        /// </summary>
        /// <param name="source">追加元 GraphSource</param>
        /// <param name="serialNumber">Serial Number</param>
        /// <param name="values">電流測定値 Raw データ（符号付き 32 ビット整数・リトルエンディアン）</param>
        public CurrentGraphSource(CurrentGraphSource source, uint serialNumber, ByteSpan values)
            : this(source.statsCalculator, source.ringBuffer, source.DataType, source.valueColor, source.medianColor, source.rmsColor, serialNumber, values)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="CurrentGraphSource"/> class.
        /// </summary>
        /// <param name="source">コピー元 GraphSource</param>
        public CurrentGraphSource(CurrentGraphSource source)
            : base(source.LastSerialNumber)
        {
            this.statsCalculator = null;
            this.DataType = source.DataType;
            this.valueColor = source.valueColor;
            this.medianColor = source.medianColor;
            this.rmsColor = source.rmsColor;

            // 元の GraphSource を引き継いだ GraphSource での要素追加と、ここでのクローン操作を同時に行わないよう排他処理を施す。
            lock (source.ringBuffer.CollectionLock)
            {
                this.ringBuffer = new RingBuffer<CurrentStatsData>(source.ringBuffer);  // 要素を shallow copy
            }
        }

        private CurrentGraphSource(CurrentStatsCalculator statsCalculator, RingBuffer<CurrentStatsData> ringBuffer, HostPortDataType dataType, Color valueColor, Color medianColor, Color rmsColor, uint serialNumber, ByteSpan values)
            : base(serialNumber)
        {
            this.statsCalculator = statsCalculator;
            this.ringBuffer = ringBuffer;
            this.DataType = dataType;
            this.valueColor = valueColor;
            this.medianColor = medianColor;
            this.rmsColor = rmsColor;

            // 元の GraphSource の描画時の要素参照、元の GraphSource からの Snap 発生時のクローン操作、そしてここでの要素追加を同時に行わないよう排他処理を施す。
            lock (this.ringBuffer.CollectionLock)
            {
                this.ringBuffer.Add(this.statsCalculator.Calculate(values));
            }
        }

        /// <summary>
        /// Host Port Frame のデータ種別を取得する。
        /// </summary>
        public HostPortDataType DataType { get; }

        /// <inheritdoc/>
        public override int BufferCount => this.ringBuffer.Count;

        /// <inheritdoc/>
        public override bool DrawLineGraph(AxisData<int> xAxis, IReadOnlyList<AxisData<double>> yAxisCollection, Func<Color[], Action<double, double>[]> notifyGraphCount)
        {
            if (xAxis == null || yAxisCollection == null || yAxisCollection.Count < 1 || notifyGraphCount == null)
            {
                return false;
            }

            var yAxis = yAxisCollection[0];
            var addPoint = notifyGraphCount.Invoke(new Color[] { this.valueColor, this.medianColor, this.rmsColor });

            lock (this.ringBuffer.CollectionLock)
            {
                var rawValuesCount = this.ringBuffer[0].Values.Length / sizeof(int);
                GetEffectiveXRange(this.ringBuffer, xAxis, out var startX, out var endX);

                if (xAxis.Max - xAxis.Min >= 1000)
                {
                    var n = (xAxis.Max - xAxis.Min) / 1000;
                    DrawDecimatedValues(this.ringBuffer, xAxis, yAxis, addPoint[0], startX, endX, n);
                }
                else if (rawValuesCount * (xAxis.Max - xAxis.Min) > 10 * 1000)
                {
                    // プロット数を 1000 にする場合の Values の分割定数
                    //                              xAxis.Range (block count, values/block)
                    // 100kHz サンプル時 (1000 pcs): 500 (2, 500), 200 (5, 200), 100 (10, 100), 50 (20, 50), 20 (50, 20), 10 (100, 10), 5 (200, 5),   2 (500, 2), 1 (1000, 1)
                    // 50kHz サンプル時  (500 pcs):  500 (2, 250), 200 (5, 100), 100 (10, 50),  50 (20, 25), 20 (50, 10), 10 (100, 5),  5 (200, 2.5), 2 (500, 1), 1 (1000, -)
                    // 10kHz サンプル時  (100 pcs):  500 (2, 50),  200 (5, 20) , 100 (10, 10),  50 (20, 5),  20 (50, 2),  10 (100, 1),  5 (200, -),   2 (500, -), 1 (1000, -)
                    //  (1) 分割数（ブロック数）   = 1000 / (xAxis.Max - xAxis.Min)
                    //  (2) ブロック毎のサンプル数 = rawValuesCount * (xAxis.Max - xAxis.Min) / 1000
                    //      ※ (2) は 1 以下であれば折れ線表現に変える必要があるが、1以上でも値が小さい程プロット間に窓が開く可能性が高くなることと、
                    //         50kHz サンプル時に割り切れない事例が存在することから、描画が重くなり過ぎない上限として 10 以下を折れ線表現とする。
                    var blockCount = 1000 / (xAxis.Max - xAxis.Min);  // 1つの CurrentStatsData.Values から blockCount 個の描画点を再抽出
                    DrawRedecimatedValues(this.ringBuffer, xAxis, yAxis, addPoint[0], startX, endX, blockCount);
                }
                else
                {
                    DrawImmediateValues(this.ringBuffer, xAxis, yAxis, addPoint[0], startX, endX);
                }

                if (xAxis.Max - xAxis.Min > 1000)
                {
                    var n = (xAxis.Max - xAxis.Min) / 1000;
                    DrawDecimatedData(this.ringBuffer, xAxis, yAxis, addPoint[1], x => x.Median, startX, endX, n);
                    DrawDecimatedData(this.ringBuffer, xAxis, yAxis, addPoint[2], x => x.Rms,    startX, endX, n);
                }
                else
                {
                    DrawRawData(this.ringBuffer, xAxis, yAxis, addPoint[1], x => x.Median, startX, endX);
                    DrawRawData(this.ringBuffer, xAxis, yAxis, addPoint[2], x => x.Rms,    startX, endX);
                }

                return true;
            }
        }

        /// <summary>
        /// Host Port フレームデータ列を取得する。
        /// </summary>
        /// <returns>Host Port フレームデータ列</returns>
        public ByteSpan[] GetHostFrames()
        {
            lock (this.ringBuffer.CollectionLock)
            {
                // オフセット処理のないオリジナルの Host Port フレームデータに直して返す。
                return this.ringBuffer.Select(x => new ByteSpan(x.Values.Array)).ToArray();
            }
        }

        private static void DrawDecimatedValues(RingBuffer<CurrentStatsData> ringBuffer, AxisData<int> xAxis, AxisData<double> yAxis, Action<double, double> addPoint, int startX, int endX, int n)
        {
            // 描画範囲で 10s（1s / DIV）以上では 1000 プロット以上になるため、Min-Max Decimation ロジックにより、最大値・最小値の2点で代表させ、間引いて描画する。
            var minFinder = new IntMinFinder();
            var maxFinder = new IntMaxFinder();

            for (var x = startX; x <= endX; x++)
            {
                var stats = GetData(ringBuffer, x);
                minFinder.Evaluate(stats.Min, x, stats.MinPosition);
                maxFinder.Evaluate(stats.Max, x, stats.MaxPosition);

                if ((x - startX + 1) % n == 0)
                {
                    var nxmin = xAxis.NormalizationFactor * (minFinder.Position + minFinder.Index - xAxis.Min);
                    var nxmax = xAxis.NormalizationFactor * (maxFinder.Position + maxFinder.Index - xAxis.Min);
                    var nymin = yAxis.NormalizationFactor * (minFinder.Value - yAxis.Min);
                    var nymax = yAxis.NormalizationFactor * (maxFinder.Value - yAxis.Min);
                    AddDecimatedPoints(addPoint, nxmin, nymin, nxmax, nymax);

                    minFinder.Reset();
                    maxFinder.Reset();
                }
            }
        }

        private static void DrawRedecimatedValues(RingBuffer<CurrentStatsData> ringBuffer, AxisData<int> xAxis, AxisData<double> yAxis, Action<double, double> addPoint, int startX, int endX, int blockCount)
        {
            var minFinder = new IntMinFinder();
            var maxFinder = new IntMaxFinder();

            var rawValuesCount = ringBuffer[0].Values.Length / sizeof(int);
            var samplesCountInBlock = rawValuesCount / blockCount;

            for (var x = startX; x <= endX; x++)
            {
                var baseX = x - xAxis.Min;
                var stats = GetData(ringBuffer, x);
                var array = stats.Values.Array;
                var startIndex = stats.Values.Offset;
                for (var blockIndex = 0; blockIndex < blockCount; blockIndex++)
                {
                    // Min-Max Decimation ロジックにより、最大値・最小値の2点で代表させて描画点を間引く。
                    minFinder.Reset();
                    maxFinder.Reset();
                    for (var index = 0; index < samplesCountInBlock; index++)
                    {
                        var v = BitConverter.ToInt32(array, startIndex + (index * sizeof(int)));
                        minFinder.Evaluate(v, index);
                        maxFinder.Evaluate(v, index);
                    }

                    var nxmin = xAxis.NormalizationFactor * (((((double)minFinder.Index / samplesCountInBlock) + blockIndex) / blockCount) + baseX);
                    var nxmax = xAxis.NormalizationFactor * (((((double)maxFinder.Index / samplesCountInBlock) + blockIndex) / blockCount) + baseX);
                    var nymin = yAxis.NormalizationFactor * (minFinder.Value - yAxis.Min);
                    var nymax = yAxis.NormalizationFactor * (maxFinder.Value - yAxis.Min);
                    AddDecimatedPoints(addPoint, nxmin, nymin, nxmax, nymax);

                    startIndex += samplesCountInBlock * sizeof(int);
                }
            }
        }

        private static void DrawImmediateValues(RingBuffer<CurrentStatsData> ringBuffer, AxisData<int> xAxis, AxisData<double> yAxis, Action<double, double> addPoint, int startX, int endX)
        {
            // 生データ総数でも 1000 個以下の場合、すべて折れ線で描画
            for (var x = startX; x <= endX; x++)
            {
                var stats = GetData(ringBuffer, x);
                var array = stats.Values.Array;
                var offset = stats.Values.Offset;
                var length = stats.Values.Length;
                for (var valuesIndex = 0; valuesIndex < length; valuesIndex += sizeof(int))
                {
                    var v = BitConverter.ToInt32(array, offset + valuesIndex);
                    var nx = xAxis.NormalizationFactor * (((double)valuesIndex / length) + x - xAxis.Min);
                    var ny = yAxis.NormalizationFactor * (v - yAxis.Min);
                    addPoint.Invoke(nx, ny);
                }
            }
        }

        /// <inheritdoc/>
        public override bool GetAutoYAxis(AxisData<int> xAxis, AxisData<double> yAutoAxis, int graphIndex, out AxisData<double> axis)
        {
            lock (this.ringBuffer.CollectionLock)
            {
                switch (graphIndex)
                {
                    case 0:  axis = GetCurrentAxisData(this.ringBuffer, xAxis, yAutoAxis.AutoTargets); return true;
                    default: axis = default; return false;
                }
            }
        }

        private static AxisData<double> GetCurrentAxisData(RingBuffer<CurrentStatsData> ringBuffer, AxisData<int> xAxis, ReadOnlyCollection<AxisData<double>> yAxisCollection)
        {
            GetMax(ringBuffer, xAxis, x => x.Max, out var max);
            return yAxisCollection.FirstOrDefault(x => !x.Auto && x.Max > max) ?? yAxisCollection[yAxisCollection.Count - 1];
        }

        private class CurrentStatsCalculator
        {
            private readonly IntMinFinder minFinder = new IntMinFinder();
            private readonly IntMaxFinder maxFinder = new IntMaxFinder();
            private int[] buffer;

            public CurrentStatsData Calculate(ByteSpan values)
            {
                if (values.Array == null)
                {
                    throw new ArgumentException(null, nameof(values));
                }

                if (values.Length == 0)
                {
                    // DataType = HostPortDataType.BeaconNoCurrent の場合
                    return new CurrentStatsData(values, 0, 0.0, 0, 0.0, 0.0, 0.0);
                }

                // ByteSpan.Length はバイト数。uint 要素数は 1/4。
                var n = values.Length / sizeof(int);

                // ソート用バッファを使い回す。
                if (this.buffer == null || this.buffer.Length != n)
                {
                    this.buffer = new int[n];
                }

                var array = values.Array;
                var offset = values.Offset;

                // 最大・最小・二乗和を1ループで計算しつつ、バッファへ int としてコピーする。
                // BitConverter.ToInt32 はリトルエンディアン環境であればそのまま使える。
                this.minFinder.Reset();
                this.maxFinder.Reset();
                var sumOfSquares = 0.0;

                for (var index = 0; index < n; index++)
                {
                    var v = BitConverter.ToInt32(array, offset + (index * sizeof(int)));
                    this.buffer[index] = v;
                    this.minFinder.Evaluate(v, index);
                    this.maxFinder.Evaluate(v, index);

                    // double にキャストしてからの乗算でオーバーフローを回避する。
                    double d = v;
                    sumOfSquares += d * d;
                }

                // 中央値はソートして求める。
                Array.Sort(this.buffer);
                var mid = n / 2;
                var median = (n % 2 == 1) ? this.buffer[mid] : ((long)this.buffer[mid - 1] + this.buffer[mid]) * 0.5;

                // 二乗平均平方根 RMS = √(Σx² / n)
                var rms = Math.Sqrt(sumOfSquares / n);

                return new CurrentStatsData(values, this.minFinder.Value, (double)this.minFinder.Index / n, this.maxFinder.Value, (double)this.maxFinder.Index / n, median, rms);
            }
        }
    }
}
