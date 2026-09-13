// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Data
{
    using System;
    using System.Collections.Generic;
    using System.Drawing;
    using Sony.Jin.Shared;

    /// <summary>
    /// 折れ線グラフを描画する処理
    /// </summary>
    /// <param name="xAxis">横軸描画範囲</param>
    /// <param name="yAxisCollection">縦軸描画範囲一覧</param>
    /// <param name="notifyGraphCount">グラフ数・描画色通知操作（引数: 描画色一覧、戻値: 描画点追加デリゲート。順に X 座標、Y 座標。座標は左下原点の幅1、高さ1の正規化座標系。</param>
    /// <returns>成功時 true、エラー時 false</returns>
    internal delegate bool DrawLineGraphFunc(AxisData<int> xAxis, IReadOnlyList<AxisData<double>> yAxisCollection, Func<Color[], Action<double, double>[]> notifyGraphCount);

    /// <summary>
    /// グラフ表示用情報
    /// </summary>
    internal abstract class GraphSource
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="GraphSource"/> class.
        /// </summary>
        /// <param name="serialNumber">Serial Number</param>
        public GraphSource(uint serialNumber)
        {
            this.LastSerialNumber = serialNumber;
        }

        /// <summary>
        /// 最終フレームの Serial Number を取得する。
        /// </summary>
        public uint LastSerialNumber { get; }

        /// <summary>
        /// データバッファの要素数を取得する。
        /// </summary>
        public abstract int BufferCount { get; }

        /// <summary>
        /// 折れ線グラフを描画する。
        /// </summary>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="yAxisCollection">縦軸描画範囲一覧</param>
        /// <param name="notifyGraphCount">グラフ数・描画色通知操作（引数: 描画色一覧、戻値: 描画点追加デリゲート。順に X 座標、Y 座標。座標は左下原点の幅1、高さ1の正規化座標系。</param>
        /// <returns>成功時 true、エラー時 false</returns>
        public abstract bool DrawLineGraph(AxisData<int> xAxis, IReadOnlyList<AxisData<double>> yAxisCollection, Func<Color[], Action<double, double>[]> notifyGraphCount);

        /// <summary>
        /// 縦軸描画範囲を自動で取得する。
        /// </summary>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="yAutoAxis">縦軸自動指定インスタンス</param>
        /// <param name="graphIndex">対象のグラフ番号</param>
        /// <param name="yAxis">縦軸描画範囲</param>
        /// <returns>成功時 true、エラー時 false</returns>
        public abstract bool GetAutoYAxis(AxisData<int> xAxis, AxisData<double> yAutoAxis, int graphIndex, out AxisData<double> yAxis);

        /// <summary>
        /// データを間引きながら折れ線グラフを描画する。
        /// </summary>
        /// <typeparam name="T">データバッファの要素型</typeparam>
        /// <param name="ringBuffer">データバッファ</param>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="yAxis">縦軸描画範囲</param>
        /// <param name="addPoint">グラフへの頂点追加操作</param>
        /// <param name="selector">対象のプロパティセレクタ</param>
        /// <param name="startX">有効な開始 X 座標</param>
        /// <param name="endX">有効な終了 X 座標</param>
        /// <param name="n">間引く単位数</param>
        protected static void DrawDecimatedData<T>(RingBuffer<T> ringBuffer, AxisData<int> xAxis, AxisData<double> yAxis, Action<double, double> addPoint, Func<T, double> selector, int startX, int endX, int n)
        {
            // Min-Max Decimation ロジックにより、最大値・最小値の2点で代表させて描画点を間引く。
            var minFinder = new DoubleMinFinder();
            var maxFinder = new DoubleMaxFinder();

            for (var x = startX; x <= endX; x++)
            {
                var stats = GetData(ringBuffer, x);
                minFinder.Evaluate(selector.Invoke(stats), x);
                maxFinder.Evaluate(selector.Invoke(stats), x);

                if ((x - startX + 1) % n == 0)
                {
                    var nxmin = xAxis.NormalizationFactor * (minFinder.Index - xAxis.Min);
                    var nxmax = xAxis.NormalizationFactor * (maxFinder.Index - xAxis.Min);
                    var nymin = yAxis.NormalizationFactor * (minFinder.Value - yAxis.Min);
                    var nymax = yAxis.NormalizationFactor * (maxFinder.Value - yAxis.Min);
                    AddDecimatedPoints(addPoint, nxmin, nymin, nxmax, nymax);

                    minFinder.Reset();
                    maxFinder.Reset();
                }
            }
        }

        /// <summary>
        /// データを間引きかず、すべてを用いて折れ線グラフを描画する。
        /// </summary>
        /// <typeparam name="T">データバッファの要素型</typeparam>
        /// <param name="ringBuffer">データバッファ</param>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="yAxis">縦軸描画範囲</param>
        /// <param name="addPoint">グラフへの頂点追加操作</param>
        /// <param name="selector">対象のプロパティセレクタ</param>
        /// <param name="startX">有効な開始 X 座標</param>
        /// <param name="endX">有効な終了 X 座標</param>
        protected static void DrawRawData<T>(RingBuffer<T> ringBuffer, AxisData<int> xAxis, AxisData<double> yAxis, Action<double, double> addPoint, Func<T, double> selector, int startX, int endX)
        {
            for (var x = startX; x <= endX; x++)
            {
                var stats = GetData(ringBuffer, x);
                var nx = xAxis.NormalizationFactor * (x - xAxis.Min);
                var ny = yAxis.NormalizationFactor * (selector.Invoke(stats) - yAxis.Min);
                addPoint.Invoke(nx, ny);
            }
        }

        /// <summary>
        /// Min-Max Decimation により抽出した最大値・最小値の2点を X 座標の順に折れ線グラフの頂点に追加する。
        /// </summary>
        /// <param name="action">グラフへの頂点追加操作</param>
        /// <param name="nx0">第1の点の正規化 X 座標</param>
        /// <param name="ny0">第1の点の正規化 Y 座標</param>
        /// <param name="nx1">第2の点の正規化 X 座標</param>
        /// <param name="ny1">第2の点の正規化 Y 座標</param>
        protected static void AddDecimatedPoints(Action<double, double> action, double nx0, double ny0, double nx1, double ny1)
        {
            if (nx0 < nx1)
            {
                action.Invoke(nx0, ny0);
                action.Invoke(nx1, ny1);
            }
            else
            {
                action.Invoke(nx1, ny1);
                action.Invoke(nx0, ny0);
            }
        }

        /// <summary>
        /// データ列から指定のプロパティ値の最大値を探索する。
        /// </summary>
        /// <typeparam name="T">データバッファの要素型</typeparam>
        /// <param name="ringBuffer">データバッファ</param>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="selector">対象のプロパティセレクタ</param>
        /// <param name="max">最大値</param>
        protected static void GetMax<T>(RingBuffer<T> ringBuffer, AxisData<int> xAxis, Func<T, int> selector, out int max)
        {
            max = int.MinValue;

            GetEffectiveXRange(ringBuffer, xAxis, out var startX, out var endX);
            for (var x = startX; x <= endX; x++)
            {
                var value = selector.Invoke(GetData(ringBuffer, x));
                max = Math.Max(value, max);
            }
        }

        /// <summary>
        /// データ列から指定のプロパティ値の最小値と最大値を探索する。
        /// </summary>
        /// <typeparam name="T">データバッファの要素型</typeparam>
        /// <param name="ringBuffer">データバッファ</param>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="selector">対象のプロパティセレクタ</param>
        /// <param name="min">最小値</param>
        /// <param name="max">最大値</param>
        protected static void GetMinMax<T>(RingBuffer<T> ringBuffer, AxisData<int> xAxis, Func<T, int> selector, out int min, out int max)
        {
            max = int.MinValue;
            min = int.MaxValue;

            GetEffectiveXRange(ringBuffer, xAxis, out var startX, out var endX);
            for (var x = startX; x <= endX; x++)
            {
                var value = selector.Invoke(GetData(ringBuffer, x));
                max = Math.Max(value, max);
                min = Math.Min(value, min);
            }
        }

        /// <summary>
        /// 有効な開始・終了 X 座標を求める。
        /// </summary>
        /// <typeparam name="T">データバッファの要素型</typeparam>
        /// <param name="ringBuffer">データバッファ</param>
        /// <param name="xAxis">横軸描画範囲</param>
        /// <param name="startX">開始 X 座標</param>
        /// <param name="endX">終了 X 座標</param>
        protected static void GetEffectiveXRange<T>(RingBuffer<T> ringBuffer, AxisData<int> xAxis, out int startX, out int endX)
        {
            // X 軸の表示区間内で CurrentStatsData が存在する範囲を取得する。
            startX = Clamp(ringBuffer.Capacity - ringBuffer.Count, xAxis.Min, xAxis.Max - 1);
            endX   = Clamp(ringBuffer.Capacity - 1,                xAxis.Min, xAxis.Max - 1);
        }

        /// <summary>
        /// 指定の X 座標のデータを取得する。
        /// </summary>
        /// <typeparam name="T">データバッファの要素型</typeparam>
        /// <param name="ringBuffer">データバッファ</param>
        /// <param name="x">X 座標</param>
        /// <returns>データ要素</returns>
        protected static T GetData<T>(RingBuffer<T> ringBuffer, int x)
        {
            // 指定の X 座標上の CurrentStatsData を取得する。
            return ringBuffer[x + ringBuffer.Count - ringBuffer.Capacity];
        }

        private static int Clamp(int value, int min, int max)
        {
            return Math.Min(Math.Max(value, min), max);
        }

        /// <summary>
        /// int 型の値の列に対して最小値を求める操作を提供する。
        /// </summary>
        protected class IntMinFinder : Finder<int>
        {
            /// <summary>
            /// Initializes a new instance of the <see cref="IntMinFinder"/> class.
            /// </summary>
            public IntMinFinder()
                : base((x, y) => x < y, int.MaxValue)
            {
            }
        }

        /// <summary>
        /// int 型の値の列に対して最大値を求める操作を提供する。
        /// </summary>
        protected class IntMaxFinder : Finder<int>
        {
            /// <summary>
            /// Initializes a new instance of the <see cref="IntMaxFinder"/> class.
            /// </summary>
            public IntMaxFinder()
                : base((x, y) => x > y, int.MinValue)
            {
            }
        }

        /// <summary>
        /// double 型の値の列に対して最小値を求める操作を提供する。
        /// </summary>
        protected class DoubleMinFinder : Finder<double>
        {
            /// <summary>
            /// Initializes a new instance of the <see cref="DoubleMinFinder"/> class.
            /// </summary>
            public DoubleMinFinder()
                : base((x, y) => x < y, double.MaxValue)
            {
            }
        }

        /// <summary>
        /// double 型の値の列に対して最大値を求める操作を提供する。
        /// </summary>
        protected class DoubleMaxFinder : Finder<double>
        {
            /// <summary>
            /// Initializes a new instance of the <see cref="DoubleMaxFinder"/> class.
            /// </summary>
            public DoubleMaxFinder()
                : base((x, y) => x > y, double.MinValue)
            {
            }
        }

        /// <summary>
        /// ある値の列に対して指定の評価式で最終的に残る値を求める操作を提供する。
        /// </summary>
        /// <typeparam name="T">値の型</typeparam>
        protected class Finder<T>
        {
            private readonly Func<T, T, bool> condition = null;
            private readonly T initialValue = default;

            /// <summary>
            /// Initializes a new instance of the <see cref="Finder{T}"/> class.
            /// </summary>
            /// <param name="condition">評価式</param>
            /// <param name="initialValue">初期値</param>
            public Finder(Func<T, T, bool> condition, T initialValue)
            {
                this.condition = condition;
                this.initialValue = initialValue;
                this.Reset();
            }

            /// <summary>
            /// 現在の値を取得する。
            /// </summary>
            public T Value { get; private set; }

            /// <summary>
            /// 現在 Value に適用されている値のインデックスを取得する。
            /// </summary>
            public int Index { get; private set; }

            /// <summary>
            /// 現在 Value に適用されている値の位置を取得する。
            /// </summary>
            public double Position { get; private set; }

            /// <summary>
            /// 値を評価する。条件に見合う場合、プロパティ Value がその値に上書きされる。
            /// </summary>
            /// <param name="value">評価対象値</param>
            /// <param name="index">評価対象値のインデックス値</param>
            /// <param name="position">評価対象値の位置</param>
            public void Evaluate(T value, int index, double position = default)
            {
                if (this.condition.Invoke(value, this.Value))
                {
                    this.Value = value;
                    this.Index = index;
                    this.Position = position;
                }
            }

            /// <summary>
            /// 初期状態にリセットする。
            /// </summary>
            public void Reset()
            {
                this.Value = this.initialValue;
                this.Index = default;
                this.Position = default;
            }
        }
    }
}
