// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.ViewModels
{
    using System;
    using System.Collections.ObjectModel;
    using System.Reactive.Linq;
    using System.Threading.Tasks;
    using System.Windows;
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
    /// MainViewModel
    /// </summary>
    internal class MainViewModel : NotifyPropertyChangedBase
    {
        private readonly AppConfig config = null;
        private readonly IMainModel mainModel = null;
        private readonly ILinkModel linkModel = null;
        private readonly IPortModel portModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="MainViewModel"/> class.
        /// </summary>
        /// <param name="config">AppConfig</param>
        /// <param name="rootModel">IRootModel</param>
        /// <param name="mainModel">IMainModel</param>
        /// <param name="linkModel">ILinkModel</param>
        /// <param name="portModel">IPortModel</param>
        /// <param name="recordModel">IRecordModel</param>
        /// <param name="snapCurrentGraphModel">ISnapCurrentGraphModel</param>
        /// <param name="snapHardwareGraphModel">ISnapHardwareGraphModel</param>
        public MainViewModel(AppConfig config, IRootModel rootModel, IMainModel mainModel, ILinkModel linkModel, IPortModel portModel, IRecordModel recordModel, ISnapCurrentGraphModel snapCurrentGraphModel, ISnapHardwareGraphModel snapHardwareGraphModel)
        {
            this.config = config;
            this.mainModel = mainModel;
            this.linkModel = linkModel;
            this.portModel = portModel;
            this.ControlHistory = mainModel.ControlHistory.ToReadOnlyReactiveCollection().AddTo(this.CompositeDisposable);
            this.DebugPortTransmitHistory = mainModel.DebugPortTransmitHistory.ToReadOnlyReactiveCollection().AddTo(this.CompositeDisposable);
            this.DebugPortReceiveHistory = mainModel.DebugPortReceiveHistory.ToReadOnlyReactiveCollection().AddTo(this.CompositeDisposable);
            this.LogPortReceiveHistory = mainModel.LogPortReceiveHistory.ToReadOnlyReactiveCollection().AddTo(this.CompositeDisposable);
            this.AppLogHistory = mainModel.AppLogHistory.ToReadOnlyReactiveCollection().AddTo(this.CompositeDisposable);
            this.SnapCurrentGraphMenuAvailable = snapCurrentGraphModel.GraphSourceItems
                .ObserveProperty(x => x.Count, isPushCurrentValueAtFirst: true)
                .Select(x => x > 0)
                .ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.SnapHardwareGraphMenuAvailable = snapHardwareGraphModel.GraphSourceItems
                .ObserveProperty(x => x.Count, isPushCurrentValueAtFirst: true)
                .Select(x => x > 0)
                .ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            this.SetLogDirectoryCommand = new AsyncReactiveCommand<string>().WithSubscribe(x => Task.Run(() => recordModel.SetDirectory(x))).AddTo(this.CompositeDisposable);
            this.SetSelectedHostPortUnitCommand = new AsyncReactiveCommand<IPortUnit<ByteSpan>>().WithSubscribe(x => Task.Run(() => portModel.SetSelectedHostPortUnit(x))).AddTo(this.CompositeDisposable);
            this.SetSelectedDebugPortUnitCommand = new AsyncReactiveCommand<IPortUnit<string>>().WithSubscribe(x => Task.Run(() => portModel.SetSelectedDebugPortUnit(x))).AddTo(this.CompositeDisposable);
            this.SetSelectedLogPortUnitCommand = new AsyncReactiveCommand<IPortUnit<string>>().WithSubscribe(x => Task.Run(() => portModel.SetSelectedLogPortUnit(x))).AddTo(this.CompositeDisposable);
            this.ResetNopCountCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => mainModel.ResetNopCount())).AddTo(this.CompositeDisposable);
            this.ShowLiveCurrentGraphWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifyLiveCurrentGraphVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.ShowSnapCurrentGraphWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifySnapCurrentGraphVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.ShowLiveHardwareGraphWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifyLiveHardwareGraphVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.ShowSnapHardwareGraphWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifySnapHardwareGraphVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.ShowLoopbackWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifyLoopbackVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.ShowStubWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifyStubVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.ShowOptionsWindowCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => rootModel.NotifyOptionsVisibilityRequest(true))).AddTo(this.CompositeDisposable);
            this.OpenRecordDirectoryCommand = new AsyncReactiveCommand().WithSubscribe(() => Task.Run(() => recordModel.OpenDirectory()).AddTo(this.CompositeDisposable));

            rootModel.ErrorDialogRequest.Subscribe(x => this.Messenger.Raise(MessageErrorDialogRequest, new MessageBoxResource(x, Resources.MainWindow_Title, MessageBoxButton.OK, MessageBoxImage.Warning))).AddTo(this.CompositeDisposable);
            recordModel.FoloderDialogRequest.Subscribe(x => this.Messenger.Raise(MessageFolderDialogRequest, new FolderDialogResource(null, null))).AddTo(this.CompositeDisposable);
        }

        /// <summary>
        /// 「エラーダイアログ表示要求」のメッセージ名
        /// </summary>
        public const string MessageErrorDialogRequest = "ErrorDialogRequest";

        /// <summary>
        /// 「フォルダ選択ダイアログ表示要求」のメッセージ名
        /// </summary>
        public const string MessageFolderDialogRequest = "FolderDialogRequest";

        /// <summary>
        /// Loopback Client メニュー項目の表示要否を取得する。
        /// </summary>
        public bool LoopbackClientMenuVisible => this.config.UseLookbackClient;

        /// <summary>
        /// Stub Host Port メニュー項目の表示要否を取得する。
        /// </summary>
        public bool StubHostPortMenuVisible => this.config.UseStubHostPort;

        /// <summary>
        /// Messenger を取得する。
        /// </summary>
        public Messenger Messenger { get; } = new Messenger();

        /// <summary>
        /// Host Port 一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<IPortUnit<ByteSpan>> HostPortUnits => this.portModel.HostPortUnits;

        /// <summary>
        /// Debug Port 一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<IPortUnit<string>> DebugPortUnits => this.portModel.DebugPortUnits;

        /// <summary>
        /// Log Port 一覧を取得する。
        /// </summary>
        public ReadOnlyCollection<IPortUnit<string>> LogPortUnits => this.portModel.LogPortUnits;

        /// <summary>
        /// コントロール履歴を取得する。
        /// </summary>
        public ReadOnlyReactiveCollection<HistoryData<ControlType>> ControlHistory { get; }

        /// <summary>
        /// Debug Port 送信履歴を取得する。
        /// </summary>
        public ReadOnlyReactiveCollection<HistoryData> DebugPortTransmitHistory { get; }

        /// <summary>
        /// Debug Port 受信履歴を取得する。
        /// </summary>
        public ReadOnlyReactiveCollection<HistoryData> DebugPortReceiveHistory { get; }

        /// <summary>
        /// Log Port 受信履歴を取得する。
        /// </summary>
        public ReadOnlyReactiveCollection<HistoryData> LogPortReceiveHistory { get; }

        /// <summary>
        /// アプリケーションログ履歴を取得する。
        /// </summary>
        public ReadOnlyObservableCollection<ILogMessage> AppLogHistory { get; }

        /// <summary>
        /// Snap Current Graph Window の前面表示メニューの操作可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> SnapCurrentGraphMenuAvailable { get; }

        /// <summary>
        /// Snap Hardware Graph Window の前面表示メニューの操作可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> SnapHardwareGraphMenuAvailable { get; }

        /// <summary>
        /// Host Port の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> HostPortAvailable => this.portModel.HostPortAvailable;

        /// <summary>
        /// Debug Port の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> DebugPortAvailable => this.portModel.DebugPortAvailable;

        /// <summary>
        /// Log Port の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> LogPortAvailable => this.portModel.LogPortAvailable;

        /// <summary>
        /// PUB 送信処理の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> PubTransmitterAvailable => this.linkModel.PubTransmitterAvailable;

        /// <summary>
        /// PULL 受信処理の利用可否を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<bool> PullReceiverAvailable => this.linkModel.PullReceiverAvailable;

        /// <summary>
        /// 選択中の Host Port を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<IPortUnit<ByteSpan>> SelectedHostPortUnit => this.portModel.SelectedHostPortUnit;

        /// <summary>
        /// 選択中の Debug Port を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<IPortUnit<string>> SelectedDebugPortUnit => this.portModel.SelectedDebugPortUnit;

        /// <summary>
        /// 選択中の Log Port を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<IPortUnit<string>> SelectedLogPortUnit => this.portModel.SelectedLogPortUnit;

        /// <summary>
        /// No Operation Control 数を取得する。
        /// </summary>
        public IReadOnlyReactiveProperty<int> NopCount => this.mainModel.NopCount;

        /// <summary>
        /// コントロール履歴の表示要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> ShowControlHistory => this.mainModel.ShowControlHistory;

        /// <summary>
        /// Debug Port 送信履歴の表示要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> ShowDebugPortTransmitHistory => this.mainModel.ShowDebugPortTransmitHistory;

        /// <summary>
        /// Debug Port 受信履歴の表示要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> ShowDebugPortReceiveHistory => this.mainModel.ShowDebugPortReceiveHistory;

        /// <summary>
        /// Log Port 受信履歴の表示要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> ShowLogPortReceiveHistory => this.mainModel.ShowLogPortReceiveHistory;

        /// <summary>
        /// アプリケーションログ履歴の表示要否を取得する。
        /// </summary>
        public IReactiveProperty<bool> ShowAppLogHistory => this.mainModel.ShowAppLogHistory;

        /// <summary>
        /// No Operation Control 数を 0 にリセットするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<string> SetLogDirectoryCommand { get; }

        /// <summary>
        /// Host Port を選択状態にするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<IPortUnit<ByteSpan>> SetSelectedHostPortUnitCommand { get; }

        /// <summary>
        /// Debug Port を選択状態にするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<IPortUnit<string>> SetSelectedDebugPortUnitCommand { get; }

        /// <summary>
        /// Log Port を選択状態にするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand<IPortUnit<string>> SetSelectedLogPortUnitCommand { get; }

        /// <summary>
        /// Live Current Graph Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowLiveCurrentGraphWindowCommand { get; }

        /// <summary>
        /// Snap Current Graph Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowSnapCurrentGraphWindowCommand { get; }

        /// <summary>
        /// Live Hardware Graph Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowLiveHardwareGraphWindowCommand { get; }

        /// <summary>
        /// Snap Hardware Graph Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowSnapHardwareGraphWindowCommand { get; }

        /// <summary>
        /// Loopback Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowLoopbackWindowCommand { get; }

        /// <summary>
        /// Stub Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowStubWindowCommand { get; }

        /// <summary>
        /// 記録ディレクトリのエクスプローラーでの表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand OpenRecordDirectoryCommand { get; }

        /// <summary>
        /// Options Window の前面表示を要求するコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ShowOptionsWindowCommand { get; }

        /// <summary>
        /// No Operation Control 数を 0 にリセットするコマンドを取得する。
        /// </summary>
        public AsyncReactiveCommand ResetNopCountCommand { get; }
    }
}
