// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections;
    using System.Collections.ObjectModel;
    using System.Linq;
    using System.Reactive.Linq;
    using System.Threading;
    using System.Threading.Tasks;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IGraphModel{T}"/>
    internal class GraphModel<T> : DisposableBase, IGraphModel<T>
        where T : GraphSource
    {
        private readonly ObservableCollection<Item<T>> graphSourceCollection = new ObservableCollection<Item<T>>();
        private readonly ReactivePropertySlim<AxisData<int>> xAxis = null;
        private readonly ReactivePropertySlim<AxisData<double>> yAxis = null;
        private readonly ReactivePropertySlim<T> graphSource = null;
        private readonly Action<bool> notifyVisibilityRequest = null;
        private readonly NonblockingQueue<Item<T>> queue = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="GraphModel{T}"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="notifyVisibilityRequest">Window の表示状態変更を要求する Action</param>
        /// <param name="settingKeyPrefix">設定キー名の接頭辞</param>
        /// <param name="ringBufferCapacity">GraphSource のリングバッファ最大要素数</param>
        /// <param name="xAxisMinRange">X 軸最小範囲</param>
        /// <param name="xAxisMaxRange">X 軸最大範囲</param>
        /// <param name="snapGraph">Snap Graph か否か</param>
        public GraphModel(ILogger logger, AppConfig config, AppSettings settings, Action<bool> notifyVisibilityRequest, string settingKeyPrefix, int ringBufferCapacity, int xAxisMinRange, int xAxisMaxRange, bool snapGraph)
        {
            this.Logger = logger;
            this.notifyVisibilityRequest = notifyVisibilityRequest;
            this.RingBufferCapacity = ringBufferCapacity;
            this.SnapGraph = snapGraph;

            var xAxisArray = new AxisData<int>[]
            {
                new AxisData<int>(ringBufferCapacity - 1,      ringBufferCapacity, "10ms",  "5ms",   "0ms",  "1ms / DIV"),
                new AxisData<int>(ringBufferCapacity - 2,      ringBufferCapacity, "20ms",  "10ms",  "0ms",  "2ms / DIV"),
                new AxisData<int>(ringBufferCapacity - 5,      ringBufferCapacity, "50ms",  "25ms",  "0ms",  "5ms / DIV"),
                new AxisData<int>(ringBufferCapacity - 10,     ringBufferCapacity, "100ms", "50ms",  "0ms",  "10ms / DIV"),
                new AxisData<int>(ringBufferCapacity - 20,     ringBufferCapacity, "200ms", "100ms", "0ms",  "20ms / DIV"),
                new AxisData<int>(ringBufferCapacity - 50,     ringBufferCapacity, "500ms", "250ms", "0ms",  "50ms / DIV"),
                new AxisData<int>(ringBufferCapacity - 100,    ringBufferCapacity, "1.0s",  "0.5s",  "0.0s", "0.1s / DIV"),
                new AxisData<int>(ringBufferCapacity - 200,    ringBufferCapacity, "2.0s",  "1.0s",  "0.0s", "0.2s / DIV"),
                new AxisData<int>(ringBufferCapacity - 500,    ringBufferCapacity, "5.0s",  "2.5s",  "0.0s", "0.5s / DIV"),
                new AxisData<int>(ringBufferCapacity - 1000,   ringBufferCapacity, "10s",   "5s",    "0s",   "1s / DIV"),
                new AxisData<int>(ringBufferCapacity - 2000,   ringBufferCapacity, "20s",   "10s",   "0s",   "2s / DIV"),
                new AxisData<int>(ringBufferCapacity - 5000,   ringBufferCapacity, "50s",   "25s",   "0s",   "5s / DIV"),
                new AxisData<int>(ringBufferCapacity - 10000,  ringBufferCapacity, "100s",  "50s",   "0s",   "10s / DIV"),
                new AxisData<int>(ringBufferCapacity - 20000,  ringBufferCapacity, "200s",  "100s",  "0s",   "20s / DIV"),
                new AxisData<int>(ringBufferCapacity - 50000,  ringBufferCapacity, "500s",  "250s",  "0s",   "50s / DIV"),
                new AxisData<int>(ringBufferCapacity - 100000, ringBufferCapacity, "1000s", "500s",  "0s",   "100s / DIV"),
            };

            this.XAxisCollection = new ReadOnlyCollection<AxisData<int>>(xAxisArray.Where(x => (x.Max - x.Min) >= xAxisMinRange && (x.Max - x.Min) <= xAxisMaxRange).ToArray());

            var valuePerMicroAmpereInLowMode = config.ValuePerMicroAmpereInLowMode;
            this.LowModeYAxisCollection = new ReadOnlyCollection<AxisData<double>>(new AxisData<double>[]
            {
                new AxisData<double>(() => this.LowModeYAxisCollection),  // 自動計算指定
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 1,   "0.0uA", "0.5uA", "1.0uA", "0.1uA / DIV"),
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 2,   "0.0uA", "1.0uA", "2.0uA", "0.2uA / DIV"),
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 5,   "0.0uA", "2.5uA", "5.0uA", "0.5uA / DIV"),
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 10,  "0uA",   "5uA",   "10uA",  "1uA / DIV"),
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 20,  "0uA",   "10uA",  "20uA",  "2uA / DIV"),
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 50,  "0uA",   "25uA",  "50uA",  "5uA / DIV"),
                new AxisData<double>(0.0, valuePerMicroAmpereInLowMode * 100, "0uA",   "50uA",  "100uA", "10uA / DIV"),
            });

            var valuePerPicoAmpereInHighMode = config.ValuePerPicoAmpereInHighMode;
            this.HighModeYAxisCollection = new ReadOnlyCollection<AxisData<double>>(new AxisData<double>[]
            {
                new AxisData<double>(() => this.HighModeYAxisCollection),  // 自動計算指定
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 1,    "0.0pA", "0.5pA", "1.0pA", "0.1pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 2,    "0.0pA", "1.0pA", "2.0pA", "0.2pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 5,    "0.0pA", "2.5pA", "5.0pA", "0.5pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 10,   "0pA",   "5pA",   "10pA",  "1pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 20,   "0pA",   "10pA",  "20pA",  "2pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 50,   "0pA",   "25pA",  "50pA",  "5pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 100,  "0pA",   "50pA",  "100pA", "10pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 200,  "0pA",   "100pA", "200pA", "20pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 500,  "0pA",   "250pA", "500pA", "50pA / DIV"),
                new AxisData<double>(0.0, valuePerPicoAmpereInHighMode * 1000, "0pA",   "0.5nA", "1.0nA", "0.1nA / DIV"),
            });

            this.GraphSourceItems = new ReadOnlyObservableCollection<Item<T>>(this.graphSourceCollection);

            var selectedXAxis = settings.ToObservableSetting<string>(settingKeyPrefix + "XAxis", "1s / DIV").AddTo(this.CompositeDisposable);
            this.SelectedXAxis = selectedXAxis.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => this.XAxisCollection.FirstOrDefault(i => i.DisplayName == x) ?? this.XAxisCollection[0],
                x => x.DisplayName).AddTo(this.CompositeDisposable);

            var selectedLowModeYAxis = settings.ToObservableSetting<string>(settingKeyPrefix + "LowModeYAxis", this.LowModeYAxisCollection[0].DisplayName).AddTo(this.CompositeDisposable);
            this.SelectedLowModeYAxis = selectedLowModeYAxis.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => this.LowModeYAxisCollection.FirstOrDefault(i => i.DisplayName == x) ?? this.LowModeYAxisCollection[0],
                x => x.DisplayName).AddTo(this.CompositeDisposable);

            var selectedHighModeYAxis = settings.ToObservableSetting<string>(settingKeyPrefix + "HighModeYAxis ", this.HighModeYAxisCollection[0].DisplayName).AddTo(this.CompositeDisposable);
            this.SelectedHighModeYAxis = selectedHighModeYAxis.ToReactivePropertySlimAsSynchronized(
                x => x.Value,
                x => this.HighModeYAxisCollection.FirstOrDefault(i => i.DisplayName == x) ?? this.HighModeYAxisCollection[0],
                x => x.DisplayName).AddTo(this.CompositeDisposable);

            this.SelectedGraphSourceItem = new ReactivePropertySlim<Item<T>>(null).AddTo(this.CompositeDisposable);
            this.xAxis = new ReactivePropertySlim<AxisData<int>>(this.SelectedXAxis.Value).AddTo(this.CompositeDisposable);
            this.XAxis = this.xAxis.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.yAxis = new ReactivePropertySlim<AxisData<double>>(this.SelectedLowModeYAxis.Value).AddTo(this.CompositeDisposable);
            this.YAxis = this.yAxis.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.graphSource = new ReactivePropertySlim<T>(null).AddTo(this.CompositeDisposable);
            this.GraphSource = this.graphSource.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);

            if (snapGraph)
            {
                this.PageLeftAvailable = Observable.CombineLatest(this.xAxis, this.graphSource, (x, y) => y != null && CheckMoveXAxis(x, -10, y.BufferCount, this.RingBufferCapacity)).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
                this.PageRightAvailable = Observable.CombineLatest(this.xAxis, this.graphSource, (x, y) => y != null && CheckMoveXAxis(x, 10, y.BufferCount, this.RingBufferCapacity)).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
                this.DivisionLeftAvailable = Observable.CombineLatest(this.xAxis, this.graphSource, (x, y) => y != null && CheckMoveXAxis(x, -1, y.BufferCount, this.RingBufferCapacity)).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
                this.DivisionRightAvailable = Observable.CombineLatest(this.xAxis, this.graphSource, (x, y) => y != null && CheckMoveXAxis(x, 1, y.BufferCount, this.RingBufferCapacity)).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
                Observable.CombineLatest(this.graphSource, this.SelectedXAxis, (x, y) => (GraphSource: x, XAxis: y)).Subscribe(x => Task.Run(() => this.TryUpdateXAxis(x.GraphSource, x.XAxis, 0))).AddTo(this.CompositeDisposable);
            }
            else
            {
                this.PageLeftAvailable = new ReadOnlyReactivePropertySlim<bool>(Observable.Empty<bool>(), false).AddTo(this.CompositeDisposable);
                this.PageRightAvailable = new ReadOnlyReactivePropertySlim<bool>(Observable.Empty<bool>(), false).AddTo(this.CompositeDisposable);
                this.DivisionLeftAvailable = new ReadOnlyReactivePropertySlim<bool>(Observable.Empty<bool>(), false).AddTo(this.CompositeDisposable);
                this.DivisionRightAvailable = new ReadOnlyReactivePropertySlim<bool>(Observable.Empty<bool>(), false).AddTo(this.CompositeDisposable);
                this.SelectedXAxis.Subscribe(x => Task.Run(() => this.xAxis.Value = x)).AddTo(this.CompositeDisposable);
            }

            // UI スレッドからの変化だけ非同期で Reaction する。非同期処理は順序が維持されるよう NonblockingQueue を利用する。
            this.queue = new NonblockingQueue<Item<T>>(this.SetGraphSource).AddTo(this.CompositeDisposable);
            this.SelectedGraphSourceItem.Where(_ => SynchronizationContext.Current != null).Subscribe(x => this.queue.AddAsync(x)).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// ILogger インスタンスを取得する。
        /// </summary>
        protected ILogger Logger { get; }

        /// <summary>
        /// GraphSource のリングバッファ最大要素数を取得する。
        /// </summary>
        protected int RingBufferCapacity { get; }

        /// <inheritdoc/>
        public bool SnapGraph { get; }

        /// <inheritdoc/>
        public ReadOnlyCollection<AxisData<int>> XAxisCollection { get; }

        /// <inheritdoc/>
        public ReadOnlyCollection<AxisData<double>> LowModeYAxisCollection { get; }

        /// <inheritdoc/>
        public ReadOnlyCollection<AxisData<double>> HighModeYAxisCollection { get; }

        /// <inheritdoc/>
        public ReadOnlyObservableCollection<Item<T>> GraphSourceItems { get; }

        /// <inheritdoc/>
        public IReactiveProperty<AxisData<int>> SelectedXAxis { get; }

        /// <inheritdoc/>
        public IReactiveProperty<AxisData<double>> SelectedLowModeYAxis { get; }

        /// <inheritdoc/>
        public IReactiveProperty<AxisData<double>> SelectedHighModeYAxis { get; }

        /// <inheritdoc/>
        public IReactiveProperty<Item<T>> SelectedGraphSourceItem { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<AxisData<int>> XAxis { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<AxisData<double>> YAxis { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> PageLeftAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> PageRightAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> DivisionLeftAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<bool> DivisionRightAvailable { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<T> GraphSource { get; }

        /// <inheritdoc/>
        public bool MoveXAxis(int delta)
        {
            if (!this.TryUpdateXAxis(this.graphSource.Value, null, delta))
            {
                this.Logger.Error(string.Format("Horizonal axis not moved: delta = {0}", delta));
                return false;
            }

            return true;
        }

        private static bool CheckMoveXAxis(AxisData<int> xAxis, int delta, int bufferCount, int bufferCapacity)
        {
            var range = xAxis.Max - xAxis.Min;
            if (range < 10 && Math.Abs(delta) < 10)
            {
                // 10ms / DIV 未満は RingBuffer 単位で ±1 DIV の横移動ができないため不可とする。
                return false;
            }

            if (delta > 0 && xAxis.Max >= bufferCapacity)
            {
                // 右側に既に張り付いているときに右側移動は不可とする。
                return false;
            }

            if (delta < 0 && xAxis.Min <= bufferCapacity - bufferCount)
            {
                // 左側に既に張り付いているときに左側移動は不可とする。
                return false;
            }

            return true;
        }

        // 横軸方向の移動が出来ない場合でもエラー扱いとはしない呼び出し元があるため、エラーログには出力しない。
        private bool TryUpdateXAxis(T graphSource, AxisData<int> xAxis, int delta)
        {
            if (graphSource == null)
            {
                return false;
            }

            var old = this.xAxis.Value;
            xAxis = xAxis ?? old;

            var range = xAxis.Max - xAxis.Min;
            if (delta != 0 && range < 10 && Math.Abs(delta) < 10)
            {
                // 10ms / DIV 未満は RingBuffer 単位で ±1 DIV の横移動ができないため不可とする。
                // 但し、delta = 0 時は横軸範囲指定のみを目的とし、±1 DIV の横移動は発生しないため、チェックの対象外とする。
                return false;
            }

            if (!TryMoveXAxis(old.Min, old.Max, range, range * delta / 10, graphSource.BufferCount, this.RingBufferCapacity, out var min, out var max))
            {
                return false;
            }

            this.xAxis.Value = CreateXAxisData(min, max, this.RingBufferCapacity, graphSource.LastSerialNumber, xAxis.DisplayName);
            return true;
        }

        private static bool TryMoveXAxis(int oldMin, int oldMax, int range, int shift, int bufferCount, int bufferCapacity, out int min, out int max)
        {
            // 先ず、横軸最小値がデータの存在範囲下限を越えないように移動する。
            min = Math.Max(((oldMin + oldMax - range) / 2) + shift, bufferCapacity - bufferCount);
            max = min + range;

            // その時、横軸最大値がデータの存在範囲上限を越えていたら、上限を優先して左側に超過分を移動する（左側の余白は許容するが、右側は許容しない）。
            if (max > bufferCapacity)
            {
                var diff = max - bufferCapacity;
                min -= diff;
                max = bufferCapacity;
            }

            return min >= 0;
        }

        private static AxisData<int> CreateXAxisData(int min, int max, int bufferCapacity, uint lastSerialNumber, string displayName)
        {
            var originSerialNumber = lastSerialNumber + 1 - bufferCapacity;  // SerialNumber = 0 の位置が X 軸左端よりも右側の場合もあるため、符号付きの long で計算

            // 負値の場合を考慮しつつミリ秒に直す（10 倍する）。X軸範囲が 10ms/DIV 未満の場合、midLabel の1ミリ秒の桁が 0 でないケースがある。
            var minLabel = CreateLabel((originSerialNumber + min) * 10);
            var midLabel = CreateLabel((originSerialNumber * 10) + ((min + max) * 5));
            var maxLabel = CreateLabel((originSerialNumber + max) * 10);
            return new AxisData<int>(min, max, minLabel, midLabel, maxLabel, displayName);
        }

        private static string CreateLabel(long milliseconds)
        {
            return string.Format("{0}{1:hh\\:mm\\:ss\\.fff}", milliseconds < 0 ? "-" : string.Empty, TimeSpan.FromMilliseconds(milliseconds));
        }

        /// <inheritdoc/>
        public virtual bool AddGraphSource(T graphSource)
        {
            // 10 msec ごとに +1 増える Serial Number を用いて絶対時刻に直したものを ComboBoxItem の Content とする。
            var displayName = TimeSpan.FromMilliseconds(graphSource.LastSerialNumber * 10).ToString(@"hh\:mm\:ss\.fff");
            var newItem = new Item<T>(graphSource, displayName);
            lock (((ICollection)this.graphSourceCollection).SyncRoot)
            {
                this.graphSourceCollection.Add(newItem);
            }

            this.SetGraphSource(newItem);
            this.notifyVisibilityRequest?.Invoke(true);
            return true;
        }

        /// <inheritdoc/>
        public void RemoveSelectedGraphSource()
        {
            var current = this.SelectedGraphSourceItem.Value;
            var newItem = default(Item<T>);
            lock (((ICollection)this.graphSourceCollection).SyncRoot)
            {
                var index = this.graphSourceCollection.IndexOf(current);
                if (index < 0)
                {
                    this.Logger.Error(string.Format("Graph source not removed: name = {0}", current?.Title ?? "(null)"));
                    return;
                }

                newItem = this.graphSourceCollection.Count <= 1 ? null : index >= this.graphSourceCollection.Count - 1 ? this.graphSourceCollection[index - 1] : this.graphSourceCollection[index + 1];

                // 重要: ComboBox の要素削除の際に新たな選択状態をセットするときの対処について
                //   ComboBox (Selector) のプロパティ ItemsSource に binding される Collection の要素削除と
                //   SelectedItem に binding される値の変更は、Selector 内の処理を踏まえて、
                //       (1) SelectedItem を null    ※ 予め削除前に選択を外すことで不整合の発生・不要な処理を防ぐ
                //       (2) ItemsSource の要素削除
                //       (3) SelectedItem を新たな選択要素をセット
                //   の UI スレッドにおける処理順を守ることが重要となる。特に (1) を欠く場合や、(3) が (2) の途中に割り込む場合、
                //   不整合により Selector から ItemsSource が null にセットされる症状が1回ないし複数回発生する。
                //   また、非 null がセットされているにも関わらず、View 上では無選択の状態になる症状が見られることもある。
                //   Model ではこの (1)(2)(3) の順序に従って処理を行うまでを役割とし、UI スレッド上での順序性の担保は GraphViewModel.cs にて行う。
                this.SetGraphSource((Item<T>)null);          // (1) の処理
                this.graphSourceCollection.RemoveAt(index);  // (2) の処理
            }

            if (newItem == null)
            {
                this.notifyVisibilityRequest?.Invoke(false);
            }

            this.SetGraphSource(newItem);  // (3) の処理
        }

        /// <summary>
        /// Y 軸情報を指定する。
        /// </summary>
        /// <param name="yAxis">Y 軸情報</param>
        protected void SetYAxis(AxisData<double> yAxis)
        {
            this.yAxis.Value = yAxis;
        }

        /// <summary>
        /// グラフ表示用情報をセットする。
        /// </summary>
        /// <param name="graphSource">グラフ表示用情報</param>
        protected void SetGraphSource(T graphSource)
        {
            this.graphSource.Value = graphSource;
        }

        private void SetGraphSource(Item<T> item)
        {
            this.SetGraphSource(item?.Value);
            this.SelectedGraphSourceItem.Value = item;
        }

        /// <summary>
        /// HTML のカラー形式テキスト（#RRGGBB）を System.Drawing.Color に変換する。
        /// </summary>
        /// <param name="htmlColor">HTML のカラー形式</param>
        /// <returns>System.Drawing.Color</returns>
        protected static System.Drawing.Color Translate(string htmlColor)
        {
            try
            {
                return System.Drawing.ColorTranslator.FromHtml(htmlColor);
            }
            catch
            {
                return System.Drawing.Color.Empty;
            }
        }
    }
}
