// Copyright 2021-2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Views
{
    using System;
    using System.Collections.Generic;
    using System.Globalization;
    using System.Windows;
    using System.Windows.Controls;
    using System.Windows.Documents;
    using System.Windows.Media;
    using Sony.Jin.Gateway.Data;

    /// <summary>
    /// 解析データのグラフ表示を行う。
    /// </summary>
    internal class GraphGrid : FrameworkElement
    {
        private Pen borderLinePen = null;
        private Pen auxLinePen = null;
        private Pen auxSubLinePen = null;
        private Typeface typeface = null;
        private double fontsize = default;
        private int skippedCount = 0;

        /// <summary>
        /// GraphSource の依存関係プロパティ
        /// </summary>
        public static readonly DependencyProperty GraphSourceProperty
            = DependencyProperty.Register(nameof(GraphSource), typeof(GraphSource), typeof(GraphGrid), new FrameworkPropertyMetadata(null, GraphSourcePropertyChanged));

        /// <summary>
        /// XAxis の依存関係プロパティ
        /// </summary>
        public static readonly DependencyProperty XAxisProperty
            = DependencyProperty.Register(nameof(XAxis), typeof(AxisData<int>), typeof(GraphGrid), new FrameworkPropertyMetadata(null, AxisPropertyChanged));

        /// <summary>
        /// YAxis の依存関係プロパティ
        /// </summary>
        public static readonly DependencyProperty YAxisProperty
            = DependencyProperty.Register(nameof(YAxis), typeof(AxisData<double>), typeof(GraphGrid), new FrameworkPropertyMetadata(null, AxisPropertyChanged));

        /// <summary>
        /// YAxisAux1 の依存関係プロパティ
        /// </summary>
        public static readonly DependencyProperty YAxisAux1Property
            = DependencyProperty.Register(nameof(YAxisAux1), typeof(AxisData<double>), typeof(GraphGrid), new FrameworkPropertyMetadata(null, AxisPropertyChanged));

        /// <summary>
        /// YAxisAux2 の依存関係プロパティ
        /// </summary>
        public static readonly DependencyProperty YAxisAux2Property
            = DependencyProperty.Register(nameof(YAxisAux2), typeof(AxisData<double>), typeof(GraphGrid), new FrameworkPropertyMetadata(null, AxisPropertyChanged));

        /// <summary>
        /// Foreground の依存関係プロパティ（TextElement.Foreground を AddOwner で借りる）
        /// </summary>
        public static readonly DependencyProperty ForegroundProperty
            = TextElement.ForegroundProperty.AddOwner(typeof(GraphGrid), new FrameworkPropertyMetadata(SystemColors.ControlTextBrush, FrameworkPropertyMetadataOptions.Inherits, ForegroundPropertyChanged));

        /// <summary>
        /// Initializes a new instance of the <see cref="GraphGrid"/> class.
        /// </summary>
        public GraphGrid()
        {
        }

        /// <summary>
        /// グラフ表示用情報を取得/設定する。
        /// </summary>
        public GraphSource GraphSource
        {
            get => (GraphSource)this.GetValue(GraphSourceProperty);
            set => this.SetValue(GraphSourceProperty, value);
        }

        /// <summary>
        /// 横軸描画範囲を取得/設定する。
        /// </summary>
        public AxisData<int> XAxis
        {
            get => (AxisData<int>)this.GetValue(XAxisProperty);
            set => this.SetValue(XAxisProperty, value);
        }

        /// <summary>
        /// 縦軸描画範囲を取得/設定する。
        /// </summary>
        public AxisData<double> YAxis
        {
            get => (AxisData<double>)this.GetValue(YAxisProperty);
            set => this.SetValue(YAxisProperty, value);
        }

        /// <summary>
        /// 縦軸描画範囲を取得/設定する。
        /// </summary>
        public AxisData<double> YAxisAux1
        {
            get => (AxisData<double>)this.GetValue(YAxisAux1Property);
            set => this.SetValue(YAxisAux1Property, value);
        }

        /// <summary>
        /// 縦軸描画範囲を取得/設定する。
        /// </summary>
        public AxisData<double> YAxisAux2
        {
            get => (AxisData<double>)this.GetValue(YAxisAux2Property);
            set => this.SetValue(YAxisAux2Property, value);
        }

        /// <summary>
        /// 前景色を取得/設定する。
        /// </summary>
        public Brush Foreground
        {
            get => (Brush)this.GetValue(ForegroundProperty);
            set => this.SetValue(ForegroundProperty, value);
        }

        private static void GraphSourcePropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (!(d is GraphGrid graphGrid))
            {
                return;
            }

            // 振幅が激しい波形の場合、グラフ横軸幅が大きいと描画するプロット数を間引いても UI スレッドを占有する時間が長くなるため、
            // 横軸幅の 1/100 ずつ進むように更新も間引く。1/1000 であれば滑らかな動きとなるが、一部 UI 操作が重くなるため、操作感を優先する。
            if (graphGrid.XAxis == null || (e.OldValue != null && ++graphGrid.skippedCount < (graphGrid.XAxis.Max - graphGrid.XAxis.Min) / 100))
            {
                return;
            }

            graphGrid.skippedCount = 0;
            graphGrid.InvalidateVisual();
        }

        private static void AxisPropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            (d as GraphGrid)?.InvalidateVisual();
        }

        private static void ForegroundPropertyChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (!(d is GraphGrid graphGrid))
            {
                return;
            }

            // 軸ラベル、境界線、主副補助線の共通色: Pro-UI ダークテーマ テキスト標準色
            graphGrid.borderLinePen = new Pen(graphGrid.Foreground, 1);
            if (graphGrid.borderLinePen.CanFreeze)
            {
                graphGrid.borderLinePen.Freeze();
            }

            graphGrid.auxLinePen = new Pen(graphGrid.Foreground, 1) { DashStyle = new DashStyle(new double[] { 2, 4 }, 0) };
            if (graphGrid.auxLinePen.CanFreeze)
            {
                graphGrid.auxLinePen.Freeze();
            }

            graphGrid.auxSubLinePen = new Pen(graphGrid.Foreground, 0.5) { DashStyle = new DashStyle(new double[] { 4, 8 }, 0) };
            if (graphGrid.auxSubLinePen.CanFreeze)
            {
                graphGrid.auxSubLinePen.Freeze();
            }

            graphGrid.InvalidateVisual();
        }

        /// <inheritdoc/>
        protected override void OnRender(DrawingContext dc)
        {
            base.OnRender(dc);

            // Loaded イベントより OnRender() が呼ばれるのが先のため、ここで this.typeface, this.fontsize 設定を行う。
            if (this.typeface == null)
            {
                this.InitFont();
            }

            this.DrawGraph(dc);
        }

        private void InitFont()
        {
            // 最も近い祖先 Control を探索
            var ancestor = this.Parent as FrameworkElement;
            while (!(ancestor is Control))
            {
                if (ancestor == null)
                {
                    return;
                }

                ancestor = ancestor.Parent as FrameworkElement;
            }

            // while() の処理によりここに null で来ることはないが、Fortify の指摘により ancestor と target の null チェックを入れる。
            if (!(ancestor is Control target))
            {
                return;
            }

            // 最も近い祖先 Control の Font 情報を継承
            this.typeface = new Typeface(target.FontFamily, target.FontStyle, target.FontWeight, target.FontStretch);
            this.fontsize = target.FontSize;
        }

        private void DrawGraph(DrawingContext dc)
        {
            var source = this.GraphSource;
            var xAxis = this.XAxis;
            var yAxis = this.YAxis;
            var yAxisAux1 = this.YAxisAux1;
            var yAxisAux2 = this.YAxisAux2;
            var yAxisCollection = new List<AxisData<double>>();

            if (xAxis == null || yAxis == null)
            {
                return;
            }

            this.DrawLinearAxisX(dc, xAxis.MinLabel, xAxis.MidLabel, xAxis.MaxLabel);

            if (source == null)
            {
                this.DrawLinearAxisY(dc, string.Empty, string.Empty, string.Empty);  // 起動時直後の source 未指示の状態でも軸・補助線だけは引いておく。
                return;
            }

            if (yAxis.Auto && !source.GetAutoYAxis(xAxis, yAxis, 0, out yAxis))
            {
                return;
            }

            this.DrawLinearAxisY(dc, yAxis.MinLabel, yAxis.MidLabel, yAxis.MaxLabel);
            yAxisCollection.Add(yAxis);

            if (yAxisAux1 != null && (!yAxisAux1.Auto || source.GetAutoYAxis(xAxis, yAxisAux1, 1, out yAxisAux1)))
            {
                this.DrawLinearAuxAxisY(dc, yAxisAux1.MinLabel, yAxisAux1.MidLabel, yAxisAux1.MaxLabel, 0);
                yAxisCollection.Add(yAxisAux1);

                if (yAxisAux2 != null && (!yAxisAux2.Auto || source.GetAutoYAxis(xAxis, yAxisAux2, 2, out yAxisAux2)))
                {
                    this.DrawLinearAuxAxisY(dc, yAxisAux2.MinLabel, yAxisAux2.MidLabel, yAxisAux2.MaxLabel, 50);
                    yAxisCollection.Add(yAxisAux2);
                }
            }

            this.DrawData(dc, xAxis, yAxisCollection, source.DrawLineGraph);
        }

        private void DrawData(DrawingContext dc, AxisData<int> xAxis, IReadOnlyList<AxisData<double>> yAxisCollection, DrawLineGraphFunc drawLineGraph)
        {
            var geometryWrappers = new List<StreamGeometryWrapper>();

            Action<double, double>[] NotifyGraphCount(System.Drawing.Color[] colors)
            {
                var actions = new Action<double, double>[colors == null ? 0 : colors.Length];
                for (var index = 0; index < actions.Length; index++)
                {
                    var geometryWrapper = new StreamGeometryWrapper(this.ActualWidth, this.ActualHeight, Color.FromArgb(colors[index].A, colors[index].R, colors[index].G, colors[index].B));
                    geometryWrappers.Add(geometryWrapper);
                    actions[index] = geometryWrapper.AddPoint;
                }

                return actions;
            }

            if (!drawLineGraph.Invoke(xAxis, yAxisCollection, NotifyGraphCount))
            {
                return;
            }

            var clipRect = new Rect(0, 0, this.ActualWidth, this.ActualHeight);
            dc.PushClip(new RectangleGeometry(clipRect));
            geometryWrappers.ForEach(x => x.Draw(dc));
            dc.Pop();
        }

        private void DrawLinearAxisX(DrawingContext dc, string minX, string midX, string maxX)
        {
            this.DrawLinearAxis(dc, this.DrawLineX, this.DrawLabelX, minX, midX, maxX);
        }

        private void DrawLinearAxisY(DrawingContext dc, string minY, string midY, string maxY)
        {
            this.DrawLinearAxis(dc, this.DrawLineY, this.DrawLabelY, minY, midY, maxY);
        }

        private void DrawLinearAuxAxisY(DrawingContext dc, string minY, string midY, string maxY, double margin)
        {
            this.DrawLinearAuxAxis(dc, this.DrawAuxLabelY, minY, midY, maxY, margin);
        }

        private void DrawLinearAxis(DrawingContext dc, Action<DrawingContext, Pen, double> drawline, Action<DrawingContext, string, double> drawlabel, string min, string mid, string max)
        {
            // 軸の上下限座標値
            drawlabel(dc, string.Format("{0}", min), 0.0);
            drawlabel(dc, string.Format("{0}", mid), 0.5);
            drawlabel(dc, string.Format("{0}", max), 1.0);

            drawline(dc, this.borderLinePen, 0.0);
            drawline(dc, this.borderLinePen, 1.0);

            // 座標値及び補助線
            for (var index = 1; index < 10; index++)
            {
                drawline(dc, this.auxLinePen, index * 0.1);
            }
        }

        private void DrawLinearAuxAxis(DrawingContext dc, Action<DrawingContext, string, double, double> drawlabel, string min, string mid, string max, double margin)
        {
            // 軸の上下限座標値
            drawlabel(dc, string.Format("{0}", min), 0.0, margin);
            drawlabel(dc, string.Format("{0}", mid), 0.5, margin);
            drawlabel(dc, string.Format("{0}", max), 1.0, margin);

            dc.DrawLine(this.borderLinePen, new Point(this.ActualWidth + margin,     0.0),                     new Point(this.ActualWidth + margin,     this.ActualHeight));
            dc.DrawLine(this.borderLinePen, new Point(this.ActualWidth + margin - 4, 0.0),                     new Point(this.ActualWidth + margin + 4, 0.0));
            dc.DrawLine(this.auxLinePen,    new Point(this.ActualWidth + margin - 4, this.ActualHeight * 0.5), new Point(this.ActualWidth + margin + 4, this.ActualHeight * 0.5));
            dc.DrawLine(this.borderLinePen, new Point(this.ActualWidth + margin - 4, this.ActualHeight),       new Point(this.ActualWidth + margin + 4, this.ActualHeight));
        }

        private void DrawLabelX(DrawingContext dc, string text, double x)
        {
            const int marginBottom = 10;
            if (this.typeface == null)
            {
                return;
            }

            // X 軸下側にテキストを描く。
            var formattedText = new FormattedText(text, CultureInfo.CurrentCulture, FlowDirection.LeftToRight, this.typeface, this.fontsize, this.Foreground, 96);
            dc.DrawText(formattedText, new Point((-formattedText.Width * 0.5) + (x * this.ActualWidth), marginBottom + this.ActualHeight));
        }

        private void DrawLabelY(DrawingContext dc, string text, double y)
        {
            const int marginLeft = 10;
            if (this.typeface == null)
            {
                return;
            }

            // Y 軸左側にテキストを描く。FlowDirection.RightToLeft とすると text の先頭に "-" がある場合、末尾（右側に）に回されるので使用しない。
            var formattedText = new FormattedText(text, CultureInfo.CurrentCulture, FlowDirection.LeftToRight, this.typeface, this.fontsize, this.Foreground, 96);
            dc.DrawText(formattedText, new Point(-(marginLeft + formattedText.Width), (-formattedText.Height * 0.5) + ((1.0 - y) * this.ActualHeight)));
        }

        private void DrawAuxLabelY(DrawingContext dc, string text, double y, double margin)
        {
            const int marginLeft = 10;
            if (this.typeface == null)
            {
                return;
            }

            var formattedText = new FormattedText(text, CultureInfo.CurrentCulture, FlowDirection.LeftToRight, this.typeface, this.fontsize, this.Foreground, 96);
            dc.DrawText(formattedText, new Point(marginLeft + this.ActualWidth + margin, (-formattedText.Height * 0.5) + ((1.0 - y) * this.ActualHeight)));
        }

        private void DrawLineX(DrawingContext dc, Pen pen, double x)
        {
            this.DrawLine(dc, pen, x, 0, x, 1);
        }

        private void DrawLineY(DrawingContext dc, Pen pen, double y)
        {
            this.DrawLine(dc, pen, 0, y, 1, y);
        }

        private void DrawLine(DrawingContext dc, Pen pen, double x1, double y1, double x2, double y2)
        {
            // 左下原点、幅・高さ共に 1 の正規化座標系から Grid 内の描画座標系への変換
            dc.DrawLine(pen, new Point(x1 * this.ActualWidth, (1.0 - y1) * this.ActualHeight), new Point(x2 * this.ActualWidth, (1.0 - y2) * this.ActualHeight));
        }

        private class StreamGeometryWrapper
        {
            private readonly StreamGeometry geometry = null;
            private readonly StreamGeometryContext context = null;
            private readonly Pen pen = null;
            private readonly double actualWidth = default;
            private readonly double actualHeight = default;
            private bool empty = true;

            public StreamGeometryWrapper(double actualWidth, double actualHeight, Color color)
            {
                this.actualWidth = actualWidth;
                this.actualHeight = actualHeight;
                this.pen = new Pen(new SolidColorBrush(color), 1);
                this.pen.Freeze();
                this.geometry = new StreamGeometry();
                this.context = this.geometry.Open();
            }

            public void Draw(DrawingContext dc)
            {
                (this.context as IDisposable)?.Dispose();
                this.geometry.Freeze();

                dc.DrawGeometry(null, this.pen, this.geometry);
            }

            public void AddPoint(double x, double y)
            {
                // 左下原点、幅・高さ共に 1 の正規化座標系から Grid 内の描画座標系への変換
                var point = new Point(x * this.actualWidth, (1.0 - y) * this.actualHeight);
                if (this.empty)
                {
                    this.context.BeginFigure(point, false, false);
                    this.empty = false;
                }
                else
                {
                    this.context.LineTo(point, true, false);
                }
            }
        }
    }
}
