// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System;
    using System.Collections.ObjectModel;
    using System.Reactive.Concurrency;
    using System.Reactive.Linq;
    using System.Threading.Tasks;
    using System.Windows;
    using System.Windows.Threading;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Gateway.Models;
    using Sony.Jin.Gateway.Properties;
    using Sony.Jin.Presentation;
    using Sony.Jin.Shared;

    // INotifyPropertyChanged が実装されていない ViewModel はメモリリークする問題があるため、
    // ViewModel は INotifyPropertyChanged を実装すること（NotifyPropertyChangedBase は実装済み）

    /// <summary>
    /// GraphViewModel
    /// </summary>
    /// <typeparam name="T">GraphSource の派生クラス</typeparam>
    internal class GraphViewModel<T> : NotifyPropertyChangedBase
        where T : GraphSource
    {
        private readonly IGraphModel<T> graphModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="GraphViewModel{T}"/> class.
        /// </summary>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="graphModel">IGraphModel</param>
        /// <param name="visibilityRequest">Graph Window の前面表示（true）・非表示（false）要求の通知</param>
        public GraphViewModel(IRootModel rootModel, IGraphModel<T> graphModel, IObservable<bool> visibilityRequest)
        {
            this.graphModel = graphModel;

            // 重要: ComboBox の要素削除の際に新たな選択状態をセットするときの対処について
            //   ComboBox (Selector) のプロパティ ItemsSource に binding される Collection の要素削除と
            //   SelectedItem に binding される値の変更は、Selector 内の処理を踏まえて、
            //       (1) SelectedItem を null    ※ 予め削除前に選択を外すことで不整合の発生・不要な処理を防ぐ
            //       (2) ItemsSource の要素削除
            //       (3) SelectedItem を新たな選択要素をセット
            //   の UI スレッドにおける処理順を守ることが重要となる。特に (1) を欠く場合や、(3) が (2) の途中に割り込む場合、
            //   不整合により Selector から ItemsSource が null にセットされる症状が1回ないし複数回発生する。
            //   また、非 null がセットされているにも関わらず、View 上では無選択の状態になる症状が見られることもある。
            //   従って、以下では順序の担保のため、
            //       - (1)(2) の処理を同一の Scheduler (Priority: Normal)
            //       - (3) の処理を (2) よりも Priority の低い Scheduler (Priority: Backgrond)
            //   で Dispatch されるようにする。
            var normalScheduler = new DispatcherScheduler(Application.Current.Dispatcher, DispatcherPriority.Normal);
            var backgroundScheduler = new DispatcherScheduler(Application.Current.Dispatcher, DispatcherPriority.Background);

            // ItemsSource へは (2) のために DispatcherPriority.Normal
            this.GraphSourceItems = graphModel.GraphSourceItems.ToReadOnlyReactiveCollection(scheduler: normalScheduler).AddTo(this.CompositeDisposable);

            // SelectedItem へは (1) null の場合 DispatcherPriority.Normal、(3) 非 null の場合 DispatcherPriority.Background
            var nullItem = graphModel.SelectedGraphSourceItem.Where(x => x == null).ObserveOn(normalScheduler);
            var nonNullItem = graphModel.SelectedGraphSourceItem.Where(x => x != null).ObserveOn(backgroundScheduler);
            this.SelectedGraphSourceItem = Observable.Merge(nullItem, nonNullItem).ToReactiveProperty(mode: ReactivePropertyMode.DistinctUntilChanged).AddTo(this.CompositeDisposable);
            this.SelectedGraphSourceItem.Subscribe(x => graphModel.SelectedGraphSourceItem.Value = x).AddTo(this.CompositeDisposable);

            this.SnapAvailable = graphModel.GraphSource.Select(x => x != null).ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.MoveXAxisCommand = new AsyncReactiveCommand<int>().WithSubscribe(x => Task.Run(() => graphModel.MoveXAxis(x))).AddTo(this.CompositeDisposable);
            this.RemoveSelectedGraphSourceCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => graphModel.RemoveSelectedGraphSource())).AddTo(this.CompositeDisposable);
            this.CaptureCommand = new AsyncReactiveCommand<string>().WithSubscribe(x => Task.Run(() => this.Messenger.Raise(MessageCaptureRequest, x))).AddTo(this.CompositeDisposable);
            this.ReceiveCaptureResultCommand = new AsyncReactiveCommand<bool>().WithSubscribe(x => x ? Task.CompletedTask : Task.Run(() => rootModel.NotifyErrorDialogRequest(Resources.ErrorDialog_MessageCaptureWindowFailure))).AddTo(this.CompositeDisposable);

            visibilityRequest.Subscribe(x => this.Messenger.Raise(MessageVisibilityRequest, x)).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// 「ウィンドウの前面表示・非表示要求」のメッセージ名
        /// </summary>
        public const string MessageVisibilityRequest = "VisibilityRequest";

        /// <summary>
        /// 「ウィンドウのキャプチャ要求」のメッセージ名
        /// </summary>
        public const string MessageCaptureRequest = "CaptureRequest";

        /// <summary>
        /// Snap Graph か否かを取得する。
        /// </summary>
        public bool SnapGraph => this.graphModel.SnapGraph;

        /// <summary>
        /// Messenger を取得する。
        /// </summary>
        public Messenger Messenger { get; } = new Messenger();

        /// <summary>
        /// X 軸情報一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<AxisData<int>> XAxisCollection => this.graphModel.XAxisCollection;

        /// <summary>
        /// ナノギャップ生成モード向け Y 軸情報一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<AxisData<double>> LowModeYAxisCollection => this.graphModel.LowModeYAxisCollection;

        /// <summary>
        /// 電流計測モード向け Y 軸情報一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<AxisData<double>> HighModeYAxisCollection => this.graphModel.HighModeYAxisCollection;

        /// <summary>
        /// グラフ表示用情報項目一覧を取得する。
        /// </summary>
        public ReadOnlyObservableCollection<Item<T>> GraphSourceItems { get; }

        /// <summary>
        /// 選択中の X 軸情報を取得する。
        /// </summary>
        public IReactiveProperty<AxisData<int>> SelectedXAxis => this.graphModel.SelectedXAxis;

        /// <summary>
        /// 選択中のナノギャップ生成モード向け Y 軸情報を取得する。
        /// </summary>
        public IReactiveProperty<AxisData<double>> SelectedLowModeYAxis => this.graphModel.SelectedLowModeYAxis;

        /// <summary>
        /// 選択中の電流計測モード向け Y 軸情報を取得する。
        /// </summary>
        public IReactiveProperty<AxisData<double>> SelectedHighModeYAxis => this.graphModel.SelectedHighModeYAxis;

        /// <summary>
        /// 選択中のグラフ表示用情報項目を取得する。
        /// </summary>
        public IReactiveProperty<Item<T>> SelectedGraphSourceItem { get; }

        /// <summary>
        /// スナップの利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> SnapAvailable { get; }

        /// <summary>
        /// 指定中の X 軸情報を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<AxisData<int>> XAxis => this.graphModel.XAxis;

        /// <summary>
        /// 指定中の Y 軸情報を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<AxisData<double>> YAxis => this.graphModel.YAxis;

        /// <summary>
        /// グラフ表示用情報を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<T> GraphSource => this.graphModel.GraphSource;

        /// <summary>
        /// 左ページ送りの利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> PageLeftAvailable => this.graphModel.PageLeftAvailable;

        /// <summary>
        /// 右ページ送りの利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> PageRightAvailable => this.graphModel.PageRightAvailable;

        /// <summary>
        /// 左1マス送りの利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> DivisionLeftAvailable => this.graphModel.DivisionLeftAvailable;

        /// <summary>
        /// 右1マス送りの利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> DivisionRightAvailable => this.graphModel.DivisionRightAvailable;

        /// <summary>
        /// X 軸を移動するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<int> MoveXAxisCommand { get; }

        /// <summary>
        /// 選択中のグラフ表示用情報を削除するマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand RemoveSelectedGraphSourceCommand { get; }

        /// <summary>
        /// Graph Window をキャプチャするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> CaptureCommand { get; }

        /// <summary>
        /// Graph Window のキャプチャ結果を受け取るコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<bool> ReceiveCaptureResultCommand { get; }

        /// <summary>
        /// System.Drawing.Color を System.Windows.Media.Brush に変換する。
        /// </summary>
        /// <param name="source">System.Drawing.Color</param>
        /// <returns>生成した System.Windows.Media.Brush</returns>
        protected static System.Windows.Media.Brush Convert(System.Drawing.Color source)
        {
            var brush = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(source.A, source.R, source.G, source.B));
            brush.Freeze();
            return brush;
        }
    }
}
