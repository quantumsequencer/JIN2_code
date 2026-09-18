// Copyright 2026 Sony Global Manufacturing & Operations Corporation

namespace Sony.Jin.Gateway.Models
{
    using System;
    using System.Collections;
    using System.Collections.ObjectModel;
    using Reactive.Bindings;
    using Reactive.Bindings.Extensions;
    using Sony.Jin.Gateway.Data;
    using Sony.Jin.Shared;

    /// <inheritdoc cref="IMainModel"/>
    internal class MainModel : DisposableBase, IMainModel
    {
        private readonly ObservableCollection<HistoryData<ControlType>> controlHistory = new ObservableCollection<HistoryData<ControlType>>();
        private readonly ObservableCollection<HistoryData> debugPortTransmitHistory = new ObservableCollection<HistoryData>();
        private readonly ObservableCollection<HistoryData> debugPortReceiveHistory = new ObservableCollection<HistoryData>();
        private readonly ObservableCollection<HistoryData> logPortReceiveHistory = new ObservableCollection<HistoryData>();
        private readonly ObservableCollection<ILogMessage> appLogHistory = new ObservableCollection<ILogMessage>();
        private readonly ReactiveProperty<int> nopCount = null;
        private readonly ILogger logger = null;
        private readonly ILinkModel linkModel = null;
        private readonly ILoopbackModel loopbackModel = null;
        private readonly IPortModel portModel = null;
        private readonly IRecordModel recordModel = null;
        private readonly ILiveCurrentGraphModel liveCurrentGraphModel = null;
        private readonly ILiveHardwareGraphModel liveHardwareGraphModel = null;
        private readonly ISnapCurrentGraphModel snapCurrentGraphModel = null;
        private readonly ISnapHardwareGraphModel snapHardwareGraphModel = null;

        /// <summary>
        /// Initializes a new instance of the <see cref="MainModel"/> class.
        /// </summary>
        /// <param name="logger">ILogger</param>
        /// <param name="config">AppConfig</param>
        /// <param name="settings">AppSettings</param>
        /// <param name="linkModel">ILinkModel</param>
        /// <param name="loopbackModel">ILoopbackModel</param>
        /// <param name="portModel">IPortModel</param>
        /// <param name="recordModel">IRecordModel</param>
        /// <param name="liveCurrentGraphModel">ILiveCurrentGraphModel</param>
        /// <param name="liveHardwareGraphModel">ILiveHardwareGraphModel</param>
        /// <param name="snapCurrentGraphModel">ISnapCurrentGraphModel</param>
        /// <param name="snapHardwareGraphModel">ISnapHardwareGraphModel</param>
        public MainModel(
            ILogger logger,
            AppConfig config,
            AppSettings settings,
            ILinkModel linkModel,
            ILoopbackModel loopbackModel,
            IPortModel portModel,
            IRecordModel recordModel,
            ILiveCurrentGraphModel liveCurrentGraphModel,
            ILiveHardwareGraphModel liveHardwareGraphModel,
            ISnapCurrentGraphModel snapCurrentGraphModel,
            ISnapHardwareGraphModel snapHardwareGraphModel)
        {
            this.logger = logger;
            this.linkModel = linkModel;
            this.loopbackModel = loopbackModel;
            this.portModel = portModel;
            this.recordModel = recordModel;
            this.liveCurrentGraphModel = liveCurrentGraphModel;
            this.liveHardwareGraphModel = liveHardwareGraphModel;
            this.snapCurrentGraphModel = snapCurrentGraphModel;
            this.snapHardwareGraphModel = snapHardwareGraphModel;

            this.ControlHistory = new ReadOnlyObservableCollection<HistoryData<ControlType>>(this.controlHistory);
            this.DebugPortTransmitHistory = new ReadOnlyObservableCollection<HistoryData>(this.debugPortTransmitHistory);
            this.DebugPortReceiveHistory = new ReadOnlyObservableCollection<HistoryData>(this.debugPortReceiveHistory);
            this.LogPortReceiveHistory = new ReadOnlyObservableCollection<HistoryData>(this.logPortReceiveHistory);
            this.AppLogHistory = new ReadOnlyObservableCollection<ILogMessage>(this.appLogHistory);
            this.nopCount = new ReactiveProperty<int>(0).AddTo(this.CompositeDisposable);
            this.NopCount = this.nopCount.ToReadOnlyReactivePropertySlim().AddTo(this.CompositeDisposable);
            var showControlHistory = settings.ToObservableSetting("ShowControlHistory", true).AddTo(this.CompositeDisposable);
            this.ShowControlHistory = showControlHistory.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            var showDebugPortTransmitHistory = settings.ToObservableSetting("ShowDebugPortTransmitHistory", true).AddTo(this.CompositeDisposable);
            this.ShowDebugPortTransmitHistory = showDebugPortTransmitHistory.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            var showDebugPortReceiveHistory = settings.ToObservableSetting("ShowDebugPortReceiveHistory", true).AddTo(this.CompositeDisposable);
            this.ShowDebugPortReceiveHistory = showDebugPortReceiveHistory.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            var showLogPortReceiveHistory = settings.ToObservableSetting("ShowLogPortReceiveHistory", true).AddTo(this.CompositeDisposable);
            this.ShowLogPortReceiveHistory = showLogPortReceiveHistory.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);
            var showAppLogHistory = settings.ToObservableSetting("ShowAppLogHistory", true).AddTo(this.CompositeDisposable);
            this.ShowAppLogHistory = showAppLogHistory.ToReactivePropertyAsSynchronized(x => x.Value).AddTo(this.CompositeDisposable);

            // Link から Port へ転送
            linkModel.HostControl.Subscribe(x => portModel.TransmitHostPortUnitAsync(x)).AddTo(this.CompositeDisposable);
            linkModel.DebugControl.Subscribe(x => portModel.TransmitDebugPortUnitAsync(x)).AddTo(this.CompositeDisposable);

            // Port から Link へ転送
            portModel.HostPortReceived.Subscribe(x => linkModel.TransmitHostTopicAsync(x)).AddTo(this.CompositeDisposable);
            portModel.DebugPortReceived.Subscribe(x => linkModel.TransmitDebugTopicAsync(x)).AddTo(this.CompositeDisposable);
            portModel.LogPortReceived.Subscribe(x => linkModel.TransmitLogTopicAsync(x)).AddTo(this.CompositeDisposable);

            // Link からの通知を処理
            linkModel.AppControl.Subscribe(this.ProcessAppControl).AddTo(this.CompositeDisposable);

            // Link/Port のログを表示
            recordModel.ControlLinkMessage.Subscribe(x => AddToCollection(this.controlHistory, x, config.ControlHistoryUpperLimit)).AddTo(this.CompositeDisposable);
            recordModel.DebugPortTxMessage.Subscribe(x => AddToCollection(this.debugPortTransmitHistory, x, config.DebugPortTransmitHistoryUpperLimit)).AddTo(this.CompositeDisposable);
            recordModel.DebugPortRxMessage.Subscribe(x => AddToCollection(this.debugPortReceiveHistory, x, config.DebugPortReceiveHistoryUpperLimit)).AddTo(this.CompositeDisposable);
            recordModel.LogPortRxMessage.Subscribe(x => AddToCollection(this.logPortReceiveHistory, x, config.LogPortReceiveHistoryUpperLimit)).AddTo(this.CompositeDisposable);

            // アプリログを表示
            logger.LogMessage.Subscribe(x => AddToCollection(this.appLogHistory, x, config.AppLogHistoryUpperLimit)).AddTo(this.CompositeDisposable);
        }

        /// <inheritdoc/>
        public ReadOnlyObservableCollection<HistoryData<ControlType>> ControlHistory { get; }

        /// <inheritdoc/>
        public ReadOnlyObservableCollection<HistoryData> DebugPortTransmitHistory { get; }

        /// <inheritdoc/>
        public ReadOnlyObservableCollection<HistoryData> DebugPortReceiveHistory { get; }

        /// <inheritdoc/>
        public ReadOnlyObservableCollection<HistoryData> LogPortReceiveHistory { get; }

        /// <inheritdoc/>
        public ReadOnlyObservableCollection<ILogMessage> AppLogHistory { get; }

        /// <inheritdoc/>
        public IReadOnlyReactiveProperty<int> NopCount { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> ShowControlHistory { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> ShowDebugPortTransmitHistory { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> ShowDebugPortReceiveHistory { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> ShowLogPortReceiveHistory { get; }

        /// <inheritdoc/>
        public IReactiveProperty<bool> ShowAppLogHistory { get; }

        /// <inheritdoc/>
        public void Initialize()
        {
        }

        /// <inheritdoc/>
        public void Activate()
        {
            this.recordModel.Activate();
            this.portModel.Activate();
            this.linkModel.Activate();
            this.loopbackModel.Activate();
        }

        /// <inheritdoc/>
        public void Deactivate()
        {
        }

        /// <inheritdoc/>
        public void ResetNopCount()
        {
            this.nopCount.Value = 0;
        }

        private void ProcessAppControl(ControlType type)
        {
            switch (type)
            {
                case ControlType.Nop: this.nopCount.Value++; return;
                case ControlType.SnapCurrentGraph: this.ProcessSnapCurrentGraph(); return;
                case ControlType.SnapHardwareGraph: this.ProcessSnapHardwareGraph(); return;
            }

            this.logger.Info(string.Format("Unsupported control type code received: code = {0:X2}h", (byte)type));
        }

        private void ProcessSnapCurrentGraph()
        {
            var currentGraphSource = this.liveCurrentGraphModel.GraphSource.Value;
            if (currentGraphSource == null)
            {
                this.logger.Info("Canceled control to snap current graph due to no live graph displayed.");
                return;
            }

            this.snapCurrentGraphModel.AddGraphSource(this.liveCurrentGraphModel.GraphSource.Value);
        }

        private void ProcessSnapHardwareGraph()
        {
            var hardwareGraphSource = this.liveHardwareGraphModel.GraphSource.Value;
            if (hardwareGraphSource == null)
            {
                this.logger.Info("Canceled control to snap hardware graph due to no live graph displayed.");
                return;
            }

            this.snapHardwareGraphModel.AddGraphSource(hardwareGraphSource);
        }

        private static void AddToCollection<T>(ObservableCollection<T> collection, T element, int upperLimit)
        {
            lock (((ICollection)collection).SyncRoot)
            {
                collection.Add(element);
                if (collection.Count > upperLimit)
                {
                    collection.RemoveAt(0);
                }
            }
        }
    }
}
