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
    /// ハードウェア測定値グラフ表示用情報
    /// </summary>
    internal class HardwareGraphSource : GraphSource
    {
        private readonly RingBuffer<HardwareData> ringBuffer = null;
        private readonly Color currentColor = default;
        private readonly Color motorColor = default;
        private readonly Color piezoColor = default;

        /// <summary>
        /// Initializes a new instance of the <see cref="HardwareGraphSource"/> class.
        /// </summary>
        /// <param name="serialNumber">Serial Number</param>
        /// <param name="hardwareData">ハードウェア測定値</param>
        /// <param name="currentColor">電流値描画色</param>
        /// <param name="motorColor">ステッピングモーター位置描画色</param>
        /// <param name="piezoColor">ピエゾアクチュエータ位置描画色</param>
        /// <param name="ringBufferCapacity">リングバッファの最大要素数</param>
        public HardwareGraphSource(uint serialNumber, HardwareData hardwareData, Color currentColor, Color motorColor, Color piezoColor, int ringBufferCapacity)
            : this(new RingBuffer<HardwareData>(ringBufferCapacity), currentColor, motorColor, piezoColor, serialNumber, hardwareData)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="HardwareGraphSource"/> class.
        /// </summary>
        /// <param name="source">追加元 GraphSource</param>
        /// <param name="serialNumber">Serial Number</param>
        /// <param name="hardwareData">ハードウェア測定値</param>
        public HardwareGraphSource(HardwareGraphSource source, uint serialNumber, HardwareData hardwareData)
            : this(source.ringBuffer, source.currentColor, source.motorColor, source.piezoColor, serialNumber, hardwareData)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="HardwareGraphSource"/> class.
        /// </summary>
        /// <param name="source">コピー元 GraphSource</param>
        public HardwareGraphSource(HardwareGraphSource source)
            : base(source.LastSerialNumber)
        {
            this.currentColor = source.currentColor;
            this.motorColor = source.motorColor;
            this.piezoColor = source.piezoColor;

            // 元の GraphSource を引き継いだ GraphSource での要素追加と、ここでのクローン操作を同時に行わないよう排他処理を施す。
            lock (source.ringBuffer.CollectionLock)
            {
                this.ringBuffer = new RingBuffer<HardwareData>(source.ringBuffer);  // 要素を shallow copy
            }
        }

        private HardwareGraphSource(RingBuffer<HardwareData> ringBuffer, Color currentColor, Color motorColor, Color piezoColor, uint serialNumber, HardwareData hardwareData)
            : base(serialNumber)
        {
            this.ringBuffer = ringBuffer;
            this.currentColor = currentColor;
            this.motorColor = motorColor;
            this.piezoColor = piezoColor;

            // 元の GraphSource の描画時の要素参照、元の GraphSource からの Snap 発生時のクローン操作、そしてここでの要素追加を同時に行わないよう排他処理を施す。
            lock (this.ringBuffer.CollectionLock)
            {
                this.ringBuffer.Add(hardwareData);
            }
        }

        /// <inheritdoc/>
        public override int BufferCount => this.ringBuffer.Count;

        /// <inheritdoc/>
        public override bool DrawLineGraph(AxisData<int> xAxis, IReadOnlyList<AxisData<double>> yAxisCollection, Func<Color[], Action<double, double>[]> notifyGraphCount)
        {
            if (xAxis == null || yAxisCollection == null || yAxisCollection.Count < 3 || notifyGraphCount == null)
            {
                return false;
            }

            lock (this.ringBuffer.CollectionLock)
            {
                var addPoint = notifyGraphCount.Invoke(new Color[] { this.currentColor, this.motorColor, this.piezoColor });
                GetEffectiveXRange(this.ringBuffer, xAxis, out var startX, out var endX);

                if (xAxis.Max - xAxis.Min > 1000)
                {
                    var n = (xAxis.Max - xAxis.Min) / 1000;
                    DrawDecimatedData(this.ringBuffer, xAxis, yAxisCollection[0], addPoint[0], x => x.Current, startX, endX, n);
                    DrawDecimatedData(this.ringBuffer, xAxis, yAxisCollection[1], addPoint[1], x => x.Motor,   startX, endX, n);
                    DrawDecimatedData(this.ringBuffer, xAxis, yAxisCollection[2], addPoint[2], x => x.Piezo,   startX, endX, n);
                }
                else
                {
                    DrawRawData(this.ringBuffer, xAxis, yAxisCollection[0], addPoint[0], x => x.Current, startX, endX);
                    DrawRawData(this.ringBuffer, xAxis, yAxisCollection[1], addPoint[1], x => x.Motor,   startX, endX);
                    DrawRawData(this.ringBuffer, xAxis, yAxisCollection[2], addPoint[2], x => x.Piezo,   startX, endX);
                }

                return true;
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
                    case 1:  axis = GetAxisData(this.ringBuffer, xAxis, x => x.Motor);                 return true;
                    case 2:  axis = GetAxisData(this.ringBuffer, xAxis, x => x.Piezo);                 return true;
                    default: axis = default;                                                           return false;
                }
            }
        }

        private static AxisData<double> GetCurrentAxisData(RingBuffer<HardwareData> ringBuffer, AxisData<int> xAxis, ReadOnlyCollection<AxisData<double>> yAxisCollection)
        {
            GetMax(ringBuffer, xAxis, x => x.Current, out var max);
            return yAxisCollection.FirstOrDefault(x => !x.Auto && x.Max > max) ?? yAxisCollection[yAxisCollection.Count - 1];
        }

        private static AxisData<double> GetAxisData(RingBuffer<HardwareData> ringBuffer, AxisData<int> xAxis, Func<HardwareData, int> getter)
        {
            GetMinMax(ringBuffer, xAxis, getter, out var min, out var max);
            return CreateGenericAxisData(min, max);
        }

        private static readonly ReadOnlyCollection<uint> UintRangeList = new ReadOnlyCollection<uint>(new uint[]
        {
            10U, 20U, 50U,
            100U, 200U, 500U,
            1000U, 2000U, 5000U,
            10000U, 20000U, 50000U,
            100000U, 200000U, 500000U,
            1000000U, 2000000U, 5000000U,
            10000000U, 20000000U, 50000000U,
            100000000U, 200000000U, 500000000U,
            1000000000U, 2000000000U,
        });

        private static AxisData<double> CreateGenericAxisData(int min, int max)
        {
            var range = (long)max - min;
            var presetRange = (long)UintRangeList.FirstOrDefault(x => x > range);
            if (presetRange == 0)
            {
                presetRange = 5000000000L;
            }

            var axisMin = min;
            var axisMid = min + (presetRange / 2);
            var axisMax = min + presetRange;
            return new AxisData<double>(axisMin, axisMax, axisMin.ToString(), axisMid.ToString(), axisMax.ToString(), $"{presetRange / 10} / DIV");
        }
    }
}
